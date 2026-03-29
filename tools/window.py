import ctypes
import os
from typing import List, Optional, Tuple
import win32api
import win32con
import win32gui


class WindowManager:
    """Windows窗口管理器"""

    def __init__(self):
        self.windows = []

    def isAdmin(self) -> bool:
        """检查当前程序是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def getAllWindows(self) -> List[Tuple[int, str]]:
        """获取所有可见窗口的句柄和标题"""
        self.windows = []

        def enum_windows_callback(hwnd, lParam):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                self.windows.append((hwnd, window_title))
            return True

        win32gui.EnumWindows(enum_windows_callback, 0)
        return self.windows

    def activateWindow(self, hwnd: int) -> bool:
        """
        激活指定窗口。
        若窗口已最小化则还原，否则只发送 WM_ACTIVATE 消息，
        不修改窗口大小、位置或 Z 序。
        """
        try:
            if not win32gui.IsWindow(hwnd):
                print("窗口句柄无效")
                return False

            # 仅在最小化时才调用 SW_RESTORE，避免不必要的窗口尺寸变化
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                print("窗口已从最小化还原")
            else:
                # 发送激活消息（不强制前台，不改变大小）
                win32api.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                print("已发送激活消息（后台激活，不改变窗口大小）")
            return True

        except Exception as e:
            print(f"激活窗口失败: {e}")
            return False
