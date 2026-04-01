from pyexpat import model
import sys

# sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.config import kRootDir, kShouLingYoloDir
from ultralytics import YOLO


if __name__ == "__main__":
    print(f"根目录路径: {kRootDir}")
    print(f"手灵YOLO目录路径: {kShouLingYoloDir}")
    