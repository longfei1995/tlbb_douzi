import win32api
import win32con
import win32gui
import time
import random
import os
import tempfile
from typing import Union, List
from pathlib import Path
import msvcrt


class KeyboardSimulator:
    """键盘模拟器"""

    # 虚拟键码映射表
    kVirtualKeyCode = {
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
        # 其他常用键
        "CAPSLOCK": 0x14,
        "NUMLOCK": 0x90,
        "SCROLLLOCK": 0x91,
        "PAUSE": 0x13,
        "PRINTSCREEN": 0x2C,
    }

    def __init__(self):
        lock_dir = self._getLockDir()
        self.lock_file = lock_dir / "tlbb_mouse_lock.txt"
        self.lock_timeout = 10
        self.lock_file_handle = None


    def _getLockDir(self) -> Path:
        """获取锁文件目录 — 使用程序根目录（tlbb/）下的 locks 子目录"""
        # 此文件位于 src/task/，向上两级到达 tlbb/ 根目录
        lock_dir = Path(__file__).parent.parent.parent / "locks"

        try:
            lock_dir.mkdir(parents=True, exist_ok=True)
            test_file = lock_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            print(f"[鼠标锁] 使用锁文件目录: {lock_dir}")
            return lock_dir
        except Exception as e:
            print(f"[鼠标锁] 无法使用程序目录 {lock_dir}: {e}")
            raise RuntimeError(f"无法创建锁文件目录: {e}") from e

    def _getLockOwnerInfo(self) -> str:
        """获取锁文件占用者信息"""
        try:
            if not self.lock_file.exists():
                return "锁文件不存在"
            with open(self.lock_file, "r") as f:
                content = f.read().strip()
                if not content:
                    return "锁文件为空"
                lines = content.split("\n")
                if len(lines) >= 2:
                    lock_time = lines[0]
                    lock_pid = lines[1]
                    try:
                        elapsed = time.time() - float(lock_time)
                        return f"占用进程ID: {lock_pid}, 持有时间: {elapsed:.1f}秒"
                    except ValueError:
                        return f"占用进程ID: {lock_pid}, 时间戳格式错误"
                return f"锁文件格式异常: {content[:50]}"
        except Exception as e:
            return f"读取锁文件失败: {e}"

    def _getMouseLock(self) -> bool:
        """获取鼠标锁"""
        max_retries = 300
        retry_count = 0

        while retry_count < max_retries:
            try:
                lock_file_handle = open(str(self.lock_file), "x")
                try:
                    lock_info = f"{time.time()}\n{os.getpid()}"
                    lock_file_handle.write(lock_info)
                    lock_file_handle.flush()
                    self.lock_file_handle = lock_file_handle
                    print(f"[鼠标锁] 成功获取锁 - 进程ID: {os.getpid()}")
                    return True
                except Exception as e:
                    print(f"[鼠标锁] 写入锁文件失败: {e}")
                    try:
                        lock_file_handle.close()
                        os.remove(str(self.lock_file))
                    except:
                        pass
                    time.sleep(0.05)
                    retry_count += 1
                    continue

            except FileExistsError:
                if retry_count % 50 == 0:
                    lock_owner_info = self._getLockOwnerInfo()
                    print(
                        f"[鼠标锁] 锁被占用，等待释放 - 当前进程ID: {os.getpid()}, 重试次数: {retry_count}, {lock_owner_info}"
                    )
                if self._checkLockTimeout():
                    continue
                else:
                    time.sleep(0.1)
                    retry_count += 1
                    continue

            except Exception as e:
                if retry_count % 50 == 0:
                    print(f"[鼠标锁] 获取锁时发生异常: {e}, 重试次数: {retry_count}")
                time.sleep(0.1)
                retry_count += 1
                continue

        print(f"[鼠标锁] 超过{max_retries}次获取锁失败，强制清理锁文件")
        self._forceReleaseLock()

        try:
            lock_file_handle = open(str(self.lock_file), "x")
            lock_info = f"{time.time()}\n{os.getpid()}"
            lock_file_handle.write(lock_info)
            lock_file_handle.flush()
            self.lock_file_handle = lock_file_handle
            print(f"[鼠标锁] 强制清理后成功获取锁 - 进程ID: {os.getpid()}")
            return True
        except Exception as e:
            print(f"[鼠标锁] 强制清理后，最终获取锁失败: {e}")
            return False

    def _checkLockTimeout(self) -> bool:
        """检查锁是否超时，如果超时则强制释放"""
        try:
            if not self.lock_file.exists():
                return True

            with open(self.lock_file, "r") as f:
                content = f.read().strip()
                if not content:
                    print(f"[鼠标锁] 发现空锁文件，强制释放")
                    self._forceReleaseLock()
                    return True

                lines = content.split("\n")
                if len(lines) < 1:
                    self._forceReleaseLock()
                    return True

                try:
                    lock_time = float(lines[0])
                except ValueError:
                    self._forceReleaseLock()
                    return True

                if time.time() - lock_time > self.lock_timeout:
                    lock_pid = lines[1] if len(lines) > 1 else "未知"
                    print(
                        f"[鼠标锁] 检测到锁超时（{self.lock_timeout}秒），占用锁的进程ID: {lock_pid}"
                    )
                    self._forceReleaseLock()
                    return True

                if len(lines) > 1:
                    try:
                        lock_pid = int(lines[1])
                        if lock_pid == os.getpid():
                            print(f"[鼠标锁] 发现同进程遗留锁，强制释放")
                            self._forceReleaseLock()
                            return True
                    except ValueError:
                        pass

            return False

        except Exception as e:
            self._forceReleaseLock()
            return True

    def _forceReleaseLock(self):
        """强制释放锁文件"""
        try:
            if hasattr(self, "lock_file_handle") and self.lock_file_handle:
                try:
                    self.lock_file_handle.close()
                    self.lock_file_handle = None
                except Exception as handle_e:
                    print(f"[鼠标锁] 关闭锁文件句柄失败: {handle_e}")

            if self.lock_file.exists():
                lock_file_path = str(self.lock_file)
                for attempt in range(3):
                    try:
                        os.remove(lock_file_path)
                        print(f"[鼠标锁] 强制释放锁文件成功")
                        return
                    except PermissionError as pe:
                        print(
                            f"[鼠标锁] 删除锁文件权限被拒绝 (尝试 {attempt + 1}/3): {pe}"
                        )
                        if attempt < 2:
                            time.sleep(0.1)
                    except FileNotFoundError:
                        return
                    except Exception as file_e:
                        if attempt < 2:
                            time.sleep(0.1)
        except Exception as e:
            print(f"[鼠标锁] 强制释放锁文件过程中发生未预期的错误: {e}")

    def _releaseMouseLock(self) -> None:
        """释放鼠标锁"""
        try:
            if self.lock_file_handle:
                try:
                    self.lock_file_handle.close()
                    self.lock_file_handle = None
                except Exception as handle_e:
                    print(f"[鼠标锁] 关闭锁文件句柄失败: {handle_e}")
        except Exception as e:
            print(f"[鼠标锁] 处理文件句柄时发生错误: {e}")

        try:
            if self.lock_file.exists():
                os.remove(str(self.lock_file))
                print(f"[鼠标锁] 释放锁成功 - 进程ID: {os.getpid()}")
            else:
                print(f"[鼠标锁] 锁文件已不存在 - 进程ID: {os.getpid()}")
        except PermissionError as pe:
            print(f"[鼠标锁] 释放锁文件权限被拒绝: {pe}")
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[鼠标锁] 释放锁文件失败: {e}")

    def _getVirtualKeyCode(self, key: str) -> int:
        """获取按键的虚拟键码"""
        key = key.upper()
        return self.kVirtualKeyCode.get(key, 0)

    def pressKey(self, key: Union[str, int], hwnd) -> bool:
        """按下并释放一个键"""
        try:
            if isinstance(key, str):
                vk_code = self._getVirtualKeyCode(key)
                if vk_code == 0:
                    print(f"未知按键: {key}")
                    return False
            else:
                vk_code = key
            try:
                win32api.PostMessage(hwnd, win32con.WM_KEYDOWN, vk_code, 0)
                time.sleep(random.uniform(0.08, 0.12))
                win32api.PostMessage(hwnd, win32con.WM_KEYUP, vk_code, 0)
                return True
            except Exception as e:
                print(f"异步发送失败: {e}")
                return False
        except Exception as e:
            print(f"按键失败: {e}")
            return False

    def mouseClick(self, x: int, y: int, hwnd: int = 0, button: str = "left") -> bool:
        """全局鼠标点击"""
        if not self._getMouseLock():
            print(f"[鼠标锁] 无法获取鼠标锁，鼠标点击失败")
            return False
        try:
            return self._mouceClick(x, y, hwnd, button)
        finally:
            self._releaseMouseLock()

    def _mouceClick(self, x: int, y: int, hwnd: int = 0, button: str = "left") -> bool:
        """执行鼠标点击的具体逻辑"""
        try:
            if hwnd <= 0:
                return False

            window_rect = win32gui.GetWindowRect(hwnd)
            window_origin_x, window_origin_y = window_rect[0], window_rect[1]

            # 若窗口已最小化，必须还原；否则只发送 WM_ACTIVATE 不改变窗口大小
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
            else:
                # 使用消息激活，不点击标题栏，避免窗口大小被修改
                win32api.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                time.sleep(0.1)

            target_screen_x = window_origin_x + x
            target_screen_y = window_origin_y + y

            win32api.SetCursorPos((target_screen_x, target_screen_y))

            if button.lower() == "left":
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            elif button.lower() == "right":
                down_flag = win32con.MOUSEEVENTF_RIGHTDOWN
                up_flag = win32con.MOUSEEVENTF_RIGHTUP
            elif button.lower() == "middle":
                down_flag = win32con.MOUSEEVENTF_MIDDLEDOWN
                up_flag = win32con.MOUSEEVENTF_MIDDLEUP
            else:
                return False

            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            return True

        except Exception as e:
            return False

    def mouseDoubleClick(
        self, x: int, y: int, hwnd: int = 0, button: str = "left"
    ) -> bool:
        """全局鼠标双击"""
        if not self._getMouseLock():
            print(f"[鼠标锁] 无法获取鼠标锁，跳过双击操作")
            return False
        try:
            return self._mouseDoubleClick(x, y, hwnd, button)
        finally:
            self._releaseMouseLock()

    def _mouseDoubleClick(
        self, x: int, y: int, hwnd: int = 0, button: str = "left"
    ) -> bool:
        """执行鼠标双击的具体逻辑"""
        try:
            if hwnd <= 0:
                return False

            window_rect = win32gui.GetWindowRect(hwnd)
            window_origin_x, window_origin_y = window_rect[0], window_rect[1]

            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                time.sleep(0.2)
            else:
                win32api.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
                time.sleep(0.1)

            target_screen_x = window_origin_x + x
            target_screen_y = window_origin_y + y

            win32api.SetCursorPos((target_screen_x, target_screen_y))

            if button.lower() == "left":
                down_flag = win32con.MOUSEEVENTF_LEFTDOWN
                up_flag = win32con.MOUSEEVENTF_LEFTUP
            elif button.lower() == "right":
                down_flag = win32con.MOUSEEVENTF_RIGHTDOWN
                up_flag = win32con.MOUSEEVENTF_RIGHTUP
            elif button.lower() == "middle":
                down_flag = win32con.MOUSEEVENTF_MIDDLEDOWN
                up_flag = win32con.MOUSEEVENTF_MIDDLEUP
            else:
                return False

            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            time.sleep(0.18)
            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(0.1)
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            return True

        except Exception as e:
            return False

    def typeChar(self, char: str, hwnd) -> bool:
        """输入字符 - 使用WM_CHAR消息"""
        try:
            if len(char) != 1:
                print(f"typeChar只能输入单个字符，收到: {char}")
                return False
            char_code = ord(char)
            win32api.PostMessage(hwnd, win32con.WM_CHAR, char_code, 0)
            time.sleep(random.uniform(0.05, 0.08))
            return True
        except Exception as e:
            print(f"字符输入失败: {e}")
            return False
