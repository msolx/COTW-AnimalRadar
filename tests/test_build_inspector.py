import io
import struct
import unittest
from memory.build_inspector import inspect_pe,locate_rva


class BuildInspectorTests(unittest.TestCase):
    def test_headers_and_rva_boundaries(self):
        data = bytearray(1024)
        data[:2] = b'MZ'
        struct.pack_into('<I',data,0x3C,0x80)
        data[0x80:0x84] = b'PE\0\0'
        struct.pack_into('<HHIIIHH',data,0x84,0x8664,1,0,0,0,240,0)
        struct.pack_into('<H',data,0x98,0x20B)
        struct.pack_into('<I',data,0x98+56,0x3000)
        section = 0x98+240
        data[section:section+8] = b'.data\0\0\0'
        struct.pack_into('<IIII',data,section+8,0x1000,0x1000,0x200,0x200)
        struct.pack_into('<I',data,section+36,0xC0000040)
        pe = inspect_pe(io.BytesIO(data))
        self.assertEqual(pe['machine'],'AMD64')
        self.assertTrue(locate_rva(pe,0x1000,12)['writable'])
        self.assertEqual(locate_rva(pe,0x2000,12)['section'],None)
        self.assertFalse(locate_rva(pe,0x2FFF,12)['in_image'])
        self.assertEqual(locate_rva(pe,0x1FFF,12)['section'],None)

    def test_rejects_truncated_or_wrong_files(self):
        for data in (b'',b'MZ',b'not a PE file'):
            with self.assertRaises(ValueError):
                inspect_pe(io.BytesIO(data))
