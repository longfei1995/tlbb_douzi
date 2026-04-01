import os
import sys
from tools.config import kShouLingYoloDir, kRootDir
from ultralytics import YOLO


if __name__ == "__main__":
    # 加载预训练模型
    model = YOLO("yolo26n.pt")

    # 训练模型
    yaml_path = os.path.join(kShouLingYoloDir, "data.yaml")
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