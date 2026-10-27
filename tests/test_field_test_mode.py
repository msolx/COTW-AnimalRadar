"""现场测试不能误入正式门禁，且未验证生命值字段必须完全不读取。"""
import json
from pathlib import Path
import tempfile
import unittest

from memory.animal_reader import AnimalReader
from memory.offsets import load_field_test_offsets,load_offsets,UnsupportedBuild
from memory.process_reader import ReadError
from tests.test_core import FakeMemory,O


class FieldTestModeTests(unittest.TestCase):
    def test_unknown_health_is_not_read_or_used_to_hide_entities(self):
        memory = FakeMemory()
        del memory.data[0x50178]
        del memory.data[0x5017C]
        offsets = {k:v for k,v in O.items() if k not in ('hp','hpmax')}
        result = AnimalReader(memory,offsets,health_verified=False).scan()
        self.assertEqual(len(result.animals),1)
        self.assertEqual(result.animals[0].vital_status,'unknown')
        self.assertIn('生命状态未知',result.message)

    def test_over_limit_is_not_silently_truncated(self):
        memory = FakeMemory()
        memory.put(0x30020,'QQ',0x40000,0x40000+65*8)
        with self.assertRaises(ReadError):
            AnimalReader(memory,O,health_verified=False,max_entities=64).scan()

    def test_profile_requires_core_evidence_and_cannot_pass_formal_gate(self):
        source = Path(__file__).resolve().parents[1]/'offsets'/'field_test_25131233.json'
        data = json.loads(source.read_text(encoding='utf-8'))
        data.pop('health_validation',None)  # 此用例始终测试未开放健康字段的旧配置
        digest = data['sha256']
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            profile = root/'field_test_sample.json'
            profile.write_text(json.dumps(data),encoding='utf-8')
            offsets = load_field_test_offsets(root,digest)
            self.assertNotIn('hp',offsets)
            self.assertNotIn('hpmax',offsets)
            with self.assertRaises(UnsupportedBuild):
                load_offsets(root,digest)
            with self.assertRaises(UnsupportedBuild):
                load_field_test_offsets(root,'b'*64)
            data['validation']['position_observed'] = False
            profile.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(UnsupportedBuild):
                load_field_test_offsets(root,digest)
