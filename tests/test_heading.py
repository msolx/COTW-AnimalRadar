"""视角矩阵与可选读取门禁；纯模拟，不打开游戏。"""
import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest
import config
from services.heading import parse_camera_world,bearing,screen_direction
from memory.animal_reader import AnimalReader
from memory.offsets import load_field_test_offsets,UnsupportedBuild
from memory.process_reader import ReadError
from tests.test_core import FakeMemory,O

def matrix(degrees=0):
    angle = math.radians(degrees)
    c,s = math.cos(angle),math.sin(angle)
    return struct.pack('<16f',c,0,s,0, 0,1,0,0, -s,0,c,0, 100,20,200,1)

class HeadingTests(unittest.TestCase):
    def test_cardinal_vectors_and_both_radar_orientations(self):
        for degrees,expected in ((0,(0,-1)),(90,(1,0)),(180,(0,1)),(270,(-1,0))):
            with self.subTest(degrees=degrees):
                position,direction = parse_camera_world(matrix(degrees))
                self.assertEqual(position,(100,20,200))
                for actual,target in zip(direction,expected): self.assertAlmostEqual(actual,target)
                self.assertAlmostEqual((bearing(direction)-degrees+180)%360-180,0,places=5)
                x,y = screen_direction(direction,True)
                self.assertAlmostEqual(x,expected[0])
                self.assertAlmostEqual(y,expected[1])
                x,y = screen_direction(direction,False)
                self.assertAlmostEqual(y,-expected[1])

    def test_invalid_matrices_and_vertical_direction(self):
        values = list(struct.unpack('<16f',matrix()))
        for index,value in ((0,float('nan')),(0,2),(4,.5),(3,1),(15,0),(0,-1),(12,1e9)):
            bad = values.copy()
            bad[index] = value
            with self.subTest(index=index,value=value),self.assertRaises(ValueError):
                parse_camera_world(struct.pack('<16f',*bad))
        with self.assertRaises(ValueError): parse_camera_world(b'')
        raw = struct.pack('<16f',1,0,0,0, 0,0,1,0, 0,-1,0,0, 100,20,200,1)
        self.assertIsNone(parse_camera_world(raw)[1])
        for direction in (None,(0,0),(float('nan'),1)):
            self.assertIsNone(screen_direction(direction,True))

    def test_optional_reader_latches_invalid_heading_without_retaining_arrow(self):
        memory = FakeMemory()
        offsets = dict(O,camera_world=O['camera']-48)
        address = memory.base+offsets['camera_world']
        memory.data[address] = matrix(90)
        reader = AnimalReader(memory,offsets)
        self.assertEqual(reader.scan().player.view_status,'valid')
        bad = list(struct.unpack('<16f',matrix()))
        bad[0] = 2
        memory.data[address] = struct.pack('<16f',*bad)
        failed = reader.scan()
        self.assertEqual(failed.player.view_status,'invalid')
        self.assertIsNone(failed.player.view_direction)
        self.assertEqual(len(failed.animals),1)
        del memory.data[address]
        self.assertEqual(reader.scan().player.view_status,'invalid')
        self.assertEqual(AnimalReader(memory,O).scan().player.view_status,'unverified')

    def test_memory_failure_is_not_bypassed_by_optional_fallback(self):
        with self.assertRaises(ReadError):
            AnimalReader(FakeMemory(),dict(O,camera_world=O['camera']-48)).scan()

    def test_heading_has_independent_hash_and_evidence_gate(self):
        profile = json.loads((config.OFFSETS_DIR/'field_test_25131233.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root/'field_test_heading.json'
            def load(data,digest=profile['sha256']):
                path.write_text(json.dumps(data),encoding='utf-8')
                return load_field_test_offsets(root,digest)
            self.assertIn('camera_world',load(profile))
            unverified = copy.deepcopy(profile)
            unverified.pop('heading_validation')
            self.assertNotIn('camera_world',load(unverified))
            for check in ('north_observed','east_observed','stationary_turn_observed'):
                bad = copy.deepcopy(profile)
                bad['heading_validation'][check] = False
                with self.assertRaises(UnsupportedBuild): load(bad)
            bad = copy.deepcopy(profile)
            bad['offsets']['camera_world'] += 4
            with self.assertRaises(UnsupportedBuild): load(bad)
            with self.assertRaises(UnsupportedBuild): load(profile,'b'*64)
