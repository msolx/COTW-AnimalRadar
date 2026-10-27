"""无需第三方依赖的回归测试；所有内存均为内置假数据。"""
import json
import ctypes
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from memory.animal_reader import AnimalReader,parse_position,GameNotReady
from memory.offsets import load_offsets,UnsupportedBuild,CHECKS
from memory.process_reader import ReadError,valid_pointer,ProcessReader
from models.animal import Animal
from services.coordinate import horizontal_distance,radar_point,aggregate
from services.mock import MockSource
from services.species import chinese,from_resource

O = dict(animals=0x100,camera=0x200,manager_vector=0x20,species=0x28,
         position=0x148,ragdoll=0xC0,hpmax=0x178,hp=0x17C)

class FakeMemory:
    base = 0x10000
    def __init__(self):
        self.data = {}
        self.put(self.base+O['camera'],'3f',100,20,200)
        self.put(self.base+O['animals'],'Q',0x20000)
        self.put(0x20008,'Q',0x30000)
        self.put(0x30020,'QQ',0x40000,0x40008)
        self.put(0x40000,'Q',0x50000)
        self.put(0x50028,'Q',0x60000)
        self.put(0x600C0,'Q',0x70000)
        self.data[0x70000] = b'/animals/blacktail_deer/a.ragdoll\0'.ljust(160,b'\0')
        self.put(0x50148,'3f',103,99,204)
        self.put(0x50178,'f',100)
        self.put(0x5017C,'f',100)
    def put(self,address,fmt,*values):
        self.data[address] = struct.pack('<'+fmt,*values)
    def read(self,address,size):
        data = self.data.get(address)
        if data is None or len(data) != size:
            raise ReadError('假内存不可读')
        return data

class CoreTests(unittest.TestCase):
    def test_continuous_radar_accepts_66_and_512_then_unloads(self):
        import config
        self.assertEqual(config.FIELD_TEST_MAX_ENTITIES,config.MAX_ANIMALS)
        self.assertLessEqual(config.FIELD_TEST_MAX_ENTITIES*8,config.MAX_READ_BYTES)
        for count in (66,config.MAX_ANIMALS):
            with self.subTest(count=count):
                memory = FakeMemory()
                pointers = [0x50000+i*0x1000 for i in range(count)]
                memory.put(0x30020,'QQ',0x40000,0x40000+count*8)
                memory.put(0x40000,'Q'*count,*pointers)
                for ptr in pointers:
                    memory.put(ptr+O['species'],'Q',0x60000)
                    memory.put(ptr+O['position'],'3f',103,99,204)
                    memory.put(ptr+O['hpmax'],'f',100)
                    memory.put(ptr+O['hp'],'f',100)
                reader = AnimalReader(memory,O,max_entities=config.FIELD_TEST_MAX_ENTITIES)
                self.assertEqual(len(reader.scan().animals),count)
                memory.put(0x30020,'QQ',0x40000,0x40008)
                memory.put(0x40000,'Q',pointers[0])
                self.assertEqual(len(reader.scan().animals),1)

    def test_entity_count_above_limit_does_not_read_pointer_array(self):
        import config
        memory = FakeMemory()
        memory.put(0x30020,'QQ',0x40000,0x40000+(config.MAX_ANIMALS+1)*8)
        original = memory.read
        reads = []
        def tracked(address,size):
            reads.append((address,size))
            return original(address,size)
        memory.read = tracked
        with self.assertRaisesRegex(ReadError,'513.*512'):
            AnimalReader(memory,O,max_entities=config.FIELD_TEST_MAX_ENTITIES).scan()
        self.assertFalse(any(address == 0x40000 for address,size in reads))

    def test_uncreated_manager_waits_without_reading_camera(self):
        memory = FakeMemory()
        memory.put(memory.base+O['animals'],'Q',0)
        del memory.data[memory.base+O['camera']]
        with self.assertRaises(GameNotReady):
            AnimalReader(memory,O).scan()
        memory.put(memory.base+O['animals'],'Q',0x20000)
        memory.put(0x20008,'Q',0)
        with self.assertRaises(GameNotReady):
            AnimalReader(memory,O).scan()

    def test_position(self):
        self.assertEqual(parse_position(struct.pack('<3f',1,2,3)),(1,2,3))
        for data in (b'',struct.pack('<3f',float('nan'),0,0),struct.pack('<3f',1e9,0,0)):
            with self.assertRaises(ReadError):
                parse_position(data)

    def test_horizontal_distance(self):
        self.assertEqual(horizontal_distance((0,1000,0),(3,-1000,4)),5)

    def test_species(self):
        for name,label in [('blacktail deer','黑尾鹿'),('whitetail deer','白尾鹿'),('moose','驼鹿')]:
            self.assertEqual(chinese(name),label)
        self.assertEqual(from_resource(b'/animals/blacktail_deer/file\0'), 'blacktail deer')
        self.assertEqual(from_resource(b'/animals/blacktail/file\0'), 'blacktail deer')
        self.assertEqual(from_resource(b'/animals/whitetail/file\0'), 'whitetail deer')
        self.assertEqual(chinese('blacktail'),'黑尾鹿')
        self.assertIsNone(from_resource(b'random'))

    def test_reader(self):
        s = AnimalReader(FakeMemory(),O).scan()
        self.assertEqual(len(s.animals),1)
        self.assertEqual(s.animals[0].position,(103,99,204))
        self.assertEqual(s.animals[0].species,'blacktail deer')

    def test_empty(self):
        m = FakeMemory()
        m.put(0x30020,'QQ',0,0)
        self.assertEqual(AnimalReader(m,O).scan().animals,())
        self.assertEqual(aggregate([], (0,0,0)),[])

    def test_invalid_pointer_vector(self):
        self.assertFalse(valid_pointer(0))
        self.assertFalse(valid_pointer(0xFFFFFFFFFFFFFFFF))
        for begin,end in [(0x40000,0x40007),(0x40000,0x40000+513*8),(0x40008,0x40000)]:
            m = FakeMemory()
            m.put(0x30020,'QQ',begin,end)
            with self.assertRaises(ReadError):
                AnimalReader(m,O).scan()

    def test_invalid_health_and_dead(self):
        m = FakeMemory()
        m.put(0x5017C,'f',0)
        dead = AnimalReader(m,O).scan().animals
        self.assertEqual(len(dead),1)
        self.assertEqual(dead[0].vital_status,'dead')
        self.assertEqual(dead[0].health_percent,0)
        m.put(0x5017C,'f',float('nan'))
        with self.assertRaises(ReadError):
            AnimalReader(m,O).scan()

    def test_unload_and_object_release(self):
        m = FakeMemory()
        reader = AnimalReader(m,O)
        self.assertEqual(len(reader.scan().animals),1)
        m.put(0x30020,'QQ',0,0)
        self.assertEqual(reader.scan().animals,())
        m.put(0x30020,'QQ',0x40000,0x40008)
        del m.data[0x50148]
        with self.assertRaises(ReadError):
            reader.scan()

    def test_list_race(self):
        m = FakeMemory()
        original = m.read
        calls = 0
        def changing(address,size):
            nonlocal calls
            if address == 0x30020:
                calls += 1
                if calls == 2:
                    return struct.pack('<QQ',0,0)
            return original(address,size)
        m.read = changing
        with self.assertRaises(ReadError):
            AnimalReader(m,O).scan()

    def test_grid(self):
        animals = [Animal('a','moose',(-1,0,-1),0),Animal('b','moose',(-49,9,-49),0),
                   Animal('c','blacktail deer',(-1,0,-1),0)]
        regions = aggregate(animals,(0,0,0),'moose')
        self.assertEqual(len(regions),1)
        self.assertEqual(regions[0].count,2)
        self.assertEqual(regions[0].position,(-25,0,-25))
        self.assertEqual((regions[0].distance_min,regions[0].distance_max),(0,100))

    def test_radar_conversion(self):
        self.assertEqual(radar_point((50,999,100),(0,0,0),200,400),(100,-200))

    def test_version_gate(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            with self.assertRaises(UnsupportedBuild):
                load_offsets(path,'a'*64)
            data = dict(sha256='a'*64,verified=False,offsets=O)
            file = path/'test.json'
            file.write_text(json.dumps(data),encoding='utf-8')
            with self.assertRaises(UnsupportedBuild):
                load_offsets(path,'a'*64)
            data.update(verified=True,validation={**dict.fromkeys(CHECKS,True),'date':'test only','notes':'synthetic fixture'})
            file.write_text(json.dumps(data),encoding='utf-8')
            self.assertEqual(load_offsets(path,'a'*64),O)

    def test_mock_lifecycle(self):
        source = MockSource()
        snapshots = [source.scan() for _ in range(23)]
        self.assertEqual(len(snapshots[0].animals),9)
        self.assertEqual(sum(a.species == 'blacktail deer' for a in snapshots[0].animals),4)
        self.assertEqual(sum(a.species == 'whitetail deer' for a in snapshots[0].animals),3)
        self.assertEqual(sum(a.species == 'moose' for a in snapshots[0].animals),2)
        self.assertNotEqual(snapshots[0].player.position,snapshots[1].player.position)
        self.assertNotEqual(snapshots[0].animals[0].position,snapshots[1].animals[0].position)
        self.assertEqual(len(snapshots[8].animals),7)
        self.assertFalse(snapshots[18].connected)
        self.assertIsNone(snapshots[18].player)
        self.assertEqual(snapshots[18].animals,())
        self.assertTrue(snapshots[22].connected)

    def test_live_exit_cleanup(self):
        from services.live import LiveSource
        class ClosedMemory:
            closed = False
            def alive(self): return False
            def connect(self): raise ReadError('游戏已退出')
            def close(self): self.closed = True
        with patch('services.live.ProcessReader',return_value=ClosedMemory()):
            source = LiveSource()
            source.reader = object()
            result = source.scan()
            self.assertFalse(result.connected)
            self.assertEqual(result.animals,())
            self.assertIsNone(source.reader)
            self.assertTrue(source.memory.closed)

    def test_memory_region_guard_and_partial_read(self):
        # 假 API 验证保护位、跨区验证和部分读取；不打开任何进程。
        class API:
            protect = 4
            partial = False
            queries = 0
            def VirtualQueryEx(self,handle,address,out,size):
                self.queries += 1
                mbi = out._obj
                mbi.BaseAddress = address
                mbi.RegionSize = 4
                mbi.State = 0x1000
                mbi.Protect = self.protect
                return size
            def ReadProcessMemory(self,handle,address,buffer,size,count):
                ctypes.memmove(buffer,b'12345678',size)
                count._obj.value = size-1 if self.partial else size
                return 1
        reader = object.__new__(ProcessReader)
        reader.api,reader.handle = API(),1
        reader.alive = lambda: True
        self.assertEqual(reader.read(0x10000,8),b'12345678')
        self.assertEqual(reader.api.queries,2)
        for protection in (1,0x104,0x10):
            reader.api.protect = protection
            with self.assertRaises(ReadError):
                reader.read(0x10000,8)
        reader.api.protect = 4
        reader.api.partial = True
        with patch('memory.process_reader.C.get_last_error',return_value=299,create=True):
            with self.assertRaises(ReadError):
                reader.read(0x10000,8)

    def test_process_closed_before_read(self):
        reader = object.__new__(ProcessReader)
        reader.alive = lambda: False
        reader.close = lambda: setattr(reader,'handle',None)
        reader.handle = 1
        with self.assertRaises(ReadError):
            reader.read(0x10000,8)
        self.assertIsNone(reader.handle)

if __name__ == '__main__':
    unittest.main()
