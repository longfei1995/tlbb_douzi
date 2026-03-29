import sys
import time
from PySide6.QtCore import QThread, Signal

from src.task.game_param import kHPBar, kMPBar, kDefaultKey, kProfilePhoto
from src.task.color_detector import ColorDetector
from src.task.keyboard_simulator import KeyboardSimulator
from src.task.dig_seed import DigSeed
from src.task.auto_return import AutoReturn


class UILogStream:
    """将 print() 输出重定向到 UI 日志面板"""

    def __init__(self, log_callback):
        self.log_callback = log_callback

    def write(self, text):
        if text.strip():
            self.log_callback(text.strip())

    def flush(self):
        pass


class RaidThread(QThread):
    """自动团本循环按键线程"""

    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(
        self,
        hwnd: int,
        key_interval: float,
        sleep_time: float,
        is_em: bool,
        key_sequence: str,
    ):
        super().__init__()
        self.hwnd = hwnd
        self.running = True
        self.key_interval = key_interval
        self.sleep_time = sleep_time
        self.is_em = is_em
        self.key_sequence = key_sequence

    def run(self):
        original_stdout = sys.stdout
        try:
            sys.stdout = UILogStream(self.log_signal.emit)
            self.autoKeyPress(self.hwnd)
        except Exception as e:
            self.log_signal.emit(f"错误：{e}")
        finally:
            sys.stdout = original_stdout
            self.finished_signal.emit()

    def autoKeyPress(self, hwnd: int):
        """自动按键主循环"""
        color_detector = ColorDetector()
        keyboard_simulator = KeyboardSimulator()
        keys = self.key_sequence.split()
        if not keys:
            print("按键序列为空，无法执行")
            return

        cycle_count = 0
        while self.running:
            cycle_count += 1
            if cycle_count > 100000:
                print("按键循环超过10w次，重置循环")
                cycle_count = 0
            print(f"=== 第 {cycle_count} 轮按键开始 ===")

            for i, key in enumerate(keys):
                if not self.running:
                    print("收到停止信号，退出按键循环")
                    return
                keyboard_simulator.pressKey(key, hwnd)
                if i < len(keys) - 1:
                    time.sleep(self.key_interval)

            # 每20轮召唤宠物
            if cycle_count % 20 == 0:
                keyboard_simulator.pressKey(kDefaultKey.pet_attack, hwnd)
            keyboard_simulator.pressKey(kDefaultKey.pet_eat, hwnd)

            # 自己蓝量为空时点击血迹
            mp_color = color_detector.getPixelPosColorInWindow(
                hwnd, kMPBar.player1.x, kMPBar.player1.y
            )
            if color_detector.isEmpty(mp_color):
                keyboard_simulator.pressKey(kDefaultKey.xue_ji, hwnd)

            # 峨眉治疗逻辑
            if self.is_em:
                players = [
                    (
                        kHPBar.p1_low,
                        kHPBar.p1_mid,
                        kHPBar.p1_high,
                        kProfilePhoto.player1,
                    ),
                    (
                        kHPBar.p2_low,
                        kHPBar.p2_mid,
                        kHPBar.p2_high,
                        kProfilePhoto.player2,
                    ),
                    (
                        kHPBar.p3_low,
                        kHPBar.p3_mid,
                        kHPBar.p3_high,
                        kProfilePhoto.player3,
                    ),
                    (
                        kHPBar.p4_low,
                        kHPBar.p4_mid,
                        kHPBar.p4_high,
                        kProfilePhoto.player4,
                    ),
                    (
                        kHPBar.p5_low,
                        kHPBar.p5_mid,
                        kHPBar.p5_high,
                        kProfilePhoto.player5,
                    ),
                    (
                        kHPBar.p6_low,
                        kHPBar.p6_mid,
                        kHPBar.p6_high,
                        kProfilePhoto.player6,
                    ),
                ]

                def is_red(pt):
                    return color_detector.isRed(
                        color_detector.getPixelPosColorInWindow(hwnd, pt.x, pt.y)
                    )

                healed = False
                # 第一优先级：紧急治疗（血量不足中等水平）
                for idx, (low_pt, mid_pt, high_pt, photo_pt) in enumerate(players):
                    if is_red(low_pt) and not is_red(mid_pt):
                        print(f"p{idx+1}血量不足中等水平，紧急治疗")
                        keyboard_simulator.mouseClick(photo_pt.x, photo_pt.y, hwnd)
                        keyboard_simulator.pressKey(kDefaultKey.qing_xin, hwnd)
                        healed = True
                        break

                # 第二优先级：预防性治疗（血量中等但未满）
                if not healed:
                    for idx, (low_pt, mid_pt, high_pt, photo_pt) in enumerate(players):
                        if is_red(low_pt) and is_red(mid_pt) and not is_red(high_pt):
                            print(f"p{idx+1}血量中等，预防性加血")
                            keyboard_simulator.mouseClick(photo_pt.x, photo_pt.y, hwnd)
                            keyboard_simulator.pressKey(kDefaultKey.qing_xin, hwnd)
                            healed = True
                            break

                if not healed:
                    print("所有队友血量充足，无需治疗")
                time.sleep(0.8)  # 清心普善咒有CD

            print(f"第 {cycle_count} 轮完成，休眠 {self.sleep_time} 秒...")
            time.sleep(self.sleep_time)
            if not self.running:
                print("***** 休眠中收到停止信号，退出 *****")
                return

        print("***** 自动按键循环结束 *****")

    def stop(self):
        self.running = False


class DigSeedThread(QThread):
    """挖种子线程"""

    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(self, hwnd: int, seed_level: int, loop_count: int, is_dig_seed: bool):
        super().__init__()
        self.hwnd = hwnd
        self.seed_level = seed_level
        self.loop_count = loop_count
        self.is_dig_seed = is_dig_seed
        self.running = True

    def run(self):
        original_stdout = sys.stdout
        try:
            sys.stdout = UILogStream(self.log_signal.emit)
            self.digSeedProcess()
        except Exception as e:
            self.log_signal.emit(f"错误：{e}")
        finally:
            sys.stdout = original_stdout
            self.finished_signal.emit()

    def digSeedProcess(self):
        print(f"开始任务... 种子等级: {self.seed_level}, 循环次数: {self.loop_count}")
        start_task = "挖种子" if self.is_dig_seed else "打怪"
        print(f"任务模式: 从{start_task}开始，挖种子和打怪交替进行")

        dig_seed = DigSeed(self.hwnd, stop_check_func=lambda: not self.running)

        for i in range(self.loop_count):
            if not self.running:
                print("收到停止信号，退出任务循环")
                return

            # 根据起始任务和轮次决定当前任务类型
            current_is_dig = (i % 2 == 0) if self.is_dig_seed else (i % 2 == 1)
            current_name = "挖种子" if current_is_dig else "打怪"
            print(f"=== 第 {i+1}/{self.loop_count} 轮{current_name}开始 ===")

            try:
                success = dig_seed.digSeed(
                    seed_level=self.seed_level, is_dig_seed=current_is_dig
                )
                if success:
                    print(f"第 {i+1} 轮{current_name}完成")
                elif not self.running:
                    print(f"第 {i+1} 轮{current_name}被中断")
                    return
                else:
                    print(f"第 {i+1} 轮{current_name}失败，下马")
                    dig_seed.getDownHorse()
            except Exception as e:
                print(f"第 {i+1} 轮{current_name}异常: {e}")
                if not self.running:
                    print("检测到停止信号，退出任务循环")
                    return

            if i < self.loop_count - 1 and self.running:
                print("等待1秒后开始下一轮...")
                time.sleep(1)

        print("***** 任务完成 *****")

    def stop(self):
        self.running = False


class AutoReturnThread(QThread):
    """自动回点线程"""

    log_signal = Signal(str)
    finished_signal = Signal()

    def __init__(
        self,
        hwnd: int,
        scene_type: str,
        x: str,
        y: str,
        is_return_immediately: bool,
        interval_time: int,
    ):
        super().__init__()
        self.hwnd = hwnd
        self.scene_type = scene_type
        self.x = x
        self.y = y
        self.is_return_immediately = is_return_immediately
        self.interval_time = interval_time
        self.running = True

    def run(self):
        original_stdout = sys.stdout
        try:
            sys.stdout = UILogStream(self.log_signal.emit)
            self.autoReturnProcess()
        except Exception as e:
            self.log_signal.emit(f"错误：{e}")
        finally:
            sys.stdout = original_stdout
            self.finished_signal.emit()

    def autoReturnProcess(self):
        print(f"开始自动回点... 场景: {self.scene_type}, 坐标: ({self.x}, {self.y})")
        print(
            f"死亡后立即起身: {'是' if self.is_return_immediately else '否'}, 循环间隔: {self.interval_time}秒"
        )
        auto_return = AutoReturn(self.hwnd)
        cycle_count = 0

        while self.running:
            cycle_count += 1
            print(f"=== 第 {cycle_count} 轮回点开始，间隔 {self.interval_time} 秒 ===")

            try:
                if self.scene_type == "雪原":
                    auto_return.toXueYuan(self.x, self.y, self.is_return_immediately)
                elif self.scene_type == "四象":
                    if cycle_count == 1:
                        auto_return._getUpHorse()
                        time.sleep(1)
                    auto_return.toSiXiang()
                elif self.scene_type == "苗人洞":
                    auto_return.toMiaoRenDong(
                        self.x, self.y, self.is_return_immediately
                    )
                else:
                    print(f"暂不支持场景: {self.scene_type}")
            except Exception as e:
                print(f"第 {cycle_count} 轮异常: {e}")
                if not self.running:
                    print("检测到停止信号，退出回点循环")
                    return

            if self.running:
                print(f"第 {cycle_count} 轮完成，等待 {self.interval_time} 秒...")
                for _ in range(self.interval_time):
                    if not self.running:
                        print("***** 等待中收到停止信号 *****")
                        return
                    time.sleep(1)

        print("***** 自动回点循环结束 *****")

    def stop(self):
        self.running = False
