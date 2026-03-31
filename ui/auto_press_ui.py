import os
import sys
import yaml
import threading

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QFrame,
    QFileDialog,
    QStackedWidget,
    QDoubleSpinBox,
)
from PySide6.QtCore import Qt

from tools.config import kRootDir
from src.auto_press_key import AutoPressKey


class AutoKeyPanel(QWidget):
    """自动按键功能面板，包含功能选择下拉菜单和各子页。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("placeholder")
        self._hwnd: int = -1
        self._keyconfig_path: str = os.path.join(kRootDir, "assets", "keyconfig.yaml")
        self._auto_press = AutoPressKey()
        self._auto_press_thread: threading.Thread | None = None
        self._buildUI()

    # ── Public interface ──────────────────────────────────────────────────────

    def set_hwnd(self, hwnd: int) -> None:
        """由主窗口在激活目标窗口后调用。"""
        self._hwnd = hwnd

    def stop(self) -> None:
        """由主窗口在关闭时调用，停止后台线程。"""
        self._auto_press.stop()

    # ── UI construction ───────────────────────────────────────────────────────

    def _buildUI(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(16, 12, 16, 12)
        vbox.setSpacing(10)

        func_combo = QComboBox()
        func_combo.addItem("基础按键")
        func_combo.setFixedWidth(160)
        vbox.addWidget(func_combo)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("hSeparator")
        vbox.addWidget(sep)

        stack = QStackedWidget()
        stack.addWidget(self._buildBasePressPage())
        vbox.addWidget(stack, 1)

        func_combo.currentIndexChanged.connect(stack.setCurrentIndex)

    def _buildBasePressPage(self) -> QWidget:
        page = QWidget()
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(0, 4, 0, 0)
        vbox.setSpacing(10)
        vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        vbox.addLayout(self._buildPathRow())
        vbox.addLayout(self._buildFileRow())
        vbox.addLayout(self._buildParamRow())
        vbox.addLayout(self._buildCtrlRow())
        return page

    def _buildPathRow(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        lbl = QLabel("当前配置文件:")
        lbl.setFixedWidth(90)
        row.addWidget(lbl)
        self._config_path_label = QLabel(self._keyconfig_path)
        self._config_path_label.setObjectName("statusLabel")
        self._config_path_label.setWordWrap(True)
        row.addWidget(self._config_path_label, 1)
        return row

    def _buildFileRow(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        load_btn = QPushButton("加载配置文件")
        load_btn.setObjectName("headerBtn")
        load_btn.setFixedWidth(110)
        load_btn.clicked.connect(self._loadKeyconfigFile)
        row.addWidget(load_btn)

        reload_btn = QPushButton("重载配置")
        reload_btn.setObjectName("headerBtn")
        reload_btn.setFixedWidth(80)
        reload_btn.clicked.connect(self._reloadKeyconfig)
        row.addWidget(reload_btn)
        return row

    def _buildParamRow(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(16)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        row.addWidget(QLabel("循环休眠(秒):"))
        self._loop_sleep_spin = QDoubleSpinBox()
        self._loop_sleep_spin.setRange(0.0, 60.0)
        self._loop_sleep_spin.setSingleStep(0.1)
        self._loop_sleep_spin.setValue(1.0)
        self._loop_sleep_spin.setFixedWidth(80)
        row.addWidget(self._loop_sleep_spin)

        row.addWidget(QLabel("按键间隔(秒):"))
        self._key_interval_spin = QDoubleSpinBox()
        self._key_interval_spin.setRange(0.0, 10.0)
        self._key_interval_spin.setSingleStep(0.05)
        self._key_interval_spin.setValue(0.1)
        self._key_interval_spin.setFixedWidth(80)
        row.addWidget(self._key_interval_spin)
        return row

    def _buildCtrlRow(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._start_btn = QPushButton("开始自动按键")
        self._start_btn.setObjectName("accentBtn")
        self._start_btn.setFixedWidth(120)
        self._start_btn.clicked.connect(self._startBasePress)
        row.addWidget(self._start_btn)

        self._stop_btn = QPushButton("停止")
        self._stop_btn.setObjectName("headerBtn")
        self._stop_btn.setFixedWidth(80)
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stopBasePress)
        row.addWidget(self._stop_btn)
        return row

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _startBasePress(self):
        if self._auto_press_thread and self._auto_press_thread.is_alive():
            return
        if self._hwnd == -1:
            print("⚠ 请先选择并激活目标窗口")
            return
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._auto_press_thread = threading.Thread(
            target=self._auto_press.base_press,
            args=(
                self._hwnd,
                self._key_interval_spin.value(),
                self._loop_sleep_spin.value(),
            ),
            daemon=True,
        )
        self._auto_press_thread.start()

    def _stopBasePress(self):
        self._auto_press.stop()
        self._stop_btn.setEnabled(False)
        self._start_btn.setEnabled(True)

    def _loadKeyconfigFile(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择按键配置文件", "", "YAML 文件 (*.yaml *.yml)"
        )
        if not path:
            return
        try:
            content = open(path, encoding="utf-8").read()
            target = os.path.join(kRootDir, "assets", "keyconfig.yaml")
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
            self._keyconfig_path = target
            self._config_path_label.setText(target)
            print(f"✓ 已加载配置文件: {path}")
        except Exception as e:
            print(f"✗ 加载配置文件失败: {e}")

    def _reloadKeyconfig(self):
        try:
            config = yaml.safe_load(open(self._keyconfig_path, encoding="utf-8")) or {}
            keys = [f"{k}: {v}" for k, v in config.items()]
            print(f"✓ 配置重载成功，共 {len(keys)} 个按键: {', '.join(keys)}")
        except Exception as e:
            print(f"✗ 配置重载失败: {e}")
