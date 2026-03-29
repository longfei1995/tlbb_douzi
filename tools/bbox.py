class Point:
    def __init__(self):
        self.x: int = 0
        self.y: int = 0
        
        
class BBox:
    def __init__(self, x:int=0, y:int=0, to_x:int=0, to_y:int=0):
        """Bounding box.
        Args:
            x (int): 左上角的x坐标
            y (int): 左上角的y坐标
            to_x (int, optional): 右下角的x坐标. Defaults to 0.
            to_y (int, optional): 右下角的y坐标. Defaults to 0.
        """
        self.__x = x
        self.__y = y
        self.__to_x = to_x
        self.__to_y = to_y
        
    def get_left_top(self) -> Point:
        """获取左上角坐标
        Returns:
            Point: 左上角坐标
        """
        point = Point()
        point.x = self.__x
        point.y = self.__y
        return point
    
    def get_right_bottom(self) -> Point:
        """获取右下角坐标
        Returns:
            Point: 右下角坐标
        """
        point = Point()
        point.x = self.__to_x
        point.y = self.__to_y
        return point
    @property
    def width(self) -> int:
        """获取宽度
        Returns:
            int: 宽度
        """        
        return self.__to_x - self.__x    
    
    @property
    def height(self) -> int:
        """获取高度 
        Returns:
            int: 高度
        """        
        return self.__to_y - self.__y
    
    @property
    def center(self) -> Point:
        """获取中心点坐标
        Returns:
            Point: 中心点坐标
        """        
        point = Point()
        point.x = self.__x + self.width // 2
        point.y = self.__y + self.height // 2
        return point
    
        