from pathlib import Path
import os
# 获取当前文件的上一级目录作为主目录
kRootDir = Path(__file__).parents[1].resolve()
# 定义资源目录
kShouLingDir = os.path.join(kRootDir, "assets", "images", "shou_ling", "yolo")


if __name__ == "__main__":
    print(f"kRootDir: {kRootDir}")
    print(f"kShouLingDir: {kShouLingDir}")