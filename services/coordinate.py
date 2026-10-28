"""X/Z水平距离、相对坐标及网格聚合；地理朝向由界面校准设置控制。"""
import math
from dataclasses import dataclass
from config import GRID_METERS, MAX_COORDINATE

def valid_position(pos):
    return len(pos) == 3 and all(math.isfinite(v) and abs(v) <= MAX_COORDINATE for v in pos)

def horizontal_distance(a, b):
    return math.hypot(a[0] - b[0], a[2] - b[2])

def radar_point(pos, player, radius, pixels):
    return ((pos[0] - player[0]) / radius * pixels,
            -(pos[2] - player[2]) / radius * pixels)

@dataclass(frozen=True)
class Region:
    key: tuple
    species: str
    position: tuple
    count: int
    distance_min: float
    distance_max: float
    vital_status: str = 'unknown'
    members: tuple = ()  # 当前快照的个体，不跨帧保留释放后的对象

def aggregate(animals, player, species=None, size=GRID_METERS):
    if size <= 0:
        raise ValueError('网格尺寸必须为正')
    groups = {}
    for animal in animals:
        if animal.status != 'loaded' or (species and animal.species != species):
            continue
        state = animal.vital_status if animal.vital_status in ('alive','wounded','dead') else 'unknown'
        key = (animal.species, math.floor(animal.position[0]/size), math.floor(animal.position[2]/size),state)
        groups.setdefault(key,[]).append(animal)
    result = []
    for key, members in groups.items():
        _, x, z, state = key
        # 距离区间取玩家到整个网格的最短/最长距离，避免中心点误导。
        x0, z0 = x*size, z*size
        px, _, pz = player
        lo = math.hypot(max(x0-px, 0, px-x0-size), max(z0-pz, 0, pz-z0-size))
        hi = max(math.hypot(cx-px, cz-pz) for cx in (x0,x0+size) for cz in (z0,z0+size))
        result.append(Region(key, key[0], (x0+size/2, 0, z0+size/2), len(members),
                             math.floor(lo/size)*size, math.ceil(hi/size)*size,state,tuple(members)))
    return sorted(result, key=lambda r: (r.distance_min, r.key))
