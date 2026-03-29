import os
import time
import random
from pathlib import Path
from config import kMainDir
import win32api
import win32con
import win32gui


class MouseSimulator:
    """鼠标模拟器，通过 win32api 向指定窗口发送鼠标消息。"""

    def __init__(self):
        lock_dir = self._get_lock_dir()
        self.lock_file = lock_dir / "tlbb_mouse_lock.txt"
        self.lock_timeout = 10
        self.lock_file_handle = None

    def _get_lock_dir(self) -> Path:
        """返回锁文件目录（项目根目录下的 locks/ 子目录）。"""
        lock_dir = Path(kMainDir) / "locks"
        try:
            lock_dir.mkdir(parents=True, exist_ok=True)
            test_file = lock_dir / "test_write.tmp"
            test_file.write_text("test")
            test_file.unlink()
            return lock_dir
        except Exception as e:
            raise RuntimeError(f"无法创建锁文件目录 {lock_dir}: {e}") from e

    def _get_lock_owner_info(self) -> str:
        """读取锁文件中的占用者信息。"""
        try:
            if not self.lock_file.exists():
                return "锁文件不存在"
            with open(self.lock_file, "r") as f:
                content = f.read().strip()
            if not content:
                return "锁文件为空"
            lines = content.split("\n")
            if len(lines) >= 2:
                try:
                    elapsed = time.time() - float(lines[0])
                    return f"占用进程ID: {lines[1]}, 持有时间: {elapsed:.1f}秒"
                except ValueError:
                    return f"占用进程ID: {lines[1]}, 时间戳格式错误"
            return f"锁文件格式异常: {content[:50]}"
        except Exception as e:
            return f"读取锁文件失败: {e}"

    def _get_mouse_lock(self) -> bool:
        """尝试获取鼠标锁，最多重试 300 次。"""
        max_retries = 300
        retry_count = 0

        while retry_count < max_retries:
            try:
                handle = open(str(self.lock_file), "x")
                try:
                    handle.write(f"{time.time()}\n{os.getpid()}")
                    handle.flush()
                    self.lock_file_handle = handle
                    return True
                except Exception as e:
                    print(f"[鼠标锁] 写入锁文件失败: {e}")
                    try:
                        handle.close()
                        os.remove(str(self.lock_file))
                    except Exception:
                        pass
                    time.sleep(0.05)
                    retry_count += 1
                    continue

            except FileExistsError:
                if retry_count % 50 == 0:
                    print(
                        f"[鼠标锁] 锁被占用，等待中 - PID: {os.getpid()}, "
                        f"重试: {retry_count}, {self._get_lock_owner_info()}"
                    )
                if self._check_lock_timeout():
                    continue
                time.sleep(0.1)
                retry_count += 1

            except Exception as e:
                if retry_count % 50 == 0:
                    print(f"[鼠标锁] 获取锁异常: {e}, 重试: {retry_count}")
                time.sleep(0.1)
                retry_count += 1

        print(f"[鼠标锁] 超过 {max_retries} 次重试，强制清理锁文件")
        self._force_release_lock()
        try:
            handle = open(str(self.lock_file), "x")
            handle.write(f"{time.time()}\n{os.getpid()}")
            handle.flush()
            self.lock_file_handle = handle
            return True
        except Exception as e:
            print(f"[鼠标锁] 强制清理后仍无法获取锁: {e}")
            return False

    def _check_lock_timeout(self) -> bool:
        """检查锁是否超时；超时则强制释放并返回 True。"""
        try:
            if not self.lock_file.exists():
                return True
            with open(self.lock_file, "r") as f:
                content = f.read().strip()
            if not content:
                self._force_release_lock()
                return True
            lines = content.split("\n")
            try:
                lock_time = float(lines[0])
            except ValueError:
                self._force_release_lock()
                return True

            if time.time() - lock_time > self.lock_timeout:
                lock_pid = lines[1] if len(lines) > 1 else "未知"
                print(f"[鼠标锁] 锁超时（{self.lock_timeout}s），占用 PID: {lock_pid}")
                self._force_release_lock()
                return True

            if len(lines) > 1:
                try:
                    if int(lines[1]) == os.getpid():
                        self._force_release_lock()
                        return True
                except ValueError:
                    pass

            return False
        except Exception:
            self._force_release_lock()
            return True

    def _force_release_lock(self):
        """强制删除锁文件。"""
        try:
            if hasattr(self, "lock_file_handle") and self.lock_file_handle:
                try:
                    self.lock_file_handle.close()
                except Exception:
                    pass
                self.lock_file_handle = None

            if self.lock_file.exists():
                for attempt in range(3):
                    try:
                        os.remove(str(self.lock_file))
                        return
                    except PermissionError:
                        if attempt < 2:
                            time.sleep(0.1)
                    except FileNotFoundError:
                        return
                    except Exception:
                        if attempt < 2:
                            time.sleep(0.1)
        except Exception as e:
            print(f"[鼠标锁] 强制释放失败: {e}")

    def _release_mouse_lock(self):
        """正常释放鼠标锁。"""
        try:
            if self.lock_file_handle:
                self.lock_file_handle.close()
                self.lock_file_handle = None
        except Exception as e:
            print(f"[鼠标锁] 关闭句柄失败: {e}")
        try:
            if self.lock_file.exists():
                os.remove(str(self.lock_file))
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"[鼠标锁] 释放锁文件失败: {e}")

    @staticmethod
    def _resolve_flags(button: str):
        """根据按键名称返回 (down_flag, up_flag)，不合法返回 None。"""
        button = button.lower()
        mapping = {
            "left": (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
            "right": (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
            "middle": (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
        }
        return mapping.get(button)

    @staticmethod
    def _activate_window(hwnd: int):
        """激活或还原窗口。"""
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            time.sleep(0.2)
        else:
            win32api.PostMessage(hwnd, win32con.WM_ACTIVATE, win32con.WA_ACTIVE, 0)
            time.sleep(0.1)

    def click(self, x: int, y: int, hwnd: int, button: str = "left") -> bool:
        """对指定窗口执行单击（加锁保护）。

        Args:
            x: 相对于窗口客户区左上角的 X 坐标（像素）。
            y: 相对于窗口客户区左上角的 Y 坐标（像素）。
            hwnd: 目标窗口句柄。
            button: 鼠标按键，"left" / "right" / "middle"。
        """
        if not self._get_mouse_lock():
            print("[鼠标锁] 无法获取锁，单击取消")
            return False
        try:
            return self._click(x, y, hwnd, button)
        finally:
            self._release_mouse_lock()

    def _click(self, x: int, y: int, hwnd: int, button: str) -> bool:
        """单击的内部实现（不加锁）。"""
        if hwnd <= 0:
            return False
        flags = self._resolve_flags(button)
        if flags is None:
            print(f"未知按键: {button}")
            return False
        try:
            rect = win32gui.GetWindowRect(hwnd) # 获取窗口在屏幕上的绝对位置，包括标题栏和边框
            self._activate_window(hwnd)
            win32api.SetCursorPos((rect[0] + x, rect[1] + y))
            down_flag, up_flag = flags
            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(random.uniform(0.08, 0.12))
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            return True
        except Exception as e:
            print(f"单击失败: {e}")
            return False

    # ------------------------------------------------------------------
    # 双击
    # ------------------------------------------------------------------

    def double_click(self, x: int, y: int, hwnd: int, button: str = "left") -> bool:
        """对指定窗口执行双击（加锁保护）。

        Args:
            x: 相对于窗口客户区左上角的 X 坐标（像素）。
            y: 相对于窗口客户区左上角的 Y 坐标（像素）。
            hwnd: 目标窗口句柄。
            button: 鼠标按键，"left" / "right" / "middle"。
        """
        if not self._get_mouse_lock():
            print("[鼠标锁] 无法获取锁，双击取消")
            return False
        try:
            return self._double_click(x, y, hwnd, button)
        finally:
            self._release_mouse_lock()

    def _double_click(self, x: int, y: int, hwnd: int, button: str) -> bool:
        """双击的内部实现（不加锁）。"""
        if hwnd <= 0:
            return False
        flags = self._resolve_flags(button)
        if flags is None:
            print(f"未知按键: {button}")
            return False
        try:
            rect = win32gui.GetWindowRect(hwnd)
            self._activate_window(hwnd)
            win32api.SetCursorPos((rect[0] + x, rect[1] + y))
            down_flag, up_flag = flags
            # 第一次点击
            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(random.uniform(0.08, 0.12))
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            time.sleep(0.18)
            # 第二次点击
            win32api.mouse_event(down_flag, 0, 0, 0, 0)
            time.sleep(random.uniform(0.08, 0.12))
            win32api.mouse_event(up_flag, 0, 0, 0, 0)
            return True
        except Exception as e:
            print(f"双击失败: {e}")
            return False
