"""只读评分的潜在奖牌预测；不把难度、体重或最终收获检查当作奖牌。"""
import json
import math
from pathlib import Path
from services.species import canonical

GRADES = ('bronze','silver','gold','diamond')
RANK = {'none':0,'bronze':1,'silver':2,'gold':3,'diamond':4,'great_one':5}
LABELS = {'none':'未达铜牌','bronze':'铜牌','silver':'白银','gold':'黄金','diamond':'钻石','great_one':'珍奇'}
COLORS = {'silver':'#d4e9f7','gold':'#ffd45f','diamond':'#00f0ff','great_one':'#ff6bdf'}


class TrophyCatalog:
    def __init__(self,data):
        if (not isinstance(data,dict) or type(data.get('schema_version')) is not int
                or data['schema_version']!=1 or not isinstance(data.get('species'),dict)
                or not isinstance(data.get('source'),str) or not data['source'].startswith('https://github.com/')):
            raise ValueError('奖牌阈值版本或来源异常')
        self.source = data['source']
        self.species = {}
        ambiguous = set()
        for name,spec in data['species'].items():
            if not isinstance(name,str) or not isinstance(spec,dict):
                continue
            key = canonical(name)
            try:
                bands = spec['bands']
                points = [(bands[g]['min'],bands[g]['max']) for g in GRADES]
                if not all(type(v) in (int,float) and math.isfinite(v) and v>=0 for pair in points for v in pair):
                    continue
                if any(lo>hi for lo,hi in points) or any(points[i][0]>=points[i+1][0] for i in range(3)):
                    continue  # 无正常奖牌区间的任务/特殊物种不强行分类
            except (KeyError,TypeError):
                continue
            normalized = dict(bands=bands,great_one_supported=spec.get('great_one_supported') is True)
            if key in self.species and self.species[key]!=normalized:
                ambiguous.add(key)
            else:
                self.species[key] = normalized
        for key in ambiguous:
            self.species.pop(key,None)

    @classmethod
    def load(cls,path:Path):
        return cls(json.loads(path.read_text(encoding='utf-8')))

    def predict(self,species,score,*,great_one=False):
        if type(score) not in (int,float) or not math.isfinite(score) or score<0:
            return None
        spec = self.species.get(canonical(species))
        if spec is None:
            return None
        if great_one:
            return 'great_one' if spec['great_one_supported'] else None
        bands = spec['bands']
        if score>bands['diamond']['max']:
            return None  # 不将异常/模组高分直接判为钻石
        for grade in reversed(GRADES):
            if score>=bands[grade]['min']:
                return grade
        return 'none'


def silver_or_better(animal):
    if animal.status!='loaded' or RANK.get(animal.trophy_prediction,0)<2:
        return False
    score = animal.trophy_score
    if type(score) not in (int,float) or not math.isfinite(score):
        return False
    if animal.trophy_source=='mock':
        return animal.score_source=='mock'
    return (animal.trophy_source=='community_threshold_prediction' and animal.score_source=='save_join'
            and animal.attribute_identity is not None and animal.attribute_save_timestamp is not None)


def region_quality(region):
    members = [a for a in region.members if silver_or_better(a)]
    if not members:
        return 0,None
    return len(members),max((a.trophy_prediction for a in members),key=RANK.get)


def trophy_text(animal):
    score = animal.trophy_score
    score_text = f'{score:.3f}' if type(score) in (int,float) and math.isfinite(score) else '未知'
    if animal.score_source=='save_join' and score_text!='未知':
        score_text += '（存档匹配）'
    grade = LABELS.get(animal.trophy_prediction)
    medal_text = ('未达铜牌（预测）' if animal.trophy_prediction=='none' else '潜在'+grade+'（预测）') if grade else '未知'
    if animal.trophy_source=='mock':
        medal_text += '（模拟）'
    return score_text,medal_text
