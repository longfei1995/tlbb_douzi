import sys
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QTextEdit,
    QComboBox,
    QMessageBox,
    QCheckBox,
    QSpinBox,
    QLineEdit,
    QStackedWidget,
    QFrame,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QCursor

from src.task.game_param import (
    kDefaultKey,
    kBaseDir,
    kKeyConfigPath,
    kAutoKeyConfigPath,
    loadKeyConfig,
    loadAutoKeyConfig,
)
from src.task.window_manager import WindowManager
from src.task.sys_manager import shutdownPC, cancelShutdown
from src.ui.workers import UILogStream, RaidThread, DigSeedThread, AutoReturnThread


class NavButton(QPushButton):
    """Sidebar navigation button."""

    def __init__(self, text: str, page_index: int, parent=None):
        super().__init__(text, parent)
        self.page_index = page_index
        self.setObjectName("navBtn")
        self.setCheckable(True)
        self.setFlat(True)
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class GameUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.raid_thread = None
        self.dig_seed_thread = None
        self.auto_return_thread = None
        self.hwnd: int = -1
        self.window_manager = WindowManager()
        self.original_stdout = sys.stdout
        # YAML 文件存在则认为已配置，无需再次手动保存
        self.keys_configured = os.path.exists(kKeyConfigPath)

        # Buffer logs that appear before log_text widget is created
        self._pending_logs: list = []
        sys.stdout = UILogStream(lambda msg: self._pending_logs.append(msg))

        self._initUI()

        # Now flush buffered logs and redirect to live widget
        for msg in self._pending_logs:
            self._appendLog(msg)
        self._pending_logs.clear()
        sys.stdout = UILogStream(self._appendLog)

    # ── UI construction ─────────────────────────────────────────────────────

    def _initUI(self):
        self.setWindowTitle("豆子 — 天龙八部助手")
        self.setFixedSize(900, 640)

        icon_path = os.path.join(kBaseDir, "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._buildHeader())

        body = QWidget()
        body_hbox = QHBoxLayout(body)
        body_hbox.setContentsMargins(0, 0, 0, 0)
        body_hbox.setSpacing(0)
        body_hbox.addWidget(self._buildSidebar())

        sep = QFrame()
        sep.setObjectName("vSeparator")
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFixedWidth(1)
        body_hbox.addWidget(sep)

        body_hbox.addWidget(self._buildRightPanel(), 1)
        vbox.addWidget(body, 1)

        # Admin check
        if self.window_manager.isAdmin():
            print("✓ 当前程序以管理员权限运行")
        else:
            print("⚠ 建议以管理员身份运行本程序")

    # ── Header ──────────────────────────────────────────────────────────────

    def _buildHeader(self) -> QWidget:
        header = QWidget()
        header.setObjectName("header")
        header.setFixedHeight(52)

        hbox = QHBoxLayout(header)
        hbox.setContentsMargins(16, 0, 16, 0)
        hbox.setSpacing(8)

        title = QLabel("豆子")
        title.setObjectName("appTitle")
        hbox.addWidget(title)

        hbox.addSpacing(16)

        refresh_btn = QPushButton("刷新窗口")
        refresh_btn.setObjectName("headerBtn")
        refresh_btn.setFixedWidth(76)
        refresh_btn.clicked.connect(self._showAllWindows)
        hbox.addWidget(refresh_btn)

        self._window_combo = QComboBox()
        self._window_combo.addItem("请先刷新窗口列表", userData=-1)
        self._window_combo.setMinimumWidth(270)
        hbox.addWidget(self._window_combo)

        self._activate_btn = QPushButton("激活")
        self._activate_btn.setObjectName("accentBtn")
        self._activate_btn.setFixedWidth(58)
        self._activate_btn.setEnabled(False)
        self._activate_btn.clicked.connect(self._activateSelectedWindow)
        hbox.addWidget(self._activate_btn)

        hbox.addSpacing(8)

        self._status_label = QLabel("● 未选择窗口")
        self._status_label.setObjectName("statusLabel")
        hbox.addWidget(self._status_label)

        hbox.addStretch()
        return header

    # ── Sidebar ─────────────────────────────────────────────────────────────

    def _buildSidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(160)

        vbox = QVBoxLayout(sidebar)
        vbox.setContentsMargins(0, 12, 0, 10)
        vbox.setSpacing(2)

        nav_items = [
            ("  ⌨  按键配置", 0),
            ("  ▶  自动按键", 1),
            ("  ⛏  挖种子", 2),
            ("  ↩  自动回点", 3),
            ("  ⚙  系统管理", 4),
        ]

        self._nav_btns: list[NavButton] = []
        for text, idx in nav_items:
            btn = NavButton(text, idx)
            btn.clicked.connect(lambda _checked, i=idx: self._switchPage(i))
            self._nav_btns.append(btn)
            vbox.addWidget(btn)

        vbox.addStretch()

        version_label = QLabel("v2026.03")
        version_label.setObjectName("versionLabel")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        vbox.addWidget(version_label)

        # Activate first nav button
        self._nav_btns[0].setChecked(True)
        return sidebar

    # ── Right panel (stack + log) ────────────────────────────────────────────

    def _buildRightPanel(self) -> QWidget:
        panel = QWidget()
        vbox = QVBoxLayout(panel)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        self._stack = QStackedWidget()
        self._buildKeyConfigPage()
        self._buildAutoKeyPage()
        self._buildDigSeedPage()
        self._buildAutoReturnPage()
        self._buildSystemPage()
        vbox.addWidget(self._stack, 1)

        vbox.addWidget(self._buildLogPanel())
        return panel

    # ── Page 0 — Key Config ──────────────────────────────────────────────────

    def _buildKeyConfigPage(self):
        page = QWidget()
        page.setObjectName("page")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 12)

        grp = QGroupBox("按键配置文件")
        g_vbox = QVBoxLayout(grp)

        hint = QLabel(
            "直接编辑下方配置文件后点击「重新加载」，或重启程序生效。\n"
            "确保游戏处于非聊天模式。"
        )
        hint.setObjectName("infoLabel")
        hint.setWordWrap(True)
        g_vbox.addWidget(hint)

        # 配置文件路径
        path_row = QHBoxLayout()
        path_lbl = QLabel(f"配置文件：{kKeyConfigPath}")
        path_lbl.setObjectName("infoLabel")
        path_lbl.setWordWrap(True)
        path_row.addWidget(path_lbl)
        open_btn = QPushButton("打开文件夹")
        open_btn.setObjectName("smallBtn")
        open_btn.setFixedWidth(76)
        open_btn.clicked.connect(lambda: os.startfile(os.path.dirname(kKeyConfigPath)))
        path_row.addWidget(open_btn)
        g_vbox.addLayout(path_row)

        # 重新加载按钮
        reload_btn = QPushButton("重新加载配置")
        reload_btn.setObjectName("accentBtn")
        reload_btn.setFixedWidth(110)
        reload_btn.clicked.connect(self._reloadKeyConfig)
        g_vbox.addWidget(reload_btn)

        # 状态标签
        initial_status = (
            "状态：已自动加载配置文件，其他功能已就绪"
            if os.path.exists(kKeyConfigPath)
            else "状态：配置文件不存在，将使用默认按键值"
        )
        self._config_status = QLabel(initial_status)
        self._config_status.setObjectName(
            "successLabel" if os.path.exists(kKeyConfigPath) else "warningLabel"
        )
        g_vbox.addWidget(self._config_status)

        vbox.addWidget(grp)
        vbox.addStretch()
        self._stack.addWidget(page)

    # ── Page 1 — Auto Key ───────────────────────────────────────────────────

    def _buildAutoKeyPage(self):
        page = QWidget()
        page.setObjectName("page")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 12)

        grp = QGroupBox("自动按键控制")
        g_vbox = QVBoxLayout(grp)

        # Row 0 — config file path
        r0 = QHBoxLayout()
        path_lbl = QLabel(f"配置文件：{kAutoKeyConfigPath}")
        path_lbl.setObjectName("infoLabel")
        path_lbl.setWordWrap(True)
        r0.addWidget(path_lbl)
        open_btn = QPushButton("打开文件夹")
        open_btn.setObjectName("smallBtn")
        open_btn.setFixedWidth(76)
        open_btn.clicked.connect(
            lambda: os.startfile(os.path.dirname(kAutoKeyConfigPath))
        )
        r0.addWidget(open_btn)
        g_vbox.addLayout(r0)

        # Row 1 — reload button + status
        r1 = QHBoxLayout()
        reload_btn = QPushButton("重新加载配置")
        reload_btn.setObjectName("accentBtn")
        reload_btn.setFixedWidth(110)
        reload_btn.clicked.connect(self._reloadAutoKeyConfig)
        r1.addWidget(reload_btn)
        self._auto_key_status = QLabel("配置将在点击\u201c开始\u201d时自动读取")
        self._auto_key_status.setObjectName("infoLabel")
        r1.addWidget(self._auto_key_status)
        r1.addStretch()
        g_vbox.addLayout(r1)

        # Row 2 — start / stop
        r2 = QHBoxLayout()
        self._start_btn = QPushButton("▶  开始自动按键")
        self._start_btn.setObjectName("startBtn")
        self._start_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._startRaid)
        r2.addWidget(self._start_btn)

        self._stop_btn = QPushButton("⬛  停止")
        self._stop_btn.setObjectName("stopBtn")
        self._stop_btn.setEnabled(False)
        self._stop_btn.clicked.connect(self._stopRaid)
        r2.addWidget(self._stop_btn)
        r2.addStretch()
        g_vbox.addLayout(r2)

        vbox.addWidget(grp)
        vbox.addStretch()
        self._stack.addWidget(page)

    # ── Page 2 — Dig Seed ───────────────────────────────────────────────────

    def _buildDigSeedPage(self):
        page = QWidget()
        page.setObjectName("page")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 12)

        grp = QGroupBox("挖种子控制")
        g_vbox = QVBoxLayout(grp)

        # Row 1 — parameters
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("种子等级:"))
        self._seed_level_spin = QSpinBox()
        self._seed_level_spin.setRange(1, 4)
        self._seed_level_spin.setValue(2)
        self._seed_level_spin.setMaximumWidth(60)
        r1.addWidget(self._seed_level_spin)

        r1.addSpacing(16)
        r1.addWidget(QLabel("循环次数:"))
        self._loop_count_spin = QSpinBox()
        self._loop_count_spin.setRange(1, 50)
        self._loop_count_spin.setValue(10)
        self._loop_count_spin.setMaximumWidth(70)
        r1.addWidget(self._loop_count_spin)

        r1.addSpacing(16)
        r1.addWidget(QLabel("起始任务:"))
        self._task_type_combo = QComboBox()
        self._task_type_combo.addItem("挖种子", userData=True)
        self._task_type_combo.addItem("打怪", userData=False)
        r1.addWidget(self._task_type_combo)

        help_btn = QPushButton("?")
        help_btn.setObjectName("smallBtn")
        help_btn.setFixedWidth(28)
        help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        help_btn.clicked.connect(self._showDigSeedHelp)
        r1.addWidget(help_btn)
        r1.addStretch()
        g_vbox.addLayout(r1)

        # Row 2 — start / stop
        r2 = QHBoxLayout()
        self._dig_start_btn = QPushButton("▶  开始挖种子")
        self._dig_start_btn.setObjectName("startBtn")
        self._dig_start_btn.setEnabled(False)
        self._dig_start_btn.clicked.connect(self._startDigSeed)
        r2.addWidget(self._dig_start_btn)

        self._dig_stop_btn = QPushButton("⬛  停止")
        self._dig_stop_btn.setObjectName("stopBtn")
        self._dig_stop_btn.setEnabled(False)
        self._dig_stop_btn.clicked.connect(self._stopDigSeed)
        r2.addWidget(self._dig_stop_btn)
        r2.addStretch()
        g_vbox.addLayout(r2)

        vbox.addWidget(grp)
        vbox.addStretch()
        self._stack.addWidget(page)

    # ── Page 3 — Auto Return ─────────────────────────────────────────────────

    def _buildAutoReturnPage(self):
        page = QWidget()
        page.setObjectName("page")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 12)

        grp = QGroupBox("自动回点控制")
        g_vbox = QVBoxLayout(grp)

        # Row 1 — scene selector
        r1 = QHBoxLayout()
        r1.addWidget(QLabel("选择场景:"))
        self._scene_combo = QComboBox()
        self._scene_combo.addItem("雪原", userData="雪原")
        self._scene_combo.addItem("四象回点", userData="四象")
        self._scene_combo.addItem("苗人洞", userData="苗人洞")
        self._scene_combo.currentIndexChanged.connect(self._onSceneChanged)
        r1.addWidget(self._scene_combo)

        help_btn = QPushButton("?")
        help_btn.setObjectName("smallBtn")
        help_btn.setFixedWidth(28)
        help_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        help_btn.clicked.connect(self._showAutoReturnHelp)
        r1.addWidget(help_btn)
        r1.addStretch()
        g_vbox.addLayout(r1)

        # Row 2 — coordinates
        r2 = QHBoxLayout()
        self._x_lbl = QLabel("X 坐标:")
        r2.addWidget(self._x_lbl)
        self._x_input = QLineEdit("107")
        self._x_input.setMaximumWidth(80)
        r2.addWidget(self._x_input)

        r2.addSpacing(12)
        self._y_lbl = QLabel("Y 坐标:")
        r2.addWidget(self._y_lbl)
        self._y_input = QLineEdit("109")
        self._y_input.setMaximumWidth(80)
        r2.addWidget(self._y_input)
        r2.addStretch()
        g_vbox.addLayout(r2)

        # Row 3 — options
        r3 = QHBoxLayout()
        self._return_immediately_cb = QCheckBox("死亡后立即起身")
        r3.addWidget(self._return_immediately_cb)
        r3.addSpacing(16)
        r3.addWidget(QLabel("循环间隔:"))
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 3600)
        self._interval_spin.setValue(20)
        self._interval_spin.setSuffix(" 秒")
        self._interval_spin.setMaximumWidth(90)
        r3.addWidget(self._interval_spin)
        r3.addStretch()
        g_vbox.addLayout(r3)

        # Row 4 — start / stop
        r4 = QHBoxLayout()
        self._return_start_btn = QPushButton("▶  开始自动回点")
        self._return_start_btn.setObjectName("startBtn")
        self._return_start_btn.setEnabled(False)
        self._return_start_btn.clicked.connect(self._startAutoReturn)
        r4.addWidget(self._return_start_btn)

        self._return_stop_btn = QPushButton("⬛  停止")
        self._return_stop_btn.setObjectName("stopBtn")
        self._return_stop_btn.setEnabled(False)
        self._return_stop_btn.clicked.connect(self._stopAutoReturn)
        r4.addWidget(self._return_stop_btn)
        r4.addStretch()
        g_vbox.addLayout(r4)

        vbox.addWidget(grp)
        vbox.addStretch()
        self._stack.addWidget(page)

    # ── Page 4 — System ──────────────────────────────────────────────────────

    def _buildSystemPage(self):
        page = QWidget()
        page.setObjectName("page")
        vbox = QVBoxLayout(page)
        vbox.setContentsMargins(20, 20, 20, 12)

        grp = QGroupBox("系统管理")
        g_vbox = QVBoxLayout(grp)

        row = QHBoxLayout()
        row.addWidget(QLabel("关机时间 (小时):"))
        self._shutdown_input = QLineEdit()
        self._shutdown_input.setMaximumWidth(100)
        self._shutdown_input.setPlaceholderText("如: 3.5")
        row.addWidget(self._shutdown_input)

        set_btn = QPushButton("设置定时关机")
        set_btn.setObjectName("accentBtn")
        set_btn.clicked.connect(self._setShutdown)
        row.addWidget(set_btn)

        cancel_btn = QPushButton("取消关机")
        cancel_btn.clicked.connect(self._cancelShutdown)
        row.addWidget(cancel_btn)
        row.addStretch()
        g_vbox.addLayout(row)

        vbox.addWidget(grp)
        vbox.addStretch()
        self._stack.addWidget(page)

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
        clear_btn.clicked.connect(self._clearLog)
        header_row.addWidget(clear_btn)
        vbox.addLayout(header_row)

        self._log_text = QTextEdit()
        self._log_text.setReadOnly(True)
        self._log_text.setObjectName("logText")
        vbox.addWidget(self._log_text)

        return panel

    # ── Navigation ───────────────────────────────────────────────────────────

    def _switchPage(self, index: int):
        if not self.keys_configured and index in (1, 2, 3):
            self._appendLog("请先在「按键配置」页保存按键后再使用此功能")
            # Switch to key config page instead
            self._switchPage(0)
            return
        self._stack.setCurrentIndex(index)
        for btn in self._nav_btns:
            btn.setChecked(btn.page_index == index)

    # ── Window management slots ──────────────────────────────────────────────

    def _showAllWindows(self):
        self._window_combo.clear()
        windows = self.window_manager.getAllWindows()
        if not windows:
            self._window_combo.addItem("未找到任何窗口", userData=-1)
            self._activate_btn.setEnabled(False)
            return
        for hwnd, title in windows:
            short_title = title[:50] if len(title) > 50 else title
            self._window_combo.addItem(f"[{hwnd}] {short_title}", userData=hwnd)
        self._activate_btn.setEnabled(True)
        print(f"刷新完成，共找到 {len(windows)} 个窗口")

    def _activateSelectedWindow(self):
        hwnd = self._window_combo.currentData()
        if hwnd is None or hwnd == -1:
            self._appendLog("请先刷新窗口列表并选择要激活的窗口")
            return
        try:
            success = self.window_manager.activateWindow(hwnd)
            if success:
                self.hwnd = hwnd
                short = self._window_combo.currentText()[:40]
                self._status_label.setText(f"● {short}")
                self._status_label.setObjectName("statusLabelOk")
                self._status_label.style().unpolish(self._status_label)
                self._status_label.style().polish(self._status_label)
                self._setTaskButtonsEnabled(True)
                print(f"✓ 已激活窗口: {self._window_combo.currentText()}")
            else:
                self._status_label.setText("● 激活失败")
                self._status_label.setObjectName("statusLabel")
                self._status_label.style().unpolish(self._status_label)
                self._status_label.style().polish(self._status_label)
                self._setTaskButtonsEnabled(False)
        except Exception as e:
            self._appendLog(f"激活窗口时出错: {e}")

    def _setTaskButtonsEnabled(self, enabled: bool):
        self._start_btn.setEnabled(enabled)
        self._dig_start_btn.setEnabled(enabled)
        self._return_start_btn.setEnabled(enabled)

    # ── RaidThread slots ─────────────────────────────────────────────────────

    def _startRaid(self):
        if self.hwnd == -1:
            self._appendLog("请先选择并激活游戏窗口")
            return
        cfg = loadAutoKeyConfig()
        if not cfg.key_sequence.strip():
            self._appendLog("auto_key.yaml 中 key_sequence 为空，无法执行")
            return
        print(
            f"[自动按键] 已加载配置: 序列={cfg.key_sequence!r}, "
            f"间隔={cfg.key_interval}s, 休眠={cfg.sleep_time}s, 峨眉={cfg.is_em}"
        )

        self.raid_thread = RaidThread(
            hwnd=self.hwnd,
            key_interval=cfg.key_interval,
            sleep_time=cfg.sleep_time,
            is_em=cfg.is_em,
            key_sequence=cfg.key_sequence,
        )
        self.raid_thread.log_signal.connect(self._appendLog)
        self.raid_thread.finished_signal.connect(self._onRaidFinished)
        self._start_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._activate_btn.setEnabled(False)
        self.raid_thread.start()

    def _stopRaid(self):
        if self.raid_thread and self.raid_thread.isRunning():
            self.raid_thread.stop()
            self.raid_thread.wait()

    def _onRaidFinished(self):
        self._start_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._activate_btn.setEnabled(True)
        self._appendLog("自动按键已停止")

    # ── DigSeedThread slots ──────────────────────────────────────────────────

    def _startDigSeed(self):
        if self.hwnd == -1:
            self._appendLog("请先选择并激活游戏窗口")
            return
        self._appendLog("*** 挖种子脚本启动 ***")
        self.dig_seed_thread = DigSeedThread(
            hwnd=self.hwnd,
            seed_level=self._seed_level_spin.value(),
            loop_count=self._loop_count_spin.value(),
            is_dig_seed=self._task_type_combo.currentData(),
        )
        self.dig_seed_thread.log_signal.connect(self._appendLog)
        self.dig_seed_thread.finished_signal.connect(self._onDigSeedFinished)
        self._dig_start_btn.setEnabled(False)
        self._dig_stop_btn.setEnabled(True)
        self._activate_btn.setEnabled(False)
        self.dig_seed_thread.start()

    def _stopDigSeed(self):
        if self.dig_seed_thread and self.dig_seed_thread.isRunning():
            self.dig_seed_thread.stop()
            self.dig_seed_thread.wait()

    def _onDigSeedFinished(self):
        self._dig_start_btn.setEnabled(True)
        self._dig_stop_btn.setEnabled(False)
        self._activate_btn.setEnabled(True)
        self._appendLog("挖种子任务已停止")

    # ── AutoReturnThread slots ───────────────────────────────────────────────

    def _startAutoReturn(self):
        if self.hwnd == -1:
            self._appendLog("请先选择并激活游戏窗口")
            return
        scene = self._scene_combo.currentData()
        x = self._x_input.text().strip()
        y = self._y_input.text().strip()
        if scene != "四象":
            if not x or not y:
                self._appendLog("请输入有效的坐标值")
                return
            try:
                int(x)
                int(y)
            except ValueError:
                self._appendLog("X / Y 坐标必须为整数")
                return
        self._appendLog("*** 自动回点脚本启动 ***")
        self.auto_return_thread = AutoReturnThread(
            hwnd=self.hwnd,
            scene_type=scene,
            x=x,
            y=y,
            is_return_immediately=self._return_immediately_cb.isChecked(),
            interval_time=self._interval_spin.value(),
        )
        self.auto_return_thread.log_signal.connect(self._appendLog)
        self.auto_return_thread.finished_signal.connect(self._onAutoReturnFinished)
        self._return_start_btn.setEnabled(False)
        self._return_stop_btn.setEnabled(True)
        self._activate_btn.setEnabled(False)
        self.auto_return_thread.start()

    def _stopAutoReturn(self):
        if self.auto_return_thread and self.auto_return_thread.isRunning():
            self.auto_return_thread.stop()
            self.auto_return_thread.wait()

    def _onAutoReturnFinished(self):
        self._return_start_btn.setEnabled(True)
        self._return_stop_btn.setEnabled(False)
        self._activate_btn.setEnabled(True)
        self._appendLog("自动回点已停止")

    # ── Key config slots ─────────────────────────────────────────────────────

    def _reloadKeyConfig(self):
        """重新从 key_config.yaml 加载按键配置并应用到 kDefaultKey。"""
        new_cfg = loadKeyConfig()
        kDefaultKey.pet_attack = new_cfg.pet_attack
        kDefaultKey.pet_eat = new_cfg.pet_eat
        kDefaultKey.xue_ji = new_cfg.xue_ji
        kDefaultKey.qing_xin = new_cfg.qing_xin
        kDefaultKey.ding_wei_fu = new_cfg.ding_wei_fu
        kDefaultKey.horse = new_cfg.horse
        self.keys_configured = os.path.exists(kKeyConfigPath)
        status = (
            "状态：配置已重新加载，其他功能已就绪"
            if self.keys_configured
            else "状态：配置文件不存在，将使用默认按键值"
        )
        obj_name = "successLabel" if self.keys_configured else "warningLabel"
        self._config_status.setText(status)
        self._config_status.setObjectName(obj_name)
        self._config_status.style().unpolish(self._config_status)
        self._config_status.style().polish(self._config_status)
        print(f"✓ 按键配置已重新加载: {new_cfg}")

    def _reloadAutoKeyConfig(self):
        """提示用户配置路径，实际配置在点击开始时读取。"""
        print(f"[自动按键] 配置文件路径: {kAutoKeyConfigPath}")
        print("[自动按键] 点击\u201c开始\u201d时将自动读取最新配置")

    # ── Scene combo slot ─────────────────────────────────────────────────────

    def _onSceneChanged(self, _index: int):
        is_si_xiang = self._scene_combo.currentData() == "四象"
        visible = not is_si_xiang
        self._x_lbl.setVisible(visible)
        self._x_input.setVisible(visible)
        self._y_lbl.setVisible(visible)
        self._y_input.setVisible(visible)
        self._return_immediately_cb.setVisible(visible)

    # ── Shutdown slots ────────────────────────────────────────────────────────

    def _setShutdown(self):
        text = self._shutdown_input.text().strip()
        if not text:
            QMessageBox.warning(self, "警告", "请输入关机时间（单位：小时）")
            return
        try:
            hours = float(text)
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数字，例如 3.5")
            return
        if hours <= 0:
            QMessageBox.warning(self, "警告", "关机时间必须大于 0")
            return
        if hours > 24:
            reply = QMessageBox.question(
                self,
                "确认",
                f"关机时间为 {hours} 小时，是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        if shutdownPC(hours):
            print(f"✓ 已设置 {hours} 小时后关机")
            QMessageBox.information(self, "成功", f"系统将在 {hours} 小时后关机")
        else:
            QMessageBox.warning(self, "失败", "设置定时关机失败，请检查系统权限")

    def _cancelShutdown(self):
        if cancelShutdown():
            print("✓ 已取消关机计划")
            QMessageBox.information(self, "成功", "关机计划已取消")
        else:
            QMessageBox.warning(self, "失败", "取消关机失败")

    # ── Help dialogs ──────────────────────────────────────────────────────────

    def _showDigSeedHelp(self):
        QMessageBox.information(
            self,
            "挖种子说明",
            (
                f"当前按键设置：\n"
                f"  定位符 = {kDefaultKey.ding_wei_fu}\n"
                f"  骑马   = {kDefaultKey.horse}\n\n"
                "使用前请确认：\n"
                "  • 任务追踪已打开且仅保留种子任务\n"
                "  • 角色已在起始点附近\n"
                "  • 游戏分辨率与工具截图一致"
            ),
        )

    def _showAutoReturnHelp(self):
        QMessageBox.information(
            self,
            "自动回点说明",
            (
                f"当前按键设置：\n"
                f"  定位符 = {kDefaultKey.ding_wei_fu}\n"
                f"  骑马   = {kDefaultKey.horse}\n\n"
                "坐标说明：输入角色死亡后需要传送到的目标坐标。\n"
                "四象场景不需要填写坐标，其他场景均需填写。\n\n"
                "循环间隔：每次执行回点操作后等待的时间（秒），\n"
                "建议设置为 15-30 秒。"
            ),
        )

    # ── Log ───────────────────────────────────────────────────────────────────

    def _appendLog(self, message: str):
        if not hasattr(self, "_log_text"):
            return
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_text.append(f"[{ts}] {message}")
        sb = self._log_text.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def _clearLog(self):
        self._log_text.clear()
        self._appendLog("日志已清除")

    # ── Close ─────────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        sys.stdout = self.original_stdout
        event.accept()
