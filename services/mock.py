"""可复现的演示：九只动物、移动、卸载、断开和重连。"""
import math
import time
from dataclasses import replace
from config import MOCK_DISCONNECT_TICK, MOCK_RECONNECT_TICK
from models.animal import Animal
from models.player import Player, Snapshot

class MockSource:
    def __init__(self):
        self.tick = -1

    def scan(self):
        self.tick += 1
        t, now = self.tick, time.time()
        if MOCK_DISCONNECT_TICK <= t % 30 < MOCK_RECONNECT_TICK:
            return Snapshot(None, (), now, '模拟：游戏已断开', False)
        player = Player((1000+t*2, 20, 2000+t), now, '模拟莱顿湖区', '模拟玩家',
                        (math.sin(t/6),-math.cos(t/6)),'valid')
        names = ['blacktail deer']*4 + ['whitetail deer']*3 + ['moose']*2
        # 模拟：个体0健康下降→死亡→确认后消失，不写入真实游戏。
        phase = t % 30
        animals = tuple(Animal(f'mock-{i}', name,
                        (1100+i*22+math.sin(t/3)*8, 20+i, 2050+i*17), now)
                        for i,name in enumerate(names) if not (8 <= phase < 14 and i in (2,3))
                        and not (13 <= phase < 18 and i == 0))
        scores = (70,0,180,0,200,0,120,0,280)
        medals = ('bronze','none','diamond','none','gold','none','silver','none','diamond')
        animals = tuple(replace(a,sex='male' if i%2 == 0 else 'female',
                        fur_color=('棕色','深棕色','灰色')[i%3],difficulty=i%5+1,
                        vital_status=('dead' if 10 <= phase < 13 else 'wounded' if 6 <= phase < 10 else 'alive')
                                     if a.entity_id == 'mock-0' else 'alive',
                        health_percent=(0 if 10 <= phase < 13 else 45 if 6 <= phase < 10 else 100)
                                       if a.entity_id == 'mock-0' else 100,
                        details_source='mock',trophy_score=scores[i],score_source='mock',
                        trophy_prediction=medals[i],trophy_source='mock') for a in animals for i in (int(a.entity_id.split('-')[1]),))
        return Snapshot(player, animals, now, '模拟数据 · 非真实游戏坐标')

    def close(self):
        pass
