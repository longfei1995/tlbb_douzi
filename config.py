import os 

# 获取当前脚本所在目录
kMainDir = os.path.dirname(os.path.abspath(__file__))
# 定义资源目录
kImageDir = os.path.join(kMainDir, "assets", "images")
ktmpImageDir = os.path.join(kMainDir, "assets", "tmp_images")