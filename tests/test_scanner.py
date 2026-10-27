"""用事件控制采样竞争，无需连接游戏或长时间等待。"""
import threading
import time
import unittest
from PySide6.QtCore import Qt
from models.player import Snapshot
from services.scanner import Scanner


class ScannerTests(unittest.TestCase):
    def test_paused_reconnect_resynchronizes_pause_then_resumes(self):
        paused,reset = threading.Event(),threading.Event()
        class Source:
            calls = 0
            suspends = 0
            closed = False
            def suspend(self):
                self.suspends += 1
                if self.suspends == 1: paused.set()
                else: reset.set()
            def reconnect(self): pass
            def scan(self):
                self.calls += 1
                return Snapshot(None,(),time.time(),'resumed',False)
            def close(self): self.closed = True
        source = Source()
        scanner = Scanner(lambda:source,60)
        scanner.pause_refresh()
        results = []
        def receive(snapshot):
            results.append(snapshot)
            scanner.stop()
        scanner.snapshot.connect(receive,Qt.ConnectionType.DirectConnection)
        scanner.start()
        try:
            self.assertTrue(paused.wait(2))
            scanner.request_reconnect()
            self.assertTrue(reset.wait(2))
            self.assertEqual(source.calls,0)
            scanner.resume_refresh()
            self.assertTrue(scanner.wait(2000))
            self.assertEqual(len(results),1)
            self.assertEqual(results[0].generation,3)
            self.assertTrue(source.closed)
        finally:
            scanner.stop()
            scanner.wait(2000)

    def test_factory_failure_waits_for_explicit_reconnect(self):
        failed = threading.Event()
        attempts = []
        class Source:
            closed = False
            def scan(self): return Snapshot(None,(),time.time(),'recovered',False)
            def close(self): self.closed = True
        source = Source()
        def factory():
            attempts.append(1)
            if len(attempts) == 1:
                raise RuntimeError('初始化失败')
            return source
        scanner = Scanner(factory,60)
        results = []
        def receive(snapshot):
            results.append(snapshot.message)
            if snapshot.message == 'recovered':
                scanner.stop()
            else:
                failed.set()
        scanner.snapshot.connect(receive,Qt.ConnectionType.DirectConnection)
        scanner.start()
        try:
            self.assertTrue(failed.wait(2))
            self.assertEqual(len(attempts),1)
            scanner.request_reconnect()
            self.assertTrue(scanner.wait(2000))
            self.assertEqual(len(attempts),2)
            self.assertEqual(results[-1],'recovered')
            self.assertTrue(source.closed)
        finally:
            scanner.stop()
            scanner.wait(2000)

    def test_pause_resume_drops_inflight_result(self):
        entered,release = threading.Event(),threading.Event()
        class Source:
            calls = 0
            closed = False
            def scan(self):
                self.calls += 1
                if self.calls == 1:
                    entered.set()
                    if not release.wait(2):
                        raise RuntimeError('测试未释放采样')
                return Snapshot(None,(),time.time(),f'frame-{self.calls}',False)
            def close(self): self.closed = True
        source = Source()
        scanner = Scanner(lambda:source,0.01)
        results = []
        def receive(snapshot):
            results.append(snapshot)
            scanner.stop()
        scanner.snapshot.connect(receive,Qt.ConnectionType.DirectConnection)
        scanner.start()
        try:
            self.assertTrue(entered.wait(2))
            scanner.pause_refresh()
            scanner.resume_refresh()
            release.set()
            self.assertTrue(scanner.wait(2000))
            self.assertEqual([s.message for s in results],['frame-2'])
            self.assertEqual(results[0].generation,2)
            self.assertTrue(source.closed)
        finally:
            release.set()
            scanner.stop()
            scanner.wait(2000)

    def test_stop_while_paused_releases_source(self):
        paused = threading.Event()
        class Source:
            closed = False
            def suspend(self): paused.set()
            def scan(self): raise AssertionError('暂停期间不应采样')
            def close(self): self.closed = True
        source = Source()
        scanner = Scanner(lambda:source,60)
        scanner.pause_refresh()
        scanner.start()
        try:
            self.assertTrue(paused.wait(2))
        finally:
            scanner.stop()
            self.assertTrue(scanner.wait(2000))
        self.assertTrue(source.closed)

    def test_reconnect_wakes_long_refresh_interval(self):
        first = threading.Event()
        class Source:
            calls = 0
            reconnects = 0
            def reconnect(self): self.reconnects += 1
            def scan(self):
                self.calls += 1
                return Snapshot(None,(),time.time(),'sample',False)
            def close(self): pass
        source = Source()
        scanner = Scanner(lambda:source,60)
        def receive(snapshot):
            if source.calls == 1:
                first.set()
            else:
                scanner.stop()
        scanner.snapshot.connect(receive,Qt.ConnectionType.DirectConnection)
        scanner.start()
        try:
            self.assertTrue(first.wait(2))
            scanner.request_reconnect()
            self.assertTrue(scanner.wait(2000))
            self.assertEqual(source.reconnects,1)
            self.assertEqual(source.calls,2)
        finally:
            scanner.stop()
            scanner.wait(2000)
