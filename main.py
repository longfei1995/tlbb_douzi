import sys
import os

# Ensure Qt can locate its platform plugins when launched outside the PySide6
# installation directory (e.g. from VS Code or a conda environment).
try:
    import PySide6

    _pyside6_dir = os.path.dirname(PySide6.__file__)
    _plugins_dir = os.path.join(_pyside6_dir, "plugins", "platforms")
    if os.path.isdir(_plugins_dir):
        os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", _plugins_dir)
except Exception:
    pass

from PySide6.QtWidgets import QApplication

from ui.main_window import GameUI


def main():
    app = QApplication(sys.argv)
    window = GameUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
