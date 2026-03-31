# 添加根目录的路径
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
from tools.config import kShouLingDir, kRootDir
from ultralytics import YOLO


if __name__ == "__main__":
    # 加载预训练模型
    model = YOLO("yolo26n.pt")

    # 训练模型
    yaml_path = os.path.join(kShouLingDir, "data.yaml")
    project_dir = os.path.join(kRootDir, "model", "shou_ling", "runs", "train")
    print(f"训练数据配置路径: {yaml_path}")
    print(f"训练输出路径: {project_dir}")
    model.train(
        data=yaml_path,
        epochs=100,
        imgsz=640,
        batch=16,
        device="cpu",
        name="shou_ling_yolo26n",
        project=project_dir,
    )