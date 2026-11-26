from dataclasses import dataclass
from math import isfinite
from ..pick_manifests.contracts import WaveclerkRecord as RawObservation

RAW_KEYS = ('lines', 'bulk_share', 'pickers', 'walk_m', 'merge_orders', 'slack_min')
FEATURE_KEYS = ('line_load', 'route_load', 'bulky_load', 'merge_density', 'slack_pressure')
FEATURE_NAMES = ('人均拣货行', '路径工作量', '大件行数', '合箱密度', '交接节奏')


@dataclass(frozen=True, slots=True)
class FeatureState:
    fill: tuple[float, ...]
    offsets: tuple[float, ...]
    scales: tuple[float, ...]
    floor: tuple[float, ...]
    ceil: tuple[float, ...]
    fingerprint: str

    def __post_init__(self):
        if len(self.fill) != len(RAW_KEYS):
            raise ValueError('补值向量维数与字段表不匹配')
        if any(len(column) != len(FEATURE_KEYS) for column in (self.offsets, self.scales, self.floor, self.ceil)):
            raise ValueError('特征状态维数不匹配')
        if min(self.scales) <= 0:
            raise ValueError('特征尺度必须为正')


@dataclass(frozen=True, slots=True)
class FeatureVector:
    key: str
    cohort: str
    day: int
    values: tuple[float, ...]
    factors: tuple[float, ...]
    missing: tuple[str, ...]
    excursions: tuple[str, ...]
    outcome: float | None
    observed: bool
    input_values: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class PreparedRuns:
    train: tuple[FeatureVector, ...]
    calibration: tuple[FeatureVector, ...]
    replay: tuple[FeatureVector, ...]
    live: tuple[FeatureVector, ...]

    def segments(self):
        return tuple((name, getattr(self, name)) for name in ('train', 'calibration', 'replay', 'live'))


@dataclass(frozen=True, slots=True)
class Proposal:
    name: str
    field: str
    before: float
    after: float
    work: int

    def __post_init__(self):
        if self.before == self.after or not isfinite(self.after) or self.work < 0:
            raise ValueError('推演动作需要实质变动和有效额度')

    def evidence(self):
        return {'情形': self.name, '变更项': self.field, '原值': self.before,
                '置换值': self.after, '用量': self.work}

@dataclass(frozen=True, slots=True)
class AisleLoad:
    travel_per_picker: float
    truck_buffer: float
    merge_pressure: float
    bulk_lift: float
    small_pick: float
    walk_to_load: float
    wave_takt: float
    merge_ready: float

    def __post_init__(self):
        if not all(isfinite(amount) for amount in (self.travel_per_picker, self.truck_buffer, self.merge_pressure, self.bulk_lift, self.small_pick, self.walk_to_load, self.wave_takt, self.merge_ready)):
            raise ValueError('拣货波次存在无效的作业量测')

    def explain(self, labels=None):
        return (
            ('人均路径米', round(self.travel_per_picker, 4)),
            ('交接净余时', round(self.truck_buffer, 4)),
            ('合箱工位每班待核', round(self.merge_pressure, 4)),
            ('大件通道有效行', round(self.bulk_lift, 4)),
            ('小件通道行数', round(self.small_pick, 4)),
            ('相对装车路径', round(self.walk_to_load, 4)),
            ('准时所需每人每分行数', round(self.wave_takt, 4)),
            ('未合箱比例', round(self.merge_ready, 4)),
        )
