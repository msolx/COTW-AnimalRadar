"""候选结构解析器：只有版本门禁放行后可由 LiveSource 调用。"""
import struct
import time
from config import MAX_ANIMALS, MAX_DISTANCE
from memory.process_reader import ReadError, valid_pointer
from models.animal import Animal
from models.player import Player, Snapshot
from services.coordinate import valid_position, horizontal_distance
from services.species import from_resource
from services.heading import parse_camera_world
from services.animal_details import health_state
from services.attribute_resolver import parse_identity


class GameNotReady(ReadError):
    """哈希已匹配，但管理器尚未创建；与坏指针或权限拒绝区分。"""
    pass

def parse_position(data):
    try:
        pos = struct.unpack('<3f',data)
    except struct.error as exc:
        raise ReadError('坐标字节长度错误') from exc
    if not valid_position(pos):
        raise ReadError('非有限值或异常坐标')
    return pos

class AnimalReader:
    def __init__(self,memory,offsets,health_verified=True,max_entities=MAX_ANIMALS,identity_enabled=False):
        self.memory,self.o = memory,offsets
        self.health_verified = health_verified
        self.max_entities = min(max_entities,MAX_ANIMALS)
        self.heading_disabled = False  # 基结构异常后停止可选朝向读取，重连才重新验证
        self.identity_enabled = identity_enabled and all(k in offsets for k in ('identity_weight','identity_seed'))

    def pointer(self,address,allow_null=False):
        ptr = struct.unpack('<Q',self.memory.read(address,8))[0]
        if ptr == 0 and allow_null:
            return 0
        if not valid_pointer(ptr):
            raise ReadError('空指针或非用户态指针')
        return ptr

    def vector(self):
        o = self.o
        root = self.pointer(self.memory.base+o['animals'],allow_null=True)
        if root == 0:
            raise GameNotReady('等待保护区加载：动物管理器尚未创建')
        manager = self.pointer(root+8,allow_null=True)
        if manager == 0:
            raise GameNotReady('等待保护区加载：动物管理器尚未创建')
        raw = self.memory.read(manager+o['manager_vector'],16)
        begin,end = struct.unpack('<QQ',raw)
        if begin == end and (begin == 0 or valid_pointer(begin)):
            return manager,raw,()
        if not valid_pointer(begin) or not valid_pointer(end) or end < begin or (end-begin)%8:
            raise ReadError('动物列表边界异常，拒绝遍历')
        if (end-begin)//8 > self.max_entities:
            raise ReadError(f'已加载动物数量{(end-begin)//8}超出本轮上限{self.max_entities}，拒绝遍历')
        pointers = struct.unpack(f'<{(end-begin)//8}Q',self.memory.read(begin,end-begin))
        if any(not valid_pointer(p) for p in pointers) or len(set(pointers)) != len(pointers):
            raise ReadError('动物列表含无效或重复指针')
        return manager,raw,pointers

    def scan(self):
        now,o = time.time(),self.o
        manager,vector,pointers = self.vector()
        direction,status = None,'invalid' if self.heading_disabled else 'unverified'
        if 'camera_world' in o and not self.heading_disabled:
            # 矩阵内包含原来已验证的位置，同一块读取避免位置/朝向跨帧。
            raw = self.memory.read(self.memory.base+o['camera_world'],64)
            position = parse_position(raw[48:60])
            try:
                position,direction = parse_camera_world(raw)
                status = 'valid' if direction is not None else 'vertical'
            except ValueError:
                self.heading_disabled = True
                status = 'invalid'
        else:
            position = parse_position(self.memory.read(self.memory.base+o['camera'],12))
        player = Player(position,now,view_direction=direction,view_status=status)
        animals = []
        for ptr in pointers:
            # 不跨扫描缓存实体或物种指针，失败即整帧失效，不继续显示旧位置。
            definition = self.pointer(ptr+o['species'])
            path = self.pointer(definition+o['ragdoll'])
            name = from_resource(self.memory.read(path,160))
            pos = parse_position(self.memory.read(ptr+o['position'],12))
            state,percent = 'unknown',None
            identity,identity_raw = None,None
            if self.health_verified:
                hpmax = struct.unpack('<f',self.memory.read(ptr+o['hpmax'],4))[0]
                hp = struct.unpack('<f',self.memory.read(ptr+o['hp'],4))[0]
                try:
                    state,percent = health_state(hp,hpmax)
                except ValueError as exc:
                    raise ReadError(str(exc)) from exc
            if self.identity_enabled:
                identity_raw = self.memory.read(ptr+o['identity_weight'],24)
                try:
                    identity = parse_identity(identity_raw)
                except ValueError:
                    self.identity_enabled = False  # 可选结构异常后该连接不再尝试，不影响位置/健康门禁
                if self.memory.read(ptr+o['identity_weight'],24) != identity_raw:
                    raise ReadError('动物个体标识在采样时变化')
            if self.pointer(ptr+o['species']) != definition:
                raise ReadError('动物对象在采样时变化')
            if name and horizontal_distance(pos,player.position) <= MAX_DISTANCE:
                animals.append(Animal(f'{manager:x}:{ptr:x}',name,pos,now,
                                      vital_status=state,health_percent=percent,
                                      attribute_identity=identity,
                                      details_source='verified_memory' if self.health_verified else 'unknown'))
        # 双读列表降低加载/释放竞争风险；普通 RPM 无法保证原子快照。
        manager2,vector2,pointers2 = self.vector()
        if (manager,vector,pointers) != (manager2,vector2,pointers2):
            raise ReadError('场景或动物列表采样中发生变化，请等待下一次刷新')
        message = '只读数据 · 摄像机近似 · 保护区未知 · 世界坐标朝向'
        if not self.health_verified:
            message += ' · 生命状态未知，可能包含死亡动物'
        return Snapshot(player,tuple(animals),now,message,scene_id=f'{manager:x}')
