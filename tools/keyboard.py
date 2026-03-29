import time
import random
from typing import Union

import win32api
import win32con


class KeyboardSimulator:
    """键盘模拟器，通过 win32api.PostMessage 向指定窗口发送键盘消息。"""

    # 虚拟键码映射表
    _VIRTUAL_KEY_CODE = {
        # 字母键
        "A": 0x41,
        "B": 0x42,
        "C": 0x43,
        "D": 0x44,
        "E": 0x45,
        "F": 0x46,
        "G": 0x47,
        "H": 0x48,
        "I": 0x49,
        "J": 0x4A,
        "K": 0x4B,
        "L": 0x4C,
        "M": 0x4D,
        "N": 0x4E,
        "O": 0x4F,
        "P": 0x50,
        "Q": 0x51,
        "R": 0x52,
        "S": 0x53,
        "T": 0x54,
        "U": 0x55,
        "V": 0x56,
        "W": 0x57,
        "X": 0x58,
        "Y": 0x59,
        "Z": 0x5A,
        # 数字键
        "0": 0x30,
        "1": 0x31,
        "2": 0x32,
        "3": 0x33,
        "4": 0x34,
        "5": 0x35,
        "6": 0x36,
        "7": 0x37,
        "8": 0x38,
        "9": 0x39,
        # 功能键
        "F1": 0x70,
        "F2": 0x71,
        "F3": 0x72,
        "F4": 0x73,
        "F5": 0x74,
        "F6": 0x75,
        "F7": 0x76,
        "F8": 0x77,
        "F9": 0x78,
        "F10": 0x79,
        "F11": 0x7A,
        "F12": 0x7B,
        # 特殊键
        "SPACE": 0x20,
        "ENTER": 0x0D,
        "TAB": 0x09,
        "ESC": 0x1B,
        "BACKSPACE": 0x08,
        "DELETE": 0x2E,
        "INSERT": 0x2D,
        "HOME": 0x24,
        "END": 0x23,
        "PAGEUP": 0x21,
        "PAGEDOWN": 0x22,
        # 方向键
        "LEFT": 0x25,
        "UP": 0x26,
        "RIGHT": 0x27,
        "DOWN": 0x28,
        # 修饰键
        "SHIFT": 0x10,
        "CTRL": 0x11,
        "ALT": 0x12,
        "WIN": 0x5B,
        "LSHIFT": 0xA0,
        "RSHIFT": 0xA1,
        "LCTRL": 0xA2,
        "RCTRL": 0xA3,
        "LALT": 0xA4,
        "RALT": 0xA5,
        # 小键盘
        "NUMPAD0": 0x60,
        "NUMPAD1": 0x61,
        "NUMPAD2": 0x62,
        "NUMPAD3": 0x63,
        "NUMPAD4": 0x64,
        "NUMPAD5": 0x65,
        "NUMPAD6": 0x66,
        "NUMPAD7": 0x67,
        "NUMPAD8": 0x68,
        "NUMPAD9": 0x69,
        "MULTIPLY": 0x6A,
        "ADD": 0x6B,
        "SUBTRACT": 0x6D,
        "DECIMAL": 0x6E,
        "DIVIDE": 0x6F,
        # 符号键
        "`": 0xC0,
        "~": 0xC0,
        # 其他
        "CAPSLOCK": 0x14,
        "NUMLOCK": 0x90,
        "SCROLLLOCK": 0x91,
        "PAUSE": 0x13,
        "PRINTSCREEN": 0x2C,
    }

    def _get_virtual_key_code(self, key: Union[str, int]) -> int:
        """将按键名称或键码转换为虚拟键码；未知键名返回 0。"""
        if isinstance(key, int):
            return key
        return self._VIRTUAL_KEY_CODE.get(key.upper(), 0)

    def press_key(self, key: Union[str, int], hwnd: int) -> bool:
        """向目标窗口发送一次按键（按下后释放）。

        Args:
            key: 按键名称（如 "ENTER"、"A"）或虚拟键码整数。
            hwnd: 目标窗口句柄。
        """
        vk = self._get_virtual_key_code(key)
        if vk == 0:
            print(f"未知按键: {key}")
            return False
        try:
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
            time.sleep(random.uniform(0.08, 0.12))
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)
            return True
        except Exception as e:
            print(f"按键失败 [{key}]: {e}")
            return False

    def press_combo(self, keys: list, hwnd: int) -> bool:
        """向目标窗口发送组合键，例如 ["CTRL", "C"]。

        keys 列表中最后一个元素作为主键，其余视为修饰键。
        修饰键按顺序按下，主键按下并释放，修饰键再逆序释放。

        Args:
            keys: 按键名称列表，如 ["CTRL", "SHIFT", "S"]。
            hwnd: 目标窗口句柄。
        """
        if not keys:
            return False

        vk_codes = []
        for key in keys:
            vk = self._get_virtual_key_code(key)
            if vk == 0:
                print(f"未知按键: {key}")
                return False
            vk_codes.append(vk)

        modifiers = vk_codes[:-1]
        main_key = vk_codes[-1]

        try:
            # 按下所有修饰键
            for vk in modifiers:
                win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk, 0)
                time.sleep(0.05)

            # 按下并释放主键
            win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, main_key, 0)
            time.sleep(random.uniform(0.08, 0.12))
            win32api.PostMessage(hwnd, win32con.WM_KEYUP, main_key, 0)
            time.sleep(0.05)

            # 逆序释放修饰键
            for vk in reversed(modifiers):
                win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk, 0)
                time.sleep(0.05)

            return True
        except Exception as e:
            print(f"组合键失败 {keys}: {e}")
            return False
