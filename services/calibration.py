"""静止窗口摘要；仅描述世界坐标变化，不推断地理方向或玩家朝向。"""
import math
from statistics import median

from services.coordinate import valid_position


def summarize(positions):
    if not positions or any(not valid_position(p) for p in positions):
        raise ValueError('校准样本为空或坐标无效')
    center = tuple(median(p[i] for p in positions) for i in range(3))
    spread = max(math.dist(a,b) for a in positions for b in positions)
    return {'median_xyz': center, 'max_spread_3d_m': spread}


def compare(start, end):
    delta = tuple(b-a for a,b in zip(start,end))
    return {'delta_xyz':delta, 'horizontal_xz_m':math.hypot(delta[0],delta[2]),
            'vertical_y_m':delta[1], 'distance_3d_m':math.dist(start,end),
            'axes_calibrated':False}
