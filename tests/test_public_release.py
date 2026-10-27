"""公开仓库入口和数据门禁回归；不连接游戏。"""
import ast
import json
from pathlib import Path
import unittest
from memory.offsets import load_field_test_offsets,UnsupportedBuild

ROOT=Path(__file__).resolve().parents[1]


class PublicReleaseTests(unittest.TestCase):
    def test_main_explicitly_uses_real_hash_gated_source(self):
        tree=ast.parse((ROOT/'main.py').read_text(encoding='utf-8'))
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call)
               and isinstance(n.func,ast.Name) and n.func.id=='MainWindow']
        self.assertEqual(len(calls),1)
        value=next(k.value for k in calls[0].keywords if k.arg=='source')
        self.assertEqual(ast.unparse(value),'config.FIELD_TEST_SOURCE')

    def test_release_profile_preserves_unknown_build_rejection(self):
        profile=json.loads((ROOT/'offsets/field_test_25131233.json').read_text(encoding='utf-8'))
        result=load_field_test_offsets(ROOT/'offsets',profile['sha256'])
        self.assertIn('position',result)
        with self.assertRaises(UnsupportedBuild):
            load_field_test_offsets(ROOT/'offsets','0'*64)

    def test_packaging_keeps_data_and_has_no_helper(self):
        source=(ROOT/'COTW_AnimalRadar.spec').read_text(encoding='utf-8')
        self.assertIn("['main.py']",source)
        self.assertNotIn('upx=True',source)
        self.assertFalse((ROOT/'solo_helper').exists())
        for file in ('reserves.json','attribute_estimates.json','trophy_thresholds.json'):
            self.assertTrue((ROOT/'data'/file).is_file())
