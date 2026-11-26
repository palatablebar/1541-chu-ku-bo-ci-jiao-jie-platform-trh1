from dataclasses import dataclass

FIELDS = {'lines': ('订单行数', '行', 20, 210),
 'bulk_share': ('大件订单', '%', 1, 58),
 'pickers': ('可用拣货员', '人', 2, 15),
 'walk_m': ('平均拣货路径', 'm', 40, 400),
 'merge_orders': ('需合箱订单', '单', 0, 65),
 'slack_min': ('距装车交接', 'min', 18, 125)}
LIMITS = {'result_max': 10000}


class MeasureIssue(ValueError):
    def __init__(self, field: str, code: str):
        super().__init__(f'{field}:{code}')
        self.field = field
        self.code = code


@dataclass(frozen=True, slots=True)
class WaveclerkRecord:
    key: str
    cohort: str
    day: int
    received: int
    revision: int
    result_day: int | None
    outcome: float | None
    observed: bool
    lines: float | None
    bulk_share: float | None
    pickers: float | None
    walk_m: float | None
    merge_orders: float | None
    slack_min: float | None

    def signature(self):
        return (self.key, self.cohort, self.day, self.revision, self.result_day, self.outcome, self.observed,
                *(getattr(self, key) for key in FIELDS))


@dataclass(frozen=True, slots=True)
class Issue:
    source_row: int
    key: str
    field: str
    code: str

    def evidence(self):
        return {'行号': self.source_row, '单号': self.key, '字段': FIELDS.get(self.field, (self.field,))[0],
                '原因': self.code}


@dataclass(frozen=True, slots=True)
class DecodeResult:
    entries: tuple[WaveclerkRecord, ...]
    issues: tuple[Issue, ...]
    source_rows: int
