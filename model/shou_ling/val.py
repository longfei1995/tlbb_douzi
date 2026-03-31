# 添加根目录的路径
import os
from pyexpat import model
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.config import kRootDir, kShouLingDir
from ultralytics import YOLO


if __name__ == "__main__":
    # 加载训练好的模型
    model_path = os.path.join(kRootDir, "model", "shou_ling", "runs", "train", "shou_ling_yolo26n", "weights", "best.pt")
    model = YOLO(model_path)
    yaml_path = os.path.join(kShouLingDir, "data.yaml")
    
    # # 验证模型
    # print(f"验证数据配置路径: {yaml_path}")
    # results = model.val(data=yaml_path)
    
    # # 输出验证结果
    # print("验证结果:")
    # print(f"mAP@0.5: {results.box.map50:.4f}")
    # print(f"mAP@0.5:0.95: {results.box.map:.4f}")
    # print(f"Precision: {results.box.mp:.4f}")
    # print(f"Recall: {results.box.mr:.4f}")
    
    # 进行推理测试
    image_path = os.path.join(kShouLingDir, "val", "images", "8.png")
    results = model(image_path)
    
    # 输出推理结果
    for result in results:
        print(f"图像: {result.path}")
        print(f"检测到的对象数量: {len(result.boxes)}")
        for box in result.boxes:
            print(f"类别: {box.cls}, 置信度: {box.conf:.4f}, 坐标: {box.xyxy}")
        result.show()
        result.save(os.path.join(kRootDir, "model", "shou_ling", "runs", "val", "inference"))
    