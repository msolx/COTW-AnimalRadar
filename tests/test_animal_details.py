"""个体属性、尸体生命周期和可选字段门禁；所有内存是模拟数据。"""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import config
from memory.offsets import load_field_test_offsets,UnsupportedBuild
from memory.animal_reader import AnimalReader
from models.animal import Animal
from services.animal_details import health_state,details_row,matches_state
from services.coordinate import aggregate
from services.mock import MockSource
from tests.test_core import FakeMemory,O

class AnimalDetailsTests(unittest.TestCase):
    def test_health_classification_and_invalid_data(self):
        self.assertEqual(health_state(100,100),('alive',100))
        self.assertEqual(health_state(25,100),('wounded',25))
        self.assertEqual(health_state(0,100),('dead',0))
        self.assertTrue(matches_state('wounded','alive'))
        self.assertFalse(matches_state('dead','alive'))
        self.assertFalse(matches_state('unknown','alive'))
        for current,maximum in ((-1,100),(101,100),(0,0),(1,float('inf')),(float('nan'),100)):
            with self.assertRaises(ValueError): health_state(current,maximum)

    def test_unknown_attributes_are_not_invented(self):
        animal = Animal('a','reindeer',(0,0,0),100)
        self.assertEqual(details_row(animal),('未知','未知','未知','未知','未知'))
        self.assertIsNone(animal.sex)
        self.assertIsNone(animal.difficulty)
        memory = FakeMemory()
        memory.data[0x70000] = b'/animals/wild_boar/wild_boar_male_internal_ragdoll_100.ragdoll\0'.ljust(160,b'\0')
        parsed = AnimalReader(memory,O).scan().animals[0]
        self.assertIsNone(parsed.sex)  # 共享骨架文件含male也不是个体性别证据
        self.assertIsNone(parsed.fur_color)
        self.assertIsNone(parsed.difficulty)

    def test_death_retained_until_entity_unloads(self):
        memory = FakeMemory()
        reader = AnimalReader(memory,O)
        self.assertEqual(reader.scan().animals[0].vital_status,'alive')
        memory.put(0x5017C,'f',45)
        self.assertEqual(reader.scan().animals[0].vital_status,'wounded')
        memory.put(0x5017C,'f',0)
        for _ in range(2):
            corpse = reader.scan().animals[0]
            self.assertEqual(corpse.vital_status,'dead')
            self.assertEqual(corpse.health_percent,0)
            self.assertIsNone(corpse.sex)
            self.assertIsNone(corpse.fur_color)
        memory.put(0x30020,'QQ',0,0)
        self.assertEqual(reader.scan().animals,())

    def test_grid_does_not_merge_living_with_corpses(self):
        live = Animal('live','moose',(10,0,10),100,vital_status='alive')
        dead = Animal('dead','moose',(11,0,11),100,vital_status='dead',health_percent=0)
        regions = aggregate((live,dead),(0,0,0))
        self.assertEqual(len(regions),2)
        self.assertEqual({r.vital_status for r in regions},{'alive','dead'})
        self.assertTrue(all(r.count == 1 and len(r.members) == 1 for r in regions))
        remaining = aggregate((live,),(0,0,0))
        self.assertEqual(len(remaining),1)
        self.assertEqual(remaining[0].vital_status,'alive')

    def test_health_requires_independent_evidence(self):
        data = json.loads((config.OFFSETS_DIR/'field_test_25131233.json').read_text(encoding='utf-8'))
        data['health_validation'] = dict(verified=True,date='2026-10-21',living_observed=True,
                                       corpse_observed=True,corpse_removed_observed=True,notes='模拟门禁测试')
        data['offsets'].update(hp=0x17c,hpmax=0x178)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/'field_test_details.json'
            def load(profile,digest=data['sha256']):
                path.write_text(json.dumps(profile),encoding='utf-8')
                return load_field_test_offsets(root,digest)
            self.assertEqual(load(data)['hp'],0x17c)
            for key in ('living_observed','corpse_observed','corpse_removed_observed'):
                bad = copy.deepcopy(data)
                bad['health_validation'][key] = False
                with self.assertRaises(UnsupportedBuild): load(bad)
            bad = copy.deepcopy(data)
            bad['health_validation']['verified'] = False
            self.assertNotIn('hp',load(bad))
            bad = copy.deepcopy(data)
            bad['offsets']['hp'] += 4
            with self.assertRaises(UnsupportedBuild): load(bad)
            with self.assertRaises(UnsupportedBuild): load(data,'b'*64)

    def test_mock_has_injury_death_and_collection_without_changing_sex(self):
        source = MockSource()
        frames = [source.scan() for _ in range(14)]
        find = lambda i:next(a for a in frames[i].animals if a.entity_id == 'mock-0')
        self.assertEqual(find(0).vital_status,'alive')
        self.assertEqual(find(6).vital_status,'wounded')
        self.assertEqual(find(10).vital_status,'dead')
        self.assertFalse(any(a.entity_id == 'mock-0' for a in frames[13].animals))
        for frame in frames:
            for animal in frame.animals:
                if animal.entity_id == 'mock-8': self.assertEqual(animal.sex,'male')
