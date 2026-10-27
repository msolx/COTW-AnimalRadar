"""个体属性格式化；未验证值保留未知，健康比例不冒充战利品完整度。"""
import math
import time
from services.trophy import trophy_text

STATE_LABELS = {'alive':'存活','wounded':'受伤','dead':'已死亡','unknown':'未知'}
FUR_LABELS = {'brown':'褐色','dark_brown':'深褐色','light_brown':'浅褐色','tan':'棕黄色',
    'black':'黑色','gray':'灰色','grey':'灰色','dark':'深色','light':'浅色','blonde':'金色',
    'albino':'白化','melanistic':'黑化','piebald':'花斑','leucistic':'白变',
    'mosaic':'马赛克','acromelanistic':'肢端黑色','common':'普通','red_brown':'红褐色'}

def matches_state(actual,wanted):
    if wanted is None:
        return True
    # 受伤也是存活，不能被“存活”筛选误删。
    return actual in ('alive','wounded') if wanted == 'alive' else actual == wanted

def health_state(current,maximum):
    if (not all(math.isfinite(v) for v in (current,maximum))
        or not 0 < maximum <= 1e7 or not 0 <= current <= maximum):
        raise ValueError('生命值异常，需要重新验证结构')
    percent = current/maximum*100
    return ('dead' if current == 0 else 'wounded' if current < maximum else 'alive'),percent

def details_row(animal):
    percent = animal.health_percent
    health = (f'{percent:.1f}%' if percent is not None and math.isfinite(percent)
              and 0 <= percent <= 100 else '未知')
    level = animal.difficulty
    level_text = str(level) if type(level) is int and 1 <= level <= 10 else '未知'
    sex_text = {'male':'雄性','female':'雌性'}.get(animal.sex,'未知')
    if animal.sex and animal.sex_source == 'save_join':
        sex_text += '（存档匹配）'
    fur_text = FUR_LABELS.get(animal.fur_color,animal.fur_color) or '未知'
    if animal.fur_color and animal.fur_source == 'seed_estimate':
        fur_text += '（推算）'
    if level_text != '未知' and animal.difficulty_source == 'weight_estimate':
        level_text += '（估算）'
    return (STATE_LABELS.get(animal.vital_status,'未知'),sex_text,health,fur_text,level_text)

def animal_tooltip(animal):
    state,sex,health,fur,level = details_row(animal)
    text = f'状态：{state} · 性别：{sex}\n生命值比例：{health} · 毛色：{fur} · 难度：{level}'
    score,trophy = trophy_text(animal)
    text += f'\n存档评分：{score} · 评级：{trophy}'
    if animal.trophy_prediction is not None:
        text += '\n评级是预测；TruRACS和收获检查可能改变最终结算结果'
    if animal.attribute_save_timestamp is not None:
        text += '\n匹配存档时间：'+time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(animal.attribute_save_timestamp))
        text += '\n体重/评分/外观种子唯一匹配；毛色与难度尚待游戏观察核对'
    return text
