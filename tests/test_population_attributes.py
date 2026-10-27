"""合成ADF与内存测试，不打开真实存档或游戏。"""
import copy
import io
import json
import struct
import tempfile
import unittest
import zlib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import config
from services.population_file import PopulationADF,PopulationError,stable_read,decompress_population,animal_nodes
from services.attribute_resolver import (SavedAttributes,unique_index,parse_identity,
    records_from_adf,estimate_fur,estimate_difficulty,AttributeResolver)
from models.animal import Animal


def fixture_adf():
    names = ['AnimalData','Gender','Weight','Score','VisualVariationSeed','IsGreatOne','Id']
    fields = [(1,0x0CA2821D,1,0),(2,0x7515a207,4,4),(3,0x7515a207,4,8),
              (4,0x075e4e4f,4,16),(5,0x0CA2821D,1,12),(6,0x075e4e4f,4,20)]
    payload = struct.pack('<B3xffB3xIIff',1,450,180,0,123456789,0,0,0)
    typedef = struct.pack('<4IQ3II',1,32,4,0x1234,0,0,0,0,len(fields))
    for name,key,size,offset in fields:
        typedef += struct.pack('<Q4IQ',name,key,size,offset,0,0)
    nt = bytes(len(n) for n in names)+b''.join(n.encode()+b'\0' for n in names)
    total = 120+len(typedef)+len(nt)
    header = b' FDA'+struct.pack('<10I',4,1,96,1,120,0,0,len(names),120+len(typedef),total)+bytes(20)
    return header+payload+struct.pack('<4IQ',0,0x1234,64,32,0)+typedef+nt


def container(adf):
    payload = b'\x01\x01\0\0\0'+adf
    header = bytearray(32)
    header[:4],header[16:20] = b'SAVE',b'COMP'
    struct.pack_into('<I',header,8,len(payload))
    struct.pack_into('<I',header,24,len(payload))
    return bytes(header)+zlib.compress(payload)


class PopulationTests(unittest.TestCase):
    def test_schema_fields_and_zero_id_are_not_live_coordinates(self):
        parsed = PopulationADF(decompress_population(container(fixture_adf())))
        animals = list(animal_nodes(parsed.roots[0]))
        self.assertEqual(len(animals),1)
        record, = records_from_adf(parsed)
        self.assertEqual(record.identity,(450,180,123456789))
        self.assertEqual(record.sex,'male')
        self.assertFalse(record.great_one)
        self.assertEqual(animals[0].value['Id'].value,0)

    def test_bad_container_and_truncation_rejected(self):
        raw = container(fixture_adf())
        for value in (b'',raw[:30],b'NONE'+raw[4:],raw[:-3],raw+b'extra'):
            with self.subTest(length=len(value)),self.assertRaises(PopulationError):
                decompress_population(value)
        bad = bytearray(raw)
        struct.pack_into('<I',bad,8,config.POPULATION_MAX_BYTES+1)
        with self.assertRaises(PopulationError): decompress_population(bad)

    def test_unsupported_version_and_instance_bounds(self):
        for offset,value in ((4,99),(12,0xffffff00),(28,999999),(40,1)):
            data = bytearray(fixture_adf())
            struct.pack_into('<I',data,offset,value)
            with self.subTest(offset=offset),self.assertRaises(PopulationError): PopulationADF(data)

    def test_invalid_gender_fails_closed(self):
        data = bytearray(fixture_adf())
        data[64] = 0
        adf = PopulationADF(data)
        with self.assertRaises(PopulationError): list(animal_nodes(adf.roots[0]))

    def test_file_stability_and_no_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'animal_population_1'
            raw = container(fixture_adf())
            path.write_bytes(raw)
            before = path.stat()
            actual,_ = stable_read(path)
            self.assertEqual(actual,raw)
            self.assertEqual(path.stat().st_mtime_ns,before.st_mtime_ns)
        fake = SimpleNamespace(stat=lambda:SimpleNamespace(st_size=32,st_mtime_ns=1))
        streams = iter((io.BytesIO(b'A'*32),io.BytesIO(b'B'*32)))
        fake.open = lambda mode: next(streams)
        with self.assertRaises(PopulationError): stable_read(fake)


class AttributeTests(unittest.TestCase):
    def test_optional_trial_changes_generation_without_resuming_pause(self):
        from services.scanner import Scanner
        from services.mock import MockSource
        scanner = Scanner(MockSource,1)
        scanner.pause_refresh()
        generation = scanner.generation
        scanner.set_details_enabled(True)
        self.assertTrue(scanner.details_enabled)
        self.assertTrue(scanner.paused.is_set())
        self.assertGreater(scanner.generation,generation)
        self.assertTrue(scanner.reconnect_event.is_set())

    def test_disabling_trial_removes_reader_access(self):
        from services.live import LiveSource
        from unittest.mock import MagicMock
        with patch('services.live.ProcessReader',return_value=MagicMock()):
            source = LiveSource(field_test=True)
        reader = SimpleNamespace(identity_enabled=True,o={'identity_weight':0x19c,'identity_seed':0x1b0})
        source.reader = reader
        source.set_details_enabled(True)
        self.assertTrue(reader.identity_enabled)
        reader.identity_enabled = False
        source.set_details_enabled(True)
        self.assertFalse(reader.identity_enabled)  # 可选结构失败时不自行恢复
        source.set_details_enabled(False)
        self.assertIsNone(source.attributes)
        self.assertFalse(reader.identity_enabled)

    def test_identity_layout_and_invalid_floats(self):
        raw = bytearray(24)
        struct.pack_into('<ff',raw,0,450,180)
        struct.pack_into('<I',raw,20,123456789)
        self.assertEqual(parse_identity(raw),(450,180,123456789))
        with self.assertRaises(ValueError): parse_identity(raw[:-1])
        struct.pack_into('<f',raw,0,float('nan'))
        with self.assertRaises(ValueError): parse_identity(raw)

    def test_duplicate_records_never_choose_first(self):
        first = SavedAttributes((450,180,123456789),'male',False)
        second = replace(first,sex='female')
        self.assertIsNone(unique_index([first,second,first])[first.identity])

    def test_no_identity_or_wrong_identity_stays_unknown(self):
        resolver = AttributeResolver()
        animal = Animal('x','moose',(0,0,0),100)
        self.assertEqual(resolver.enrich(animal),animal)
        resolver.index[(450,180,123)] = SavedAttributes((450,180,123),'male',False)
        self.assertIsNone(resolver.enrich(replace(animal,attribute_identity=(450,180,124))).sex)

    def test_estimates_have_explicit_provenance(self):
        resolver = AttributeResolver()
        identity = (450,180,123456789)
        resolver.index = unique_index([SavedAttributes(identity,'male',False)])
        resolver.save_timestamp = 100
        animal = resolver.enrich(Animal('x','moose',(0,0,0),101,attribute_identity=identity))
        self.assertEqual(animal.sex,'male')
        self.assertEqual(animal.sex_source,'save_join')
        self.assertEqual(animal.difficulty,2)
        from services.animal_details import details_row
        row = details_row(animal)
        self.assertIn('存档匹配',row[1])
        self.assertIn('推算',row[3])
        self.assertIn('估算',row[4])
        resolver.set_reserve('medved')
        self.assertEqual(resolver.index,{})

    def test_missing_save_clears_previous_metadata(self):
        resolver = AttributeResolver()
        resolver.set_reserve('layton')
        resolver.index = {1:'old'}
        with patch('services.attribute_resolver.stable_read',side_effect=PopulationError('正在写入')):
            resolver.refresh()
        self.assertEqual(resolver.index,{})
        self.assertIsNone(resolver.save_timestamp)

    def test_seed_prediction_does_not_use_zero_probability_fur(self):
        self.assertEqual(estimate_fur(123,dict(fur_total_probability=1,furs={'mission':0,'brown':1})),'brown')
        self.assertIsNone(estimate_fur(-1,{}))
        self.assertIsNone(estimate_fur(123,dict(fur_total_probability=3,furs={'brown':1})))
        self.assertIsNone(estimate_difficulty(4,[[1,2],[5,7]]))
        self.assertEqual(estimate_difficulty(600,[],True),10)

    def test_reader_only_reads_identity_when_enabled_and_profile_has_keys(self):
        from tests.test_core import FakeMemory,O
        from memory.animal_reader import AnimalReader
        memory = FakeMemory()
        offsets = dict(O,identity_weight=0x19c,identity_seed=0x1b0)
        raw = bytearray(24)
        struct.pack_into('<ff',raw,0,450,180)
        struct.pack_into('<I',raw,20,123456789)
        memory.data[0x5019c] = bytes(raw)
        self.assertIsNone(AnimalReader(memory,offsets).scan().animals[0].attribute_identity)
        self.assertEqual(AnimalReader(memory,offsets,identity_enabled=True).scan().animals[0].attribute_identity,
                         (450,180,123456789))

    def test_identity_profile_gate(self):
        from memory.offsets import load_field_test_offsets,UnsupportedBuild
        profile = json.loads((config.OFFSETS_DIR/'field_test_25131233.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'field_test_identity.json'
            path.write_text(json.dumps(profile),encoding='utf-8')
            self.assertEqual(load_field_test_offsets(Path(folder),profile['sha256'])['identity_weight'],0x19c)
            profile['identity_validation']['joint_unique_match_observed'] = False
            path.write_text(json.dumps(profile),encoding='utf-8')
            with self.assertRaises(UnsupportedBuild): load_field_test_offsets(Path(folder),profile['sha256'])
