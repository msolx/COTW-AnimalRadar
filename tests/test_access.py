"""权限错误只用假API回归，不再次尝试访问游戏。"""
import ctypes as C
import unittest
from unittest.mock import patch
from memory.process_reader import ProcessReader,ProcessAccessError
from services.live import LiveSource


class AccessTests(unittest.TestCase):
    def test_enumeration_denial_is_not_reported_as_end(self):
        from memory.process_reader import PROCESSENTRY32W
        reader = object.__new__(ProcessReader)
        entry = PROCESSENTRY32W()
        def fail(snapshot, out):
            return 0
        with patch('memory.process_reader.C.set_last_error',create=True):
            with patch('memory.process_reader.C.get_last_error',return_value=5,create=True):
                with self.assertRaises(ProcessAccessError) as caught:
                    reader._enumeration_call(fail,1,entry,'process_next')
                self.assertEqual(caught.exception.winerror,5)
                self.assertEqual(caught.exception.stage,'process_next')
            with patch('memory.process_reader.C.get_last_error',return_value=18,create=True):
                self.assertFalse(reader._enumeration_call(fail,1,entry,'process_next'))

    def test_snapshot_reports_exact_stage(self):
        class API:
            calls = 0
            def CreateToolhelp32Snapshot(self,flags,pid):
                self.calls += 1
                return C.c_void_p(-1).value
        for flags,stage in ((2,'process_snapshot'),(0x18,'module_snapshot')):
            reader = object.__new__(ProcessReader)
            reader.api = API()
            with patch('memory.process_reader.C.get_last_error',return_value=5,create=True):
                with self.assertRaises(ProcessAccessError) as caught:
                    reader._snapshot(flags,123)
            self.assertEqual(caught.exception.stage,stage)
            self.assertEqual(caught.exception.winerror,5)
            self.assertEqual(reader.api.calls,1)

    def test_denied_source_does_not_retry(self):
        class DeniedMemory:
            calls = 0
            closes = 0
            def alive(self): return False
            def connect(self):
                self.calls += 1
                raise ProcessAccessError('module_snapshot',5)
            def close(self): self.closes += 1
        memory = DeniedMemory()
        with patch('services.live.ProcessReader',return_value=memory):
            source = LiveSource()
            first,second = source.scan(),source.scan()
        self.assertFalse(first.connected)
        self.assertEqual(first.animals,())
        self.assertEqual(second.message,first.message)
        self.assertEqual(memory.calls,1)
        self.assertEqual(memory.closes,1)
        self.assertTrue(source.blocked)

    def test_ctypes_x64_layout(self):
        from memory.process_reader import MODULEENTRY32W,PROCESSENTRY32W,MEMORY_BASIC_INFORMATION
        if C.sizeof(C.c_wchar) != 2 or C.sizeof(C.c_void_p) != 8:
            self.skipTest('仅验证Windows x64 ABI')
        self.assertEqual(C.sizeof(MODULEENTRY32W),1080)
        self.assertEqual(C.sizeof(PROCESSENTRY32W),568)
        self.assertEqual(C.sizeof(MEMORY_BASIC_INFORMATION),48)
        self.assertEqual(MEMORY_BASIC_INFORMATION.RegionSize.offset,24)
