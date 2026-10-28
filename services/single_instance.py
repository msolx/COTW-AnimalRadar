"""同目录雷达单实例与主窗口唤醒；仅本机用户级IPC，不连接或修改游戏。"""
import ctypes
import hashlib
import os
from pathlib import Path
import sys
import time

from PySide6.QtCore import QObject, QLockFile, QTimer, Qt, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication

REQUEST = b'activate\n'
REPLY = b'ok\n'


def allow_foreground(pid):
    """由用户新启动的进程把前台权限交给已有实例；不模拟按键、不绕过焦点限制。"""
    if sys.platform != 'win32' or os.environ.get('QT_QPA_PLATFORM') == 'offscreen':
        return False
    try:
        api = ctypes.WinDLL('user32', use_last_error=True)
        api.AllowSetForegroundWindow.argtypes = [ctypes.c_ulong]
        api.AllowSetForegroundWindow.restype = ctypes.c_int
        return bool(api.AllowSetForegroundWindow(pid))
    except (OSError, AttributeError):
        return False


def wake_window(window):
    """恢复最小化/隐藏窗口，保留最大化状态；离屏窗口移回有效显示器。"""
    window.setWindowState(window.windowState() & ~Qt.WindowState.WindowMinimized)
    window.show()
    screens = QApplication.screens()
    if screens and not any(s.availableGeometry().intersects(window.frameGeometry()) for s in screens):
        area = QApplication.primaryScreen().availableGeometry()
        # 只搬回完全离屏的窗口；不覆盖用户正常的多屏摆放。
        window.move(area.topLeft())
    window.raise_()
    window.activateWindow()
    if sys.platform == 'win32' and QApplication.platformName() != 'offscreen':
        try:
            api = ctypes.WinDLL('user32', use_last_error=True)
            api.SetForegroundWindow.argtypes = [ctypes.c_void_p]
            api.SetForegroundWindow.restype = ctypes.c_int
            api.SetForegroundWindow(int(window.winId()))
        except (OSError, AttributeError):
            pass
    # 系统不允许切前台时，至少恢复窗口并提示任务栏；不强行劫持输入。
    QApplication.alert(window, 2000)


class SingleInstance(QObject):
    activation_requested = Signal()

    def __init__(self, lock_path: Path, timeout_ms=2500):
        super().__init__()
        self.lock = QLockFile(str(lock_path))
        self.lock.setStaleLockTime(0)  # 长期持锁不因超时被误判；死进程由Qt校验清理。
        key = os.path.normcase(str(lock_path.resolve()))
        self.name = 'cotw_radar_' + hashlib.sha256(key.encode('utf-8')).hexdigest()[:32]
        self.timeout_ms = timeout_ms
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._accept)
        self.clients = {}
        self.primary = False

    def acquire_or_activate(self):
        """返回True时本进程负责UI；False表示已有实例收到请求，本进程正常退出。"""
        if self.lock.tryLock(0):
            return self._listen()
        if self.lock.error() != QLockFile.LockError.LockFailedError:
            raise RuntimeError('无法创建雷达锁文件，请将完整程序解压到当前用户可写的文件夹。')
        pid, _, _ = self.lock.getLockInfo()
        if pid > 0:
            allow_foreground(pid)
        if self._notify_existing():
            return False
        # 等待期间旧进程可能已退出；重新获取锁后才允许清理陈旧IPC端点。
        if self.lock.tryLock(0):
            return self._listen()
        raise RuntimeError('已有雷达未响应唤醒。若仍是v1.1.0旧版，请先正常关闭旧版一次，再启动新版；'
                           '若正在启动，请稍等后重试。不要删除正在使用的radar.lock。')

    def _listen(self):
        self.primary = True
        QLocalServer.removeServer(self.name)
        if not self.server.listen(self.name):
            self.close()
            raise RuntimeError('无法建立本机窗口唤醒通道：' + self.server.errorString())
        return True

    def _notify_existing(self):
        deadline = time.monotonic() + self.timeout_ms / 1000
        while time.monotonic() < deadline:
            socket = QLocalSocket()
            socket.connectToServer(self.name)
            remaining = max(1, int((deadline-time.monotonic())*1000))
            if not socket.waitForConnected(min(150, remaining)):
                socket.abort()
                # named pipe不存在时会立即失败，避免启动竞态下忙循环。
                time.sleep(min(.03, max(0, deadline-time.monotonic())))
                continue
            socket.write(REQUEST)
            if socket.bytesToWrite() and not socket.waitForBytesWritten(remaining):
                socket.abort()
                return False
            response = bytearray()
            while time.monotonic() < deadline and len(response) < len(REPLY):
                if not socket.bytesAvailable():
                    remaining = max(1, int((deadline-time.monotonic())*1000))
                    if not socket.waitForReadyRead(remaining):
                        break
                response.extend(bytes(socket.readAll()))
            socket.abort()
            return bytes(response) == REPLY
        return False

    def _accept(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            self.clients[socket] = bytearray()
            timer = QTimer(socket)
            timer.setSingleShot(True)
            timer.timeout.connect(socket.abort)
            timer.start(self.timeout_ms)
            socket.readyRead.connect(lambda s=socket: self._receive(s))
            socket.disconnected.connect(lambda s=socket: self._forget(s))
            if socket.bytesAvailable():
                self._receive(socket)

    def _receive(self, socket):
        data = self.clients.get(socket)
        if data is None:
            return
        data.extend(bytes(socket.readAll()))
        if len(data) > len(REQUEST) or not REQUEST.startswith(data):
            socket.abort()  # 只接受固定激活消息，不接受路径、命令或其他远程操作。
            return
        if bytes(data) == REQUEST:
            self.activation_requested.emit()
            socket.write(REPLY)
            socket.disconnectFromServer()

    def _forget(self, socket):
        self.clients.pop(socket, None)
        socket.deleteLater()

    def close(self):
        for socket in tuple(self.clients):
            socket.abort()
        self.server.close()
        if self.primary:
            self.lock.unlock()
            self.primary = False
