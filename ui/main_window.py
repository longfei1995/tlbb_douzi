import os
import sys

# Ensure the project root is on sys.path so that `config` and `tools` are
# importable regardless of how this file is invoked.
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QTextEdit,
    QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QCursor

from config import kMainDir
from tools.window import WindowManager
from ui.auto_press_ui import AutoKeyPanel


class NavButton(QPushButton):
    """Sidebar navigation button — icon emoji + label stacked vertically."""

    def __init__(self, icon_char: str, label: str, parent=None):
        super().__init__(f"{icon_char}\n{label}", parent)
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedWidth(70)


class UILogStream:
    """将 print() 输出重定向到 UI 日志面板。"""

    def __init__(self, log_callback):
        self.log_callback = log_callback

    def write(self, text):
        if text.strip():
            self.log_callback(text.strip())

    def flush(self):
        pass


class GameUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.hwnd: int = -1
        self.window_manager = WindowManager()

        # Buffer logs emitted before the log widget is created
        self._pending_logs: list = []
        self._original_stdout = sys.stdout
        sys.stdout = UILogStream(lambda msg: self._pending_logs.append(msg))

        self._initUI()

        # Flush buffered logs into the live widget, then keep redirecting
        for msg in self._pending_logs:
            self._appendLog(msg)
        self._pending_logs.clear()
        sys.stdout = UILogStream(self._appendLog)

    def closeEvent(self, event):
        self._autokey_panel.stop()
        sys.stdout = self._original_stdout
        super().closeEvent(event)

    # ── UI construction ──────────────────────────────────────────────────────

    def _initUI(self):
        self.setWindowTitle("豆子 — 天龙八部助手")
        self.setMinimumWidth(760)

        icon_path = os.path.join(kMainDir, "assets", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        qss_path = os.path.join(kMainDir, "ui", "styles.qss")
        if os.path.exists(qss_path):
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._buildHeader())
        vbox.addWidget(self._buildSeparator())
        vbox.addWidget(self._buildBody(), 1)
        vbox.addWidget(self._buildLogPanel())

        # Admin status — printed via stdout redirect so it lands in the log panel
        if self.window_manager.isAdmin():
            print("✓ 当前程序以管理员权限运行")
        else:
            print("⚠ 建议以管理员身份运行本程序（部分功能可能受限）")

    # ── Header ───────────────────────────────────────────────────────────────

    def _buildHeader(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(56)

        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(16, 0, 16, 0)
        hbox.setSpacing(8)

        title = QLabel("豆子")
        title.setObjectName("appTitle")
        hbox.addWidget(title)

        hbox.addSpacing(20)

        refresh_btn = QPushButton("刷新窗口")
        refresh_btn.setObjectName("headerBtn")
        refresh_btn.setFixedWidth(80)
        refresh_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        refresh_btn.clicked.connect(self._showAllWindows)
        hbox.addWidget(refresh_btn)

        self._window_combo = QComboBox()
        self._window_combo.addItem("请先刷新窗口列表", userData=-1)
        self._window_combo.setMinimumWidth(300)
        hbox.addWidget(self._window_combo)

        self._activate_btn = QPushButton("激活")
        self._activate_btn.setObjectName("accentBtn")
        self._activate_btn.setFixedWidth(64)
        self._activate_btn.setEnabled(False)
        self._activate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._activate_btn.clicked.connect(self._activateSelectedWindow)
        hbox.addWidget(self._activate_btn)

        hbox.addSpacing(12)

        self._status_label = QLabel("● 未选择窗口")
        self._status_label.setObjectName("statusLabel")
        hbox.addWidget(self._status_label)

        hbox.addStretch()
        return header

    # ── Horizontal separator ─────────────────────────────────────────────────

    def _buildSeparator(self) -> QFrame:
        sep = QFrame()
        sep.setObjectName("hSeparator")
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        return sep

    # ── Body (sidebar + content) ─────────────────────────────────────────────

    def _buildBody(self) -> QWidget:
        body = QWidget()
        hbox = QHBoxLayout(body)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)

        hbox.addWidget(self._buildSidebar())

        sep = QFrame()
        sep.setObjectName("vSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        hbox.addWidget(sep)

        self._autokey_panel = AutoKeyPanel()
        hbox.addWidget(self._autokey_panel, 1)
        return body

    def _buildSidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(70)

        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(0, 8, 0, 8)
        vbox.setSpacing(2)

        self._autokey_btn = NavButton("⌨", "自动按键")
        self._autokey_btn.setChecked(True)
        self._autokey_btn.setEnabled(False)  # 未激活窗口前禁用
        vbox.addWidget(self._autokey_btn)

        vbox.addStretch()

        about_btn = NavButton("？", "关于")
        about_btn.setCheckable(False)
        about_btn.clicked.connect(self._showAboutDialog)
        vbox.addWidget(about_btn)

        return sidebar

    def _showAboutDialog(self):
        readme_path = os.path.join(kMainDir, "assets", "readme.txt")
        try:
            with open(readme_path, encoding="utf-8") as f:
                content = f.read()
        except FileNotFoundError:
            content = "未找到 readme.txt 文件。"

        dlg = QDialog(self)
        dlg.setWindowTitle("关于")
        dlg.setMinimumSize(440, 280)

        vbox = QVBoxLayout(dlg)
        vbox.setContentsMargins(16, 16, 16, 12)
        vbox.setSpacing(10)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setObjectName("logText")
        text.setPlainText(content)
        vbox.addWidget(text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("关闭")
        close_btn.setObjectName("accentBtn")
        close_btn.setFixedWidth(80)
        close_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(close_btn)
        vbox.addLayout(btn_row)

        dlg.exec()

    # ── Log panel ────────────────────────────────────────────────────────────

    def _buildLogPanel(self) -> QWidget:
        panel = QWidget()
        panel.setObjectName("logPanel")
        panel.setFixedHeight(150)

        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(10, 4, 10, 6)
        vbox.setSpacing(3)

        header_row = QHBoxLayout()
        log_lbl = QLabel("运行日志")
        log_lbl.setObjectName("logTitle")
        header_row.addWidget(log_lbl)
        header_row.addStretch()
        clear_btn = QPushButton("清除")
        clear_btn.setObjectName("smallBtn")
        clear_btn.setFixedWidth(52)
        clear_btn.clicked.connect(lambda: self._log_text.clear())
        header_row.addWidget(clear_btn)
        vbox.addLayout(header_row)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setObjectName("logText")
        vbox.addWidget(self._log_text)

        return panel

    def _appendLog(self, msg: str):
        self._log_text.append(msg)
        self._log_text.verticalScrollBar().setValue(
            self._log_text.verticalScrollBar().maximum()
        )

    # ── Window management slots ──────────────────────────────────────────────

    def _showAllWindows(self):
        self._window_combo.clear()
        windows = self.window_manager.getAllWindows()
        if not windows:
            self._window_combo.addItem("未找到任何窗口", userData=-1)
            self._activate_btn.setEnabled(False)
            return
        for hwnd, title in windows:
            short_title = title[:60] if len(title) > 60 else title
            self._window_combo.addItem(f"[{hwnd}]  {short_title}", userData=hwnd)
        self._activate_btn.setEnabled(True)

    def _activateSelectedWindow(self):
        hwnd = self._window_combo.currentData()
        if hwnd is None or hwnd == -1:
            return

        success = self.window_manager.activateWindow(hwnd)
        if success:
            self.hwnd = hwnd
            short = self._window_combo.currentText()[:50]
            self._status_label.setText(f"● {short}")
            self._status_label.setObjectName("statusLabelOk")
            self._autokey_btn.setEnabled(True)   # 解锁自动按键选项卡
            self._autokey_panel.set_hwnd(hwnd)   # 通知面板更新目标窗口
        else:
            self._status_label.setText("● 激活失败")
            self._status_label.setObjectName("statusLabel")

        # Refresh stylesheet for the label so the new objectName takes effect
        self._status_label.style().unpolish(self._status_label)
        self._status_label.style().polish(self._status_label)
