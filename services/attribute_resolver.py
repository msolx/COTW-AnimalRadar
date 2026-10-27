"""用已核对三字段唯一关联存档属性；拒绝重复记录，不使用位置或动物序号关联。"""
from dataclasses import dataclass,replace
import json
import math
import struct
import time
import config
from services.population_file import stable_read,decompress_population,PopulationADF,animal_nodes,PopulationError
from services.species import canonical
from services.trophy import TrophyCatalog


@dataclass(frozen=True)
class SavedAttributes:
    identity: tuple[float,float,int]
    sex: str
    great_one: bool


def parse_identity(raw):
    if len(raw) != 24:
        raise ValueError('个体标识块长度错误')
    weight,score = struct.unpack_from('<ff',raw)
    seed, = struct.unpack_from('<I',raw,20)
    if not math.isfinite(weight) or not math.isfinite(score) or not 0 < weight <= 1e6 or not 0 <= score <= 1e9:
        raise ValueError('个体体重或评分异常')
    return weight,score,seed


def records_from_adf(adf):
    result = []
    for root in adf.roots:
        for node in animal_nodes(root):
            f = node.value
            if 'IsGreatOne' in f:
                flag = f['IsGreatOne'].value
            elif 'FeatureModifiers' in f:
                flag = f['FeatureModifiers'].value['Flags'].value & 1
            else:
                flag = None
            if flag not in (0,1):
                raise PopulationError('无法确认记录的 Great One 标志')
            result.append(SavedAttributes((f['Weight'].value,f['Score'].value,f['VisualVariationSeed'].value),
                          'male' if f['Gender'].value == 1 else 'female',bool(flag)))
    return result


def unique_index(records):
    index = {}
    for record in records:
        # 同一标识出现第二次，即使性别相同也禁用；不能用“第一个”消除歧义。
        index[record.identity] = record if record.identity not in index else None
    return index


def estimate_fur(seed,table):
    """社区种子模型，只给出推算结果。不能称为从实时模型材质直接读取。"""
    if type(seed) is not int or not 0 <= seed <= 0xffffffff or not table:
        return None
    total = table.get('fur_total_probability')
    furs = table.get('furs',{})
    if (not isinstance(total,(int,float)) or not math.isfinite(total) or total <= 0
            or any(not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0 for v in furs.values())
            or not math.isclose(sum(furs.values()),total,rel_tol=1e-6)):
        return None
    state = (0x343fd*seed+0x269ec3) & 0xffffffff
    bits = (((state >> 16) | 0x3f8000) << 8) & 0xffffffff
    probability = abs(struct.unpack('<f',struct.pack('<I',bits))[0])-1
    cumulative = 0.0
    for name,weight in furs.items():
        if weight <= 0:
            continue  # 0概率的任务专属皮毛不能因种子恰在边界而被选中
        cumulative += weight/total
        if probability <= cumulative:
            return name
    return None


def estimate_difficulty(weight,levels,great_one=False):
    if great_one:
        return 10
    if not math.isfinite(weight) or weight <= 0:
        return None
    weight = round(weight,2 if weight > 10 else 3)
    matches = []
    for level,(low,high) in enumerate(levels,1):
        high = round(high,2 if high > 10 else 3)
        if low <= weight <= high:
            matches.append(level)
    return matches[0] if len(matches) == 1 and matches[0] <= 9 else None


class AttributeResolver:
    def __init__(self):
        data = json.loads(config.ATTRIBUTE_ESTIMATES_FILE.read_text(encoding='utf-8'))
        self.catalog = {canonical(k):v for k,v in data['species'].items()}
        try:
            self.trophies = TrophyCatalog.load(config.TROPHY_THRESHOLDS_FILE)
        except (OSError,ValueError,KeyError,TypeError):
            self.trophies = None  # 不影响其它只读属性；没有有效阈值时评级未知
        self.reserve = None
        self.index = {}
        self.save_timestamp = None
        self.next_check = 0
        self.message = '尚未选择保护区，属性未关联'

    def set_reserve(self,reserve):
        if reserve != self.reserve:
            self.reserve = reserve
            self.clear('保护区变化，等待属性存档')
            self.next_check = 0

    def clear(self,message):
        self.index = {}
        self.save_timestamp = None
        self.message = message

    def refresh(self):
        number = config.POPULATION_RESERVE_IDS.get(self.reserve)
        if number is None:
            self.clear('未确认保护区，属性不关联')
            return
        if time.monotonic() < self.next_check:
            return
        self.next_check = time.monotonic()+config.POPULATION_RELOAD_SECONDS
        try:
            path = config.POPULATION_SAVE_DIR/f'animal_population_{number}'
            raw,stamp = stable_read(path)
            adf = PopulationADF(decompress_population(raw))
            self.index = unique_index(records_from_adf(adf))
            self.save_timestamp = stamp
            self.message = '性别来自三字段唯一匹配存档；毛色推算、难度估算'
        except (OSError,ValueError,KeyError,TypeError) as exc:
            self.clear(f'属性存档不可用：{exc}')

    def enrich(self,animal):
        record = self.index.get(animal.attribute_identity)
        if record is None:
            if animal.trophy_source=='community_threshold_prediction':
                return replace(animal,trophy_score=None,score_source='unknown',trophy_prediction=None,trophy_source='unknown')
            return animal
        spec = self.catalog.get(canonical(animal.species),{})
        gender = ('great_one_' if record.great_one else '')+record.sex
        fur = estimate_fur(record.identity[2],spec.get('gender',{}).get(gender))
        level = estimate_difficulty(record.identity[0],spec.get('level',[]),record.great_one)
        trophy = self.trophies.predict(animal.species,record.identity[1],great_one=record.great_one) if self.trophies else None
        return replace(animal,sex=record.sex,fur_color=fur,difficulty=level,
            sex_source='save_join',fur_source='seed_estimate' if fur else 'unknown',
            difficulty_source='weight_estimate' if level is not None else 'unknown',
            attribute_save_timestamp=self.save_timestamp,trophy_score=record.identity[1],score_source='save_join',
            trophy_prediction=trophy,trophy_source='community_threshold_prediction' if trophy is not None else 'unknown')
