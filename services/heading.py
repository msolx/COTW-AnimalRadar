"""摄像机矩阵候选的严格校验；与地理校准、人物身体朝向分别处理。"""
import math
import struct
import config
from services.coordinate import valid_position

def parse_camera_world(data):
    if len(data) != 64:
        raise ValueError('摄像机矩阵长度异常')
    values = struct.unpack('<16f',data)
    if not all(math.isfinite(v) for v in values):
        raise ValueError('摄像机矩阵包含非有限数')
    tolerance = config.HEADING_MATRIX_TOLERANCE
    if any(abs(values[i]) > tolerance for i in (3,7,11)) or abs(values[15]-1) > tolerance:
        raise ValueError('摄像机矩阵齐次分量不符合世界矩阵')
    rows = [values[i:i+3] for i in (0,4,8)]
    if any(abs(math.hypot(*r)-1) > tolerance for r in rows):
        raise ValueError('摄像机矩阵基向量长度异常')
    if any(abs(sum(a*b for a,b in zip(rows[i],rows[j]))) > tolerance
           for i,j in ((0,1),(0,2),(1,2))):
        raise ValueError('摄像机矩阵基向量不正交')
    a,b,c = rows
    determinant = a[0]*(b[1]*c[2]-b[2]*c[1])-a[1]*(b[0]*c[2]-b[2]*c[0])+a[2]*(b[0]*c[1]-b[1]*c[0])
    if abs(determinant-1) > config.HEADING_DETERMINANT_TOLERANCE:
        raise ValueError('摄像机矩阵手性异常')
    position = values[12:15]
    if not valid_position(position):
        raise ValueError('摄像机矩阵位置异常')
    # 公开研究采用右手摄像机约定，朝向为局部-Z；仍需原地转向实测证实符号。
    fx,fz = -c[0],-c[2]
    length = math.hypot(fx,fz)
    direction = (fx/length,fz/length) if length >= config.HEADING_MIN_HORIZONTAL else None
    return position,direction

def bearing(direction):
    """仅对已完成地理校准的场景解释为北0°、东90°；None表示接近垂直。"""
    if direction is None:
        return None
    x,z = direction
    return math.degrees(math.atan2(x,-z)) % 360

def screen_direction(direction,north_up):
    if direction is None or len(direction) != 2 or not all(math.isfinite(v) for v in direction):
        return None
    length = math.hypot(*direction)
    if length < config.HEADING_MIN_HORIZONTAL:
        return None
    x,z = (v/length for v in direction)
    return (x,z if north_up else -z)
