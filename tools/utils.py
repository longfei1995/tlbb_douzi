from typing import Dict, List, Optional, Union

import cv2
import numpy as np
import os

from bbox import BBox


class ImageUtils:
    """图像处理工具类，包含一些常用的图像操作方法"""

    def __init__(self, hwnd: int, yolo_model_path: str = "assets/best.pt"):
        """
        参数:
            hwnd: 目标窗口句柄
            yolo_model_path: YOLO 模型文件路径，默认 assets/best.pt
        """
        self.hwnd = hwnd
        self._yolo_model_path = yolo_model_path
        self._ocr_model = None
        self._yolo_model = None
        self._color_reference: Optional[np.ndarray] = None

    # ------------------------------------------------------------------ #
    #  内部截图工具                                                         #
    # ------------------------------------------------------------------ #

    def _screenshot(self, box: Optional[BBox] = None) -> np.ndarray:
        """
        截取 hwnd 窗口图像（包括标题栏），若提供 box 则裁剪到该区域。

        参数:
            box: BBox 对象（坐标相对于窗口左上角），None 表示整个窗口

        返回:
            BGR numpy 数组
        """
        import win32con
        import win32gui
        import win32ui

        left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
        w = right - left
        h = bottom - top

        hwnd_dc = win32gui.GetWindowDC(self.hwnd)
        mfc_dc = win32ui.CreateDCFromHandle(hwnd_dc)
        save_dc = mfc_dc.CreateCompatibleDC()

        bitmap = win32ui.CreateBitmap()
        bitmap.CreateCompatibleBitmap(mfc_dc, w, h)
        save_dc.SelectObject(bitmap)
        save_dc.BitBlt((0, 0), (w, h), mfc_dc, (0, 0), win32con.SRCCOPY)

        bmp_info = bitmap.GetInfo()
        bmp_str = bitmap.GetBitmapBits(True)
        img = np.frombuffer(bmp_str, dtype=np.uint8).reshape(
            bmp_info["bmHeight"], bmp_info["bmWidth"], 4
        )
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        save_dc.DeleteDC()
        mfc_dc.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, hwnd_dc)
        win32gui.DeleteObject(bitmap.GetHandle())

        if box is not None:
            x1, y1, x2, y2 = box.int_coords()
            img = img[y1:y2, x1:x2]

        return img

    # ------------------------------------------------------------------ #
    #  OCR                                                                 #
    # ------------------------------------------------------------------ #

    def ocr(
        self,
        box: Optional[BBox] = None,
        scale: float = 1.0,
    ) -> List[BBox]:
        """
        对屏幕指定区域进行光学字符识别（OCR）。

        参数:
            box:   识别区域，None 表示整个窗口
            scale: 送入 OCR 前的放大倍数（建议小区域用 3.0），不影响返回坐标

        返回:
            包含识别结果的 BBox 列表，BBox.name 为识别文本，BBox.confidence 为置信度
        """
        from onnxocr.onnx_paddleocr import ONNXPaddleOcr

        if self._ocr_model is None:
            self._ocr_model = ONNXPaddleOcr(use_angle_cls=True, use_gpu=False)

        img = self._screenshot(box)
        if scale != 1.0:
            h, w = img.shape[:2]
            img = cv2.resize(
                img,
                (max(1, int(w * scale)), max(1, int(h * scale))),
                interpolation=cv2.INTER_LANCZOS4,
            )
            # 转灰度 → Otsu 二值化（亮字深色背景 → 黑字白底）
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            img = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        result = self._ocr_model.ocr(img)

        boxes: List[BBox] = []
        if not result or not result[0]:
            return boxes

        offset_x = box.x1 if box is not None else 0.0
        offset_y = box.y1 if box is not None else 0.0

        for line in result[0]:
            pts, (text, conf) = line[0], line[1]
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            boxes.append(
                BBox(
                    x1=min(xs) + offset_x,
                    y1=min(ys) + offset_y,
                    x2=max(xs) + offset_x,
                    y2=max(ys) + offset_y,
                    name=text,
                    confidence=conf,
                )
            )

        return boxes

    # ------------------------------------------------------------------ #
    #  模板匹配                                                            #
    # ------------------------------------------------------------------ #

    def match_template(
        self,
        label_json: str,
        label: str,
        threshold: float = 0.8,
        save_debug: bool = False,
        debug_dir: str = "assets/tmp_images",
    ) -> Optional[BBox]:
        """
        从标注 JSON 中指定的区域，在当前窗口截图中匹配。
        适合用于判断当前是否处于某个场景等需求。

        参数:
            label_json: 标注 JSON 路径
            label:      要匹配的标注名称（如 "chang_jing_ming_zi"）
            threshold:  匹配置信度阈值 [0, 1]，默认 0.8
            save_debug: 是否保存调试图片（模板、截图、匹配热力图）
            debug_dir:  调试图片保存目录

        返回:
            匹配成功返回 BBox（坐标为当前窗口内的位置，confidence 为匹配度）；
            未找到或低于阈值返回 None
        """
        import json as _json
        import time
        import win32gui

        self.activate()

        # 等待窗口尺寸合法（与 read_labeled_regions 保持一致）
        for _ in range(20):
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            win_w, win_h = right - left, bottom - top
            if left != -32000 and win_w > 100 and win_h > 100:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError(
                f"窗口尺寸异常，无法截图: rect=({left},{top},{right},{bottom})"
            )

        if not os.path.isfile(label_json):
            raise FileNotFoundError(f"标注文件不存在: {label_json}")
        with open(label_json, encoding="utf-8") as f:
            meta = _json.load(f)
        ref_w, ref_h = meta["imageWidth"], meta["imageHeight"]
        target_shape = next(
            (
                s
                for s in meta.get("shapes", [])
                if s["label"] == label and s.get("shape_type") == "rectangle"
            ),
            None,
        )
        if target_shape is None:
            raise ValueError(f"标注文件 {label_json} 中未找到 label='{label}'")

        pts = target_shape["points"]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        tx1, ty1, tx2, ty2 = int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys))

        # 从 JSON 的 imagePath 字段推断图片路径（相对于 JSON 所在目录）
        image_path = meta.get("imagePath", "")
        if not os.path.isabs(image_path):
            image_path = os.path.join(os.path.dirname(label_json), image_path)
        ref_img = cv2.imread(image_path)
        if ref_img is None:
            raise FileNotFoundError(f"参考图读取失败: {image_path}")
        template = ref_img[ty1:ty2, tx1:tx2]

        screen = self._screenshot()
        screen_resized = screen
        if screen.shape[1] != ref_w or screen.shape[0] != ref_h:
            screen_resized = cv2.resize(
                screen, (ref_w, ref_h), interpolation=cv2.INTER_LINEAR
            )

        if save_debug:
            os.makedirs(debug_dir, exist_ok=True)
            cv2.imwrite(
                os.path.join(debug_dir, f"match_template_{label}.png"), template
            )
            cv2.imwrite(
                os.path.join(debug_dir, f"match_screen_{label}.png"), screen_resized
            )
            print(
                f"  [debug] window: {win_w}x{win_h}  screen_resized: {screen_resized.shape[1]}x{screen_resized.shape[0]}"
            )
            print(
                f"  [debug] template: {template.shape[1]}x{template.shape[0]}  from ref {ref_w}x{ref_h}"
            )
            print(f"  [debug] template bbox: tx1={tx1} ty1={ty1} tx2={tx2} ty2={ty2}")

        match_result = cv2.matchTemplate(screen_resized, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(match_result)

        if save_debug:
            # 归一化热力图并标注最佳匹配位置
            heat = cv2.normalize(match_result, None, 0, 255, cv2.NORM_MINMAX, cv2.CV_8U)
            heat_bgr = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
            mx, my = max_loc
            cv2.rectangle(
                heat_bgr, (mx, my), (mx + tx2 - tx1, my + ty2 - ty1), (0, 255, 0), 2
            )
            cv2.imwrite(os.path.join(debug_dir, f"match_heatmap_{label}.png"), heat_bgr)
            # 在截图上标注最佳匹配框
            annotated = screen_resized.copy()
            cv2.rectangle(
                annotated, (mx, my), (mx + tx2 - tx1, my + ty2 - ty1), (0, 255, 0), 2
            )
            cv2.putText(
                annotated,
                f"{max_val:.3f}",
                (mx, max(my - 5, 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
            cv2.imwrite(
                os.path.join(debug_dir, f"match_annotated_{label}.png"), annotated
            )
            print(
                f"  [debug] max_val={max_val:.4f}  threshold={threshold}  max_loc={max_loc}"
            )
            print(
                f"  [debug] saved: match_template/screen/heatmap/annotated_{label}.png -> {debug_dir}"
            )

        if max_val < threshold:
            return None

        scale_x = win_w / ref_w
        scale_y = win_h / ref_h
        mx, my = max_loc
        return BBox(
            x1=mx * scale_x,
            y1=my * scale_y,
            x2=(mx + (tx2 - tx1)) * scale_x,
            y2=(my + (ty2 - ty1)) * scale_y,
            name=label,
            confidence=float(max_val),
        )

    # ------------------------------------------------------------------ #
    #  特征查找（YOLO）                                                     #
    # ------------------------------------------------------------------ #

    def find_feature(
        self,
        feature_name: Optional[Union[str, List[str]]] = None,
        box: Optional[BBox] = None,
    ) -> List[BBox]:
        """
        在指定区域内查找一个或多个图像特征（YOLO 目标检测）。

        参数:
            feature_name: 要查找的 YOLO 类别名（str 或 list[str]），None 表示返回全部类别
            box: 搜索区域，None 表示整个窗口

        返回:
            找到的所有匹配特征的 BBox 列表，BBox.name 为类别名，BBox.confidence 为置信度
        """
        from ultralytics import YOLO

        if self._yolo_model is None:
            self._yolo_model = YOLO(self._yolo_model_path)

        img = self._screenshot(box)
        results = self._yolo_model(img)

        name_filter: Optional[set] = None
        if feature_name is not None:
            name_filter = (
                {feature_name} if isinstance(feature_name, str) else set(feature_name)
            )

        offset_x = box.x1 if box is not None else 0.0
        offset_y = box.y1 if box is not None else 0.0

        boxes: List[BBox] = []
        for r in results:
            for det in r.boxes:
                cls_id = int(det.cls[0])
                cls_name = r.names[cls_id]
                if name_filter is not None and cls_name not in name_filter:
                    continue
                x1, y1, x2, y2 = det.xyxy[0].tolist()
                boxes.append(
                    BBox(
                        x1=x1 + offset_x,
                        y1=y1 + offset_y,
                        x2=x2 + offset_x,
                        y2=y2 + offset_y,
                        name=cls_name,
                        confidence=float(det.conf[0]),
                    )
                )

        return boxes

    # ------------------------------------------------------------------ #
    #  颜色监控                                                             #
    # ------------------------------------------------------------------ #

    def set_color_reference(self, reference: np.ndarray) -> None:
        """
        设置 find_color 的参考图像（标定图）。

        参数:
            reference: 参考状态的 BGR 图像（numpy 数组），例如满血时截取的血条图像
        """
        self._color_reference = reference

    def find_color(self, box: BBox, reference: Optional[np.ndarray] = None) -> float:
        """
        计算指定 box 区域内与参考图主色调相符的像素百分比。

        原理：从参考图提取主色调（HSV 色调直方图峰值 ± 15°），在当前截图中
        统计该色调范围的像素占比，适合监控血条满/半/空等状态。

        参数:
            box: 要检测的区域（坐标相对于窗口客户区）
            reference: 参考 BGR 图像；None 时使用 set_color_reference() 所设置的图像

        返回:
            float [0.0, 1.0]，值越大表示目标颜色占比越高

        异常:
            ValueError: reference 和 _color_reference 均为 None 时抛出
        """
        ref = reference if reference is not None else self._color_reference
        if ref is None:
            raise ValueError(
                "未设置参考图，请先调用 set_color_reference() 或传入 reference 参数"
            )

        current = self._screenshot(box)

        # 从参考图中提取有饱和度的像素的主色调
        ref_hsv = cv2.cvtColor(ref, cv2.COLOR_BGR2HSV)
        sat = ref_hsv[:, :, 1]
        val = ref_hsv[:, :, 2]
        valid_mask = ((sat > 40) & (val > 40)).astype(np.uint8) * 255
        hue_hist = cv2.calcHist([ref_hsv], [0], valid_mask, [180], [0, 180])
        dominant_hue = int(np.argmax(hue_hist))

        # 色调容差 ±15
        tolerance = 15
        h_lo = (dominant_hue - tolerance) % 180
        h_hi = (dominant_hue + tolerance) % 180

        cur_hsv = cv2.cvtColor(current, cv2.COLOR_BGR2HSV)
        if h_lo <= h_hi:
            color_mask = cv2.inRange(
                cur_hsv,
                np.array([h_lo, 40, 40]),
                np.array([h_hi, 255, 255]),
            )
        else:
            # 色调环绕（如红色横跨 170~10）
            mask1 = cv2.inRange(
                cur_hsv, np.array([h_lo, 40, 40]), np.array([179, 255, 255])
            )
            mask2 = cv2.inRange(
                cur_hsv, np.array([0, 40, 40]), np.array([h_hi, 255, 255])
            )
            color_mask = cv2.bitwise_or(mask1, mask2)

        total_pixels = current.shape[0] * current.shape[1]
        if total_pixels == 0:
            return 0.0

        return int(np.count_nonzero(color_mask)) / total_pixels

    # ------------------------------------------------------------------ #
    #  激活窗口 + 读取标注区域文字                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _auto_scale(w: float, h: float, target_short: int = 64) -> float:
        """
        根据区域像素宽高自动计算放大倍数，使短边不低于 target_short。
        最小返回 1.0，最大返回 8.0，避免过度放大带来噪点。
        """
        short = min(w, h)
        if short <= 0:
            return 4.0
        scale = target_short / short
        return float(max(1.0, min(scale, 8.0)))

    def activate(self) -> bool:
        """激活目标窗口，若最小化则还原并等待完成。"""
        import time
        import win32con
        import win32gui

        try:
            if not win32gui.IsWindow(self.hwnd):
                return False

            # 直接检查坐标判断最小化（IsIconic 对部分游戏窗口不可靠）
            left, _, _, _ = win32gui.GetWindowRect(self.hwnd)
            if win32gui.IsIconic(self.hwnd) or left == -32000:
                # SW_SHOWNORMAL 比 SW_RESTORE 对游戏窗口更可靠
                win32gui.ShowWindow(self.hwnd, win32con.SW_SHOWNORMAL)
                for _ in range(40):
                    time.sleep(0.05)
                    left, _, _, _ = win32gui.GetWindowRect(self.hwnd)
                    if left != -32000 and not win32gui.IsIconic(self.hwnd):
                        break

            try:
                win32gui.SetForegroundWindow(self.hwnd)
            except Exception:
                pass  # 非前台进程调用 SetForegroundWindow 会失败，可忽略

            return True
        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False

    @staticmethod
    def _load_label_file(label_file: str, classes_file: str = "") -> List[tuple]:
        """
        加载标注文件，自动识别格式：
          - .json  anylabeling 格式，坐标已归一化（除以图像宽高）
          - .txt   YOLO 格式，坐标本身即为归一化值
        返回 (label_name, x1_norm, y1_norm, x2_norm, y2_norm) 列表（均为归一化坐标）。
        """
        import json as _json

        ext = os.path.splitext(label_file)[1].lower()

        if ext == ".json":
            with open(label_file, encoding="utf-8") as f:
                data = _json.load(f)
            img_w = data["imageWidth"]
            img_h = data["imageHeight"]
            entries = []
            for shape in data.get("shapes", []):
                if shape.get("shape_type") != "rectangle":
                    continue
                pts = shape["points"]
                xs = [p[0] for p in pts]
                ys = [p[1] for p in pts]
                entries.append(
                    (
                        shape["label"],
                        min(xs) / img_w,
                        min(ys) / img_h,
                        max(xs) / img_w,
                        max(ys) / img_h,
                    )
                )
            return entries

        # YOLO txt 格式
        with open(classes_file, encoding="utf-8") as f:
            classes = [line.strip() for line in f if line.strip()]
        entries = []
        with open(label_file, encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) != 5:
                    continue
                cls_id = int(parts[0])
                cx, cy, w, h = (
                    float(parts[1]),
                    float(parts[2]),
                    float(parts[3]),
                    float(parts[4]),
                )
                label = classes[cls_id] if cls_id < len(classes) else str(cls_id)
                entries.append((label, cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        return entries

    def read_labeled_regions(
        self,
        label_file: str = "assets/tmp_images/1.json",
        classes_file: str = "assets/tmp_images/classes.txt",
        save_debug: bool = False,
        debug_dir: str = "assets/tmp_images",
    ) -> Dict[str, str]:
        """
        激活窗口，读取标注文件定义的各区域文字。

        参数:
            label_file:  标注文件路径，支持 anylabeling JSON (.json) 或 YOLO (.txt)
            classes_file: YOLO txt 模式下的类别名称文件，JSON 模式下忽略
            save_debug:  是否将每个区域的截图保存为 debug_<label>.png
            debug_dir:   debug 图片保存目录

        返回:
            Dict[label_name, ocr_text]，key 为标注类别名，value 为 OCR 识别文字拼接
        """
        import time
        import win32gui

        self.activate()

        # 等待窗口尺寸合法（排除最小化占位坐标 -32000）
        for _ in range(20):
            left, top, right, bottom = win32gui.GetWindowRect(self.hwnd)
            win_w = right - left
            win_h = bottom - top
            if left != -32000 and win_w > 100 and win_h > 100:
                break
            time.sleep(0.05)
        else:
            raise RuntimeError(
                f"窗口尺寸异常，无法截图: rect=({left},{top},{right},{bottom})"
            )

        if save_debug:
            print(f"  [debug] window rect: {win_w}x{win_h}  (left={left}, top={top})")

        entries = self._load_label_file(label_file, classes_file)

        if save_debug:
            os.makedirs(debug_dir, exist_ok=True)

        result: Dict[str, str] = {}
        for label, x1n, y1n, x2n, y2n in entries:
            x1 = x1n * win_w
            y1 = y1n * win_h
            x2 = x2n * win_w
            y2 = y2n * win_h
            box = BBox(x1=x1, y1=y1, x2=x2, y2=y2, name=label)
            if save_debug:
                crop = self._screenshot(box)
                if crop is None or crop.size == 0:
                    print(
                        f"  [debug] SKIP {label}: empty crop "
                        f"(box pixel: x1={x1:.0f} y1={y1:.0f} x2={x2:.0f} y2={y2:.0f})"
                    )
                else:
                    debug_path = os.path.join(debug_dir, f"debug_{label}.png")
                    cv2.imwrite(debug_path, crop)
                    print(
                        f"  [debug] saved {debug_path}  "
                        f"size={crop.shape[1]}x{crop.shape[0]}  "
                        f"(box pixel: x1={x1:.0f} y1={y1:.0f} x2={x2:.0f} y2={y2:.0f})"
                    )
            ocr_boxes = self.ocr(box, scale=self._auto_scale(x2 - x1, y2 - y1))
            result[label] = " ".join(b.name for b in ocr_boxes if b.name)

        return result


if __name__ == "__main__":
    # 1. 简单测试：激活游戏窗口，读取各标注区域的文字
    # import sys
    # import os

    # sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # from tools.window import WindowManager

    # wm = WindowManager()
    # windows = wm.getAllWindows()

    # target = next((hw for hw, title in windows if "新天龙八部" in title), None)
    # if target is None:
    #     print("未找到游戏窗口")
    # else:
    #     print(f"找到窗口句柄: {target}")
    #     utils = ImageUtils(hwnd=target)
    #     regions = utils.read_labeled_regions(
    #         label_file="assets/images/1.json",
    #         save_debug=True,
    #     )
    #     for name, text in regions.items():
    #         print(f"  {name}: {text}")

    # 2. 测试 match_template()：判断当前游戏是否在参考图所在场景
    import sys
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tools.window import WindowManager

    wm = WindowManager()
    windows = wm.getAllWindows()

    target = next((hw for hw, title in windows if "新天龙八部" in title), None)
    if target is None:
        print("未找到游戏窗口")
    else:
        print(f"找到窗口句柄: {target}")
        utils = ImageUtils(hwnd=target)
        utils.activate()

        match = utils.match_template(
            label_json="assets/images/1.json",
            label="zuo_biao",
            threshold=0.7,
            save_debug=True,
        )
        if match:
            print(f"场景匹配成功！置信度: {match.confidence:.3f}  位置: {match}")
        else:
            print("当前不在参考场景中（低于阈值）")
