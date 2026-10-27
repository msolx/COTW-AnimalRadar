"""入口无需命令行参数，设置见 config.py。"""
import sys

def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('缺少 PySide6，请先执行 .venv\\Scripts\\python.exe -m pip install -r requirements.txt')
        return 1
    from PySide6.QtCore import QLockFile
    from ui.main_window import MainWindow
    import config

    app = QApplication(sys.argv[:1])
    from services.fonts import setup_fonts
    setup_fonts(app)

    lock = QLockFile(str(config.ROOT / 'radar.lock'))
    if not lock.tryLock(0):
        print('A radar window is already running.')
        return 1

    try:
        window = MainWindow(source=config.FIELD_TEST_SOURCE)
        window.show()
        return app.exec()
    finally:
        lock.unlock()

if __name__ == '__main__':
    raise SystemExit(main())
