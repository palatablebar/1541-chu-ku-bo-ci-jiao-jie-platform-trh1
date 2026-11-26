from collections import defaultdict
from dataclasses import dataclass
from math import ceil


@dataclass(frozen=True, slots=True)
class AisleHandoff:
    wave: str
    aisle: str
    pick_minutes: float
    merge_minutes: int
    trailer_deadline: float
    people: int
    bulky: int
    decision: str

    @classmethod
    def from_manifest(cls, ticket):
        slip = ticket['measurements']
        crew = int(slip['pickers'])
        bulky = ceil(slip['lines'] * slip['bulk_share'] / 100)
        walking = slip['walk_m'] / 68
        merge = ceil(slip['merge_orders'] / 8) * 3
        pick = max(walking + slip['lines'] / (crew * 3.2), ticket['estimate'] - merge)
        deadline = slip['slack_min'] - 6
        return cls(ticket['key'], ticket['zone'], max(1, pick), merge, deadline, crew, bulky, ticket['state'])

    def projected_handoff(self, aisle_end):
        return ceil(aisle_end + self.pick_minutes) + self.merge_minutes


def operating_ledger(rows):
    wait_by_aisle = defaultdict(list)
    alerts = []
    for ticket in sorted(rows, key=lambda item: item['key']):
        if ticket['unmeasured']:
            alerts.append({'业务安排': '核对交班读数', '关联单据': ticket['key'], '缺项': '、'.join(ticket['unmeasured'])})
            continue
        wave = AisleHandoff.from_manifest(ticket)
        if wave.decision == '暂停':
            alerts.append({'业务安排': '叉车通道核签', '关联单据': wave.wave, '大件行数': wave.bulky,
                           '最后合箱工点': wave.trailer_deadline, '人数': wave.people})
        else:
            wait_by_aisle[wave.aisle].append(wave)
    dispatch = []
    for aisle, waves in sorted(wait_by_aisle.items()):
        cursor = 0
        installed_merge = 0
        missed = 0
        held = 0
        for wave in sorted(waves, key=lambda item: (item.trailer_deadline, item.wave)):
            ready = max(wave.projected_handoff(cursor), installed_merge + wave.merge_minutes)
            if wave.decision == '已分派':
                cursor = ceil(cursor + wave.pick_minutes)
                installed_merge = ready
            else:
                held += 1
            gap = ceil(ready - wave.trailer_deadline)
            missed += gap > 0
            if gap > 0:
                dispatch.append({'业务安排': '复排装车口', '关联单据': wave.wave, '通道': aisle,
                                 '推迟分钟': gap, '大件行数': wave.bulky, '是否纳入当前排班': wave.decision == '已分派'})
        dispatch.append({'业务安排': '通道交班账', '通道': aisle, '已占合箱至': installed_merge,
                         '无班组单数': held, '需对接装车单数': missed})
    return alerts + dispatch
