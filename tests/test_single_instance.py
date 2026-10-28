"""真实本机IPC/子进程与Qt窗口状态测试；不创建扫描器、不连接游戏。"""
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from PySide6.QtCore import QLockFile, QTimer, Qt
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication, QWidget
from services.single_instance import SingleInstance, wake_window


CHILD = '''
import json, sys
from pathlib import Path
from PySide6.QtCore import QCoreApplication
from services.single_instance import SingleInstance
app=QCoreApplication(['radar_activation_test'])
instance=SingleInstance(Path(sys.argv[1]),timeout_ms=1500)
try:
    print(json.dumps({'primary':instance.acquire_or_activate()}),flush=True)
finally:
    instance.close()
'''


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'radar.lock'
        self.instances=[]
        self.windows=[]
        self.previous_quit=self.app.quitOnLastWindowClosed()
        self.app.setQuitOnLastWindowClosed(False)

    def tearDown(self):
        for instance in self.instances:
            instance.close()
        for window in self.windows:
            window.close()
        self.app.processEvents()
        self.app.setQuitOnLastWindowClosed(self.previous_quit)
        self.temp.cleanup()

    def instance(self,timeout=2500):
        value=SingleInstance(self.path,timeout)
        self.instances.append(value)
        return value

    def pump_until(self,predicate,seconds=5):
        deadline=time.monotonic()+seconds
        while not predicate() and time.monotonic()<deadline:
            self.app.processEvents()
            time.sleep(.005)
        self.assertTrue(predicate(),'Qt/IPC等待超时')

    def child(self):
        process=subprocess.Popen([sys.executable,'-c',CHILD,str(self.path)],
            cwd=Path(__file__).resolve().parents[1],stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            text=True,encoding='utf-8')
        try:
            self.pump_until(lambda:process.poll() is not None)
            stdout,stderr=process.communicate(timeout=1)
            self.assertEqual(process.returncode,0,stderr)
            return json.loads(stdout)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_second_process_restores_minimized_main_and_exits_without_primary(self):
        primary=self.instance()
        self.assertTrue(primary.acquire_or_activate())
        window=QWidget(); self.windows.append(window)
        window.showMinimized()
        self.app.processEvents()
        self.assertTrue(window.isMinimized())
        calls=[]
        primary.activation_requested.connect(lambda:(calls.append(1),wake_window(window)))
        self.assertFalse(self.child()['primary'])
        self.assertEqual(calls,[1])
        self.assertTrue(window.isVisible())
        self.assertFalse(window.isMinimized())
        self.assertTrue(primary.primary)
        # 多次点击仍复用同一主实例。
        self.assertFalse(self.child()['primary'])
        self.assertEqual(len(calls),2)

    def test_startup_race_retries_until_primary_listener_ready(self):
        primary=self.instance()
        self.assertTrue(primary.lock.tryLock(0))
        calls=[]
        primary.activation_requested.connect(lambda:calls.append(1))
        QTimer.singleShot(350,primary._listen)
        self.assertFalse(self.child()['primary'])
        self.assertEqual(calls,[1])

    def test_legacy_instance_no_channel_reports_error_without_taking_lock(self):
        old=QLockFile(str(self.path)); old.setStaleLockTime(0)
        self.assertTrue(old.tryLock(0))
        try:
            secondary=self.instance(timeout=80)
            with self.assertRaisesRegex(RuntimeError,'v1.1.0'):
                secondary.acquire_or_activate()
            self.assertFalse(secondary.primary)
            self.assertTrue(old.isLocked())
        finally:
            old.unlock()

    def test_close_releases_channel_and_lock_for_normal_restart(self):
        first=self.instance()
        self.assertTrue(first.acquire_or_activate())
        first.close()
        second=self.instance()
        self.assertTrue(second.acquire_or_activate())

    def test_different_install_paths_do_not_share_channel_names(self):
        first=self.instance()
        second=SingleInstance(self.path.parent/'other'/'radar.lock')
        self.instances.append(second)
        self.assertNotEqual(first.name,second.name)

    def test_partial_message_is_buffered_and_unknown_command_is_rejected(self):
        primary=self.instance()
        self.assertTrue(primary.acquire_or_activate())
        calls=[]
        primary.activation_requested.connect(lambda:calls.append(1))
        socket=QLocalSocket()
        socket.connectToServer(primary.name)
        self.assertTrue(socket.waitForConnected(300))
        socket.write(b'act'); socket.flush()
        self.pump_until(lambda:bool(primary.clients))
        self.app.processEvents()
        self.assertEqual(calls,[])
        socket.write(b'ivate\n'); socket.flush()
        self.pump_until(lambda:len(calls)==1)
        self.pump_until(lambda:not primary.clients)
        socket.abort()
        bad=QLocalSocket(); bad.connectToServer(primary.name)
        self.assertTrue(bad.waitForConnected(300))
        bad.write(b'run game command\n'); bad.flush()
        self.pump_until(lambda:bad.state()==QLocalSocket.LocalSocketState.UnconnectedState)
        self.assertEqual(calls,[1])

    def test_hidden_maximized_state_is_preserved_and_offscreen_window_is_recovered(self):
        window=QWidget(); self.windows.append(window)
        window.showMaximized(); self.app.processEvents()
        window.hide()
        wake_window(window)
        self.assertTrue(window.isVisible())
        self.assertTrue(window.windowState() & Qt.WindowState.WindowMaximized)
        window.showNormal(); window.move(-100000,-100000)
        wake_window(window)
        self.assertTrue(any(s.availableGeometry().intersects(window.frameGeometry()) for s in self.app.screens()))
