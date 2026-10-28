"""入口无需命令行参数，设置见 config.py。"""
import sys

def main():
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print('缺少 PySide6，请先执行 .venv\\Scripts\\python.exe -m pip install -r requirements.txt')
        return 1
    from PySide6.QtWidgets import QMessageBox
    from services.single_instance import SingleInstance, wake_window
    import config

    app = QApplication(sys.argv[:1])
    instance = SingleInstance(config.ROOT / 'radar.lock', config.ACTIVATION_TIMEOUT_MS)
    try:
        primary = instance.acquire_or_activate()
    except RuntimeError as exc:
        QMessageBox.warning(None, 'COTW AnimalRadar', str(exc))
        return 1
    if not primary:
        return 0

    try:
        from services.fonts import setup_fonts
        from ui.main_window import MainWindow
        setup_fonts(app)
        window = MainWindow(source=config.FIELD_TEST_SOURCE)
        instance.activation_requested.connect(lambda: wake_window(window))
        window.show()
        return app.exec()
    finally:
        instance.close()

if __name__ == '__main__':
    raise SystemExit(main())
