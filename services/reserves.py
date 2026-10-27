"""保护区名录是筛选依据，不是实时动物数据或内存中的保护区识别结果。

19区资料核对日期及来源见 data/reserves.json 和 RESERVE_CATALOG.md。
内部资源名与公开亚种名不一定相同；
例如 reindeer 对应公开名 Mountain Reindeer，暂不改写真实资源身份。
"""
import json
from datetime import date
from pathlib import Path
import config
from services.species import canonical,NAMES

def load_catalog(path):
    """坏名录必须显式报错，不悄悄退回不完整的列表或全物种列表。"""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if data.get('schema_version') != 1:
        raise ValueError('保护区名录格式版本不支持')
    date.fromisoformat(data['reviewed_on'])
    entries, sources = data['reserves'],data['sources']
    if len(entries) != config.EXPECTED_RESERVE_COUNT:
        raise ValueError('保护区名录数量与配置不符，请重新核对')
    ids, labels = set(),set()
    for entry in entries:
        key, label, names = entry['id'],entry['name_zh'],entry['species']
        if not key or key in ids or not label or label in labels or not entry['name_en']:
            raise ValueError('保护区标识或名称重复/缺失')
        ids.add(key)
        labels.add(label)
        if (not names or len(names) != entry['expected_count'] or len(set(names)) != len(names)
            or any(name != canonical(name) or name not in NAMES for name in names)):
            raise ValueError(f'{key} 的物种数量、名称或中文翻译异常')
        missions = entry.get('mission_only',[])
        if (len(set(missions)) != len(missions) or set(missions) & set(names)
            or any(name not in NAMES or name != canonical(name) for name in missions)):
            raise ValueError(f'{key} 的任务专属物种异常')
        if not entry['sources'] or any(not sources.get(s,'').startswith('https://') for s in entry['sources']):
            raise ValueError(f'{key} 缺少可追溯资料来源')
    return data

CATALOG = load_catalog(config.RESERVE_CATALOG_FILE)
RESERVES = {entry['id']:(entry['name_zh'],tuple(entry['species'])) for entry in CATALOG['reserves']}
MISSION_ONLY = {entry['id']:tuple(entry.get('mission_only',())) for entry in CATALOG['reserves']}

def mission_species(reserve):
    """任务动物不混入普通种群名录；只有真实采样出现时才添加带说明选项。"""
    return MISSION_ONLY.get(reserve,())

def species_for(reserve, observed=()):
    """未收录的保护区只展示本次采样名称，不累积其它地图的菜单。"""
    if reserve in RESERVES:
        return RESERVES[reserve][1]
    return tuple(sorted({canonical(name) for name in observed}))

def unexpected_species(reserve, observed):
    if reserve not in RESERVES:
        return ()
    return tuple(sorted({canonical(name) for name in observed}
                        - set(species_for(reserve)) - set(mission_species(reserve))))
