from pyexpat import model
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from tools.config import kRootDir, kShouLingDir
from ultralytics import YOLO


if __name__ == "__main__":
    