import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from models.player import Player,Snapshot
from models.animal import Animal
from memory.process_reader import ReadError,GameNotRunning
from memory.offsets import UnsupportedBuild
from memory.animal_reader import GameNotReady
from services.live import LiveSource


def frame(scene='a',x=0):
    return Snapshot(Player((x,0,0),100),
                    (Animal('temporary','whitetail deer',(x+10,0,0),100),),100,
                    'fake',scene_id=scene)


class Memory:
    active = False
    available = True
    pid = 123
    sha256 = 'a'*64
    connects = 0
    closes = 0
    def alive(self): return self.active
    def connect(self):
        self.connects += 1
        if not self.available:
            raise GameNotRunning('未找到游戏进程')
        self.active = True
    def close(self):
        self.closes += 1
        self.active = False


class LiveLifecycleTests(unittest.TestCase):
    def test_validation_refusal_is_not_access_denial(self):
        source,_,clock,_ = self.make_source([ReadError('动物列表边界异常，拒绝遍历'),frame()])
        self.assertFalse(source.scan().connected)
        self.assertFalse(source.blocked)
        self.assertEqual(source.consecutive_failures,1)
        clock[0] += 4
        self.assertTrue(source.scan().connected)
        self.assertEqual(source.consecutive_failures,0)

    def test_last_read_error_survives_recovery_and_close(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'status.json'
            self.enterContext(patch('config.FIELD_TEST_STATUS_FILE',path))
            source,_,clock,_ = self.make_source([ReadError('采样期间列表变化'),frame()],field_test=True)
            self.assertFalse(source.scan().connected)
            clock[0] += 4
            self.assertTrue(source.scan().connected)
            source.close()
            report = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(report['last_read_error']['message'],'采样期间列表变化')
            self.assertEqual(report['read_failures'],1)
            self.assertEqual(report['successful_frames'],1)

    def test_loading_wait_is_not_a_read_error_or_circuit_breaker(self):
        source,_,clock,_ = self.make_source([GameNotReady('等待保护区加载')]*5+[frame()])
        for _ in range(5):
            self.assertFalse(source.scan().connected)
            self.assertEqual(source.connection_state,'waiting_for_reserve')
            clock[0] += 4
        self.assertFalse(source.blocked)
        self.assertEqual(source.failures,0)
        self.assertEqual(source.waiting_checks,5)
        self.assertTrue(source.scan().connected)
        self.assertEqual(source.connection_state,'connected')

    def make_source(self,actions,field_test=False):
        memory = Memory()
        clock = [10.0]
        class Reader:
            def scan(self):
                action = actions.pop(0)
                if isinstance(action,Exception): raise action
                return action
        self.enterContext(patch('services.live.ProcessReader',return_value=memory))
        self.enterContext(patch('services.live.AnimalReader',return_value=Reader()))
        loader = self.enterContext(patch('services.live.load_offsets',return_value={}))
        self.enterContext(patch('services.live.load_field_test_offsets',return_value={}))
        self.enterContext(patch('services.live.time.monotonic',side_effect=lambda:clock[0]))
        return LiveSource(field_test=field_test),memory,clock,loader

    def test_exit_clears_data_waits_and_reconnects(self):
        source,memory,clock,_ = self.make_source([frame(),frame()])
        self.assertTrue(source.scan().connected)
        memory.active,memory.available = False,False
        disconnected = source.scan()
        self.assertFalse(disconnected.connected)
        self.assertEqual(source.failures,0)
        self.assertEqual(source.waiting_checks,1)
        self.assertEqual(source.connection_state,'waiting_for_game')
        self.assertEqual(disconnected.animals,())
        self.assertIsNone(source.reader)
        attempts = memory.connects
        self.assertFalse(source.scan().connected)
        self.assertEqual(memory.connects,attempts)
        memory.available = True
        clock[0] += 4
        reconnected = source.scan()
        self.assertTrue(reconnected.connected)
        self.assertTrue(reconnected.scene_changed)
        self.assertEqual(source.connections,2)

    def test_changed_manager_and_position_jump_invalidate_scene(self):
        source,_,_,_ = self.make_source([frame('a'),frame('a',20),frame('b',20),
                                        frame('b',21),frame('b',900)])
        flags = [source.scan().scene_changed for _ in range(5)]
        self.assertEqual(flags,[False,False,True,False,True])
        self.assertEqual(source.scene_changes,2)

    def test_three_structure_failures_stop_until_explicit_reconnect(self):
        source,memory,clock,_ = self.make_source([ReadError('对象已释放')]*3+[frame()])
        for _ in range(3):
            self.assertFalse(source.scan().connected)
            clock[0] += 4
        self.assertTrue(source.blocked)
        attempts = memory.connects
        self.assertFalse(source.scan().connected)
        self.assertEqual(memory.connects,attempts)
        source.reconnect()
        self.assertTrue(source.scan().connected)
        self.assertFalse(source.blocked)

    def test_restarted_game_rechecks_build_before_reading(self):
        source,memory,_,loader = self.make_source([frame()])
        self.assertTrue(source.scan().connected)
        memory.active = False
        loader.side_effect = UnsupportedBuild('不支持新的哈希')
        result = source.scan()
        self.assertFalse(result.connected)
        self.assertEqual(result.animals,())
        self.assertTrue(source.blocked)
        self.assertIsNone(source.reader)

    def test_pause_and_close_write_no_live_coordinates(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'status.json'
            self.enterContext(patch('config.FIELD_TEST_STATUS_FILE',path))
            source,_,_,_ = self.make_source([frame(),frame()],field_test=True)
            self.assertTrue(source.scan().connected)
            source.suspend()
            paused = json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(paused['connected'])
            self.assertTrue(paused['paused'])
            self.assertEqual(paused['entity_count'],0)
            self.assertNotIn('position',paused)
            source.reconnect()
            reconnecting = json.loads(path.read_text(encoding='utf-8'))
            self.assertEqual(reconnecting['connection_state'],'connecting')
            self.assertFalse(reconnecting['connected'])
            source.suspend()
            self.assertTrue(json.loads(path.read_text(encoding='utf-8'))['paused'])
            self.assertTrue(source.scan().connected)
            source.close()
            closed = json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(closed['connected'])
            self.assertEqual(closed['successful_frames'],2)
