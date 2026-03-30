from typing import List, Optional, Dict, Union
import numpy as np

class BBox:
    """Bounding Box 类，包含左上角和右下角坐标"""

    def __init__(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        name: Optional[str] = None,
        confidence: float = 1.0,
    ):
        """
        初始化 BBox 对象

        参数:
            x1: 左上角 x 坐标
            y1: 左上角 y 坐标
            x2: 右下角 x 坐标
            y2: 右下角 y 坐标
            name: 类别名称或识别文本，默认为 None
            confidence: 置信度，默认为 1.0
        """
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.name = name
        self.confidence = confidence

    @property
    def width(self) -> float:
        """获取宽度"""
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        """获取高度"""
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        """获取面积"""
        return self.width * self.height

    @property
    def center(self) -> tuple[float, float]:
        """获取中心点坐标"""
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    def get_roi(self, image: np.ndarray) -> np.ndarray:
        """从图像中提取该 BBox 区域"""
        x1, y1, x2, y2 = self.int_coords()
        return image[y1:y2, x1:x2]

    def int_coords(self) -> tuple[int, int, int, int]:
        """获取整数坐标，用于 OpenCV 操作"""
        return (int(self.x1), int(self.y1), int(self.x2), int(self.y2))

    def __repr__(self) -> str:
        """字符串表示"""
        return f"BBox(x1={self.x1:.1f}, y1={self.y1:.1f}, x2={self.x2:.1f}, y2={self.y2:.1f}, name={self.name}, conf={self.confidence:.2f})"
