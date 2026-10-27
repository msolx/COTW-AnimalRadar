import time
import json
from dataclasses import replace
import config
from config import OFFSETS_DIR
from memory.process_reader import ProcessReader, GameNotRunning
from memory.offsets import load_offsets, load_field_test_offsets, UnsupportedBuild
from memory.animal_reader import AnimalReader,GameNotReady
from models.player import Snapshot
from services.coordinate import horizontal_distance

class LiveSource:
    def __init__(self,field_test=False):
        self.memory = ProcessReader()
        self.reader = None
        self.blocked = False
        self.field_test = field_test
        self.frames = 0
        self.connections = 0
        self.failures = 0
        self.consecutive_failures = 0
        self.scene_changes = 0
        self.last_scene = None
        self.last_player = None
        self.next_connect_at = 0
        self.started = time.monotonic()
        self.last_success = None
        self.error = '等待连接游戏'
        self.suspended = False
        self.waiting_checks = 0
        self.connection_state = 'waiting_for_game'
        self.last_read_error = None  # 恢复/关闭后保留最后原因，便于区分切屏巧合和实际读取失败
        self.attributes = None
        if field_test and config.DETAILS_JOIN_ENABLED:
            from services.attribute_resolver import AttributeResolver
            self.attributes = AttributeResolver()

    def set_reserve(self,reserve):
        if self.attributes:
            self.attributes.set_reserve(reserve)

    def set_details_enabled(self,enabled):
        enabled = enabled and self.field_test
        if enabled == (self.attributes is not None):
            return  # 不因每轮同步重新开启本连接已因异常停用的可选结构
        if enabled and self.attributes is None:
            from services.attribute_resolver import AttributeResolver
            self.attributes = AttributeResolver()
        elif not enabled and self.attributes is not None:
            self.attributes = None
        if self.reader:
            self.reader.identity_enabled = bool(self.attributes and
                all(k in self.reader.o for k in ('identity_weight','identity_seed')))

    def scan(self):
        self.suspended = False
        if self.blocked:
            self.connection_state = 'blocked'
            return self._failure_snapshot()
        try:
            new_connection = False
            if self.reader is None or not self.memory.alive():
                if time.monotonic() < self.next_connect_at:
                    return self._failure_snapshot()
                self.reader = None
                self.connection_state = 'connecting'
                self.memory.connect()
                if self.field_test:
                    offsets = load_field_test_offsets(OFFSETS_DIR,self.memory.sha256)
                    self.reader = AnimalReader(self.memory,offsets,health_verified=all(k in offsets for k in ('hp','hpmax')),
                                               max_entities=config.FIELD_TEST_MAX_ENTITIES,
                                               identity_enabled=self.attributes is not None)
                else:
                    self.reader = AnimalReader(self.memory,load_offsets(OFFSETS_DIR,self.memory.sha256))
                self.connections += 1
                new_connection = self.connections > 1
            result = self.reader.scan()
            if self.attributes:
                self.attributes.refresh()
                result = replace(result,animals=tuple(self.attributes.enrich(a) for a in result.animals),
                                 message=result.message+' · '+self.attributes.message)
            changed = (new_connection or
                (self.last_scene is not None and result.scene_id != self.last_scene) or
                (self.last_player is not None and horizontal_distance(result.player.position,self.last_player)
                 > config.SCENE_JUMP_METERS))
            self.last_scene, self.last_player = result.scene_id,result.player.position
            if changed:
                self.scene_changes += 1
            result = replace(result,scene_changed=changed,scene_id=f'{self.connections}:{result.scene_id}',
                             game_pid=getattr(self.memory,'pid',0) or 0)
            self.consecutive_failures = 0
            self.last_success = result.timestamp
            self.connection_state = 'connected'
            if self.field_test:
                result = replace(result,player=replace(result.player,reserve=config.FIELD_TEST_RESERVE_LABEL),
                                 message='现场测试 · '+result.message)
                self.frames += 1
                self._record_status(result)
            return result
        except Exception as exc:
            self.memory.close()
            self.reader = None
            self.error = str(exc)
            self.last_scene, self.last_player = None,None
            self.next_connect_at = time.monotonic()+config.RECONNECT_SECONDS
            if isinstance(exc,(GameNotRunning,GameNotReady)):
                self.waiting_checks += 1
                self.consecutive_failures = 0
                self.connection_state = 'waiting_for_game' if isinstance(exc,GameNotRunning) else 'waiting_for_reserve'
            else:
                self.failures += 1
                self.consecutive_failures += 1
                self.connection_state = 'retrying'
                self.last_read_error = {'timestamp':time.time(),'type':type(exc).__name__,
                                        'message':self.error,'stage':getattr(exc,'stage',None),
                                        'winerror':getattr(exc,'winerror',None)}
            # 权限/版本错误后不反复尝试打开进程；用户显式重连才解除。
            # 只按结构化错误识别权限拒绝；“拒绝遍历”是数据校验提示，不是系统访问拒绝。
            self.blocked = isinstance(exc,UnsupportedBuild) or getattr(exc,'winerror',None) == 5
            if self.consecutive_failures >= config.MAX_CONSECUTIVE_SCAN_FAILURES:
                self.blocked = True
                self.error += f'；连续{self.consecutive_failures}次失败，已停止自动尝试，请检查后重新连接'
            if self.blocked:
                self.connection_state = 'blocked'
            return self._failure_snapshot()

    def _failure_snapshot(self):
        result = Snapshot(None,(),time.time(),self.error,False)
        if self.field_test:
            self._record_status(result)
        return result

    def suspend(self):
        self.suspended = True
        self.connection_state = 'paused'
        if self.field_test:
            self._record_status(Snapshot(None,(),time.time(),'刷新已暂停，无实时标记',False))

    def _record_status(self,result):
        # 仅写诊断摘要，不保存实体地址、原始内存或世界坐标。
        report = {'timestamp':result.timestamp, 'connected':result.connected,
                  'successful_frames':self.frames, 'entity_count':len(result.animals),
                  'entity_limit':getattr(self.reader,'max_entities',config.FIELD_TEST_MAX_ENTITIES),
                  'vital_counts':{},
                  'species_counts':{}, 'message':result.message,
                  'field_test':True, 'health_read_enabled':bool(getattr(self.reader,'health_verified',False)),
                  'read_failures':self.failures, 'connection_count':self.connections,
                  'scene_changes':self.scene_changes, 'paused':self.suspended,
                  'waiting_checks':self.waiting_checks, 'connection_state':self.connection_state,
                  'last_success_timestamp':self.last_success,
                  'last_read_error':self.last_read_error,
                  'attribute_trial_enabled':self.attributes is not None,
                  'attribute_matched_count':sum(a.sex_source == 'save_join' for a in result.animals),
                  'attribute_message':self.attributes.message if self.attributes else '属性试验未开启',
                  'view_status':result.player.view_status if result.player else 'unavailable',
                  'uptime_seconds':round(time.monotonic()-self.started,1)}
        for animal in result.animals:
            counts = report['species_counts']
            counts[animal.species] = counts.get(animal.species,0)+1
            vital = report['vital_counts']
            vital[animal.vital_status] = vital.get(animal.vital_status,0)+1
        try:
            temporary = config.FIELD_TEST_STATUS_FILE.with_suffix('.tmp')
            temporary.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary.replace(config.FIELD_TEST_STATUS_FILE)
        except OSError:
            pass  # 本地摘要失败不影响采样结果，也不改变游戏访问权限。

    def close(self):
        self.memory.close()
        self.reader = None
        if self.attributes:
            self.attributes.clear('已断开，属性匹配已清理')
            self.attributes.next_check = 0
        self.suspended = False
        self.connection_state = 'closed'
        if self.field_test:
            self._record_status(Snapshot(None,(),time.time(),'现场测试已关闭，句柄已释放',False))

    def reconnect(self):
        self.close()
        self.blocked = False
        self.next_connect_at = 0
        self.consecutive_failures = 0
        self.error = '等待重新连接'
        self.connection_state = 'connecting'
        if self.field_test:
            self._record_status(Snapshot(None,(),time.time(),self.error,False))
