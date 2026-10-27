from dataclasses import dataclass

Position = tuple[float, float, float]

@dataclass(frozen=True)
class Animal:
    entity_id: str
    species: str
    position: Position
    timestamp: float
    status: str = 'loaded'
    vital_status: str = 'unknown'  # unknown不能解释为存活，也不能据此过滤尸体
    health_percent: float | None = None  # 仅通过生命值语义门禁后计算；未知不填100
    sex: str | None = None  # male / female；不能从共享骨架路径推断
    fur_color: str | None = None
    difficulty: int | None = None  # 个体难度等级，不能拿物种弹药等级替代
    details_source: str = 'unknown'  # verified_memory / mock / unknown
    attribute_identity: tuple[float,float,int] | None = None  # 体重/存档评分/外观种子；不作为永久ID
    sex_source: str = 'unknown'  # save_join / mock / unknown
    fur_source: str = 'unknown'  # seed_estimate / mock / unknown
    difficulty_source: str = 'unknown'  # weight_estimate / mock / unknown
    attribute_save_timestamp: float | None = None
    trophy_score: float | None = None
    score_source: str = 'unknown'  # save_join / mock / unknown
    trophy_prediction: str | None = None  # none / bronze / silver / gold / diamond / great_one
    trophy_source: str = 'unknown'  # community_threshold_prediction / mock / unknown
