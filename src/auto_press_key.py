import os
import sys
import threading

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import yaml

from tools.config import kRootDir
from tools.keyboard import KeyboardSimulator

_KEYCONFIG_PATH = os.path.join(kRootDir, "assets", "keyconfig.yaml")


class AutoPressKey:
    def __init__(self):
        self._stop_event = threading.Event()
        self._keyboard = KeyboardSimulator()

    def stop(self):
        """通知 base_press 循环停止。"""
        self._stop_event.set()

    def base_press(
        self,
        hwnd: int,
        key_interval: float = 0.1,
        loop_sleep: float = 1.0,
    ) -> None:
        """循环读取 keyconfig.yaml 配置，依次按下所有非空按键，直到 stop() 被调用。

        Args:
            hwnd: 目标窗口句柄。
            key_interval: 每两个按键之间的间隔时间（秒）。
            loop_sleep: 每次循环结束后的休眠时间（秒）。
        """
        self._stop_event.clear()
        print("[自动按键] 开始运行")
        while not self._stop_event.is_set():
            try:
                with open(_KEYCONFIG_PATH, encoding="utf-8") as f:
                    config: dict = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[自动按键] 读取配置失败: {e}")
                break

            for action, key in config.items():
                if self._stop_event.is_set():
                    break
                if not key or not str(key).strip():
                    continue
                self._keyboard.press_key(str(key).strip(), hwnd)
                if key_interval > 0:
                    self._stop_event.wait(key_interval)

            if not self._stop_event.is_set() and loop_sleep > 0:
                self._stop_event.wait(loop_sleep)

        print("[自动按键] 已停止")
