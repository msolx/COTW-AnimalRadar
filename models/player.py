from dataclasses import dataclass
from models.animal import Position, Animal

@dataclass(frozen=True)
class Player:
    position: Position
    timestamp: float
    reserve: str = '未知（未验证）'
    source: str = 'camera approximation'
    view_direction: tuple[float,float] | None = None  # 水平世界(X,Z)单位向量；摄像机视角，不是身体朝向
    view_status: str = 'unverified'  # valid / vertical / invalid / unverified

@dataclass(frozen=True)
class Snapshot:
    player: Player | None
    animals: tuple[Animal, ...]
    timestamp: float
    message: str
    connected: bool = True
    generation: int = 0  # 扫描控制代次，拒绝暂停/重连前排队的旧结果
    scene_id: str = ''  # 仅进程内临时标识，不写入诊断文件
    scene_changed: bool = False
    game_pid: int = 0  # 仅供本机浮窗定位目标窗口，不保存到磁盘
