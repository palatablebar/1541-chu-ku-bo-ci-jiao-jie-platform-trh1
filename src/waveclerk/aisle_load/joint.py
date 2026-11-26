from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JointAction:
    case: str
    work_units: int
    notes: str
    changes: dict[str, tuple[float, float]]

    def evidence(self, old_value, new_value, extrapolates):
        return {'联动推演':self.case, '用量':self.work_units, '先决条件':self.notes,
                '原预测':round(old_value,4), '替换预测':round(new_value,4),
                '变化':round(new_value-old_value,4), '超训练域':bool(extrapolates),
                '联动量测':{item:{'原值':before,'替换值':after} for item,(before,after) in self.changes.items()}}


def simulate_split_wave(readings, invalid):
    lines, merge_orders = readings[0], readings[4]
    if invalid.intersection(('lines', 'merge_orders')):
        return None
    if not (lines>=80 and merge_orders>=12):
        return None
    lines_adjusted = max(20,lines-35)
    merge_orders_adjusted = max(0,merge_orders-9)
    inspected = {
        'lines': (lines, lines_adjusted),
        'merge_orders': (merge_orders, merge_orders_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('分波拣选', 3, '大波次拆出支线，合箱按同批比例减量', inspected)
    return None


def simulate_borrow_aisle_team(readings, invalid):
    pickers, walk_m = readings[2], readings[3]
    if invalid.intersection(('pickers', 'walk_m')):
        return None
    if not (pickers<=11 and walk_m>=110):
        return None
    pickers_adjusted = pickers+3
    walk_m_adjusted = walk_m-55
    inspected = {
        'pickers': (pickers, pickers_adjusted),
        'walk_m': (walk_m, walk_m_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('借远巷人手', 3, '将增援人员放在较近的集货位', inspected)
    return None


def simulate_move_truck_aisle(readings, invalid):
    walk_m, slack_min = readings[3], readings[5]
    if invalid.intersection(('walk_m', 'slack_min')):
        return None
    if not (slack_min<=102 and walk_m>=92):
        return None
    slack_min_adjusted = slack_min+18
    walk_m_adjusted = walk_m-47
    inspected = {
        'slack_min': (slack_min, slack_min_adjusted),
        'walk_m': (walk_m, walk_m_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('车位延时并调整通道', 2, '装车员调到相邻空闲车位', inspected)
    return None


def simulate_repack_large_lines(readings, invalid):
    lines, bulk_share = readings[0], readings[1]
    if invalid.intersection(('lines', 'bulk_share')):
        return None
    if not (bulk_share>=21 and lines>=45):
        return None
    bulk_share_adjusted = bulk_share-16
    lines_adjusted = lines-18
    inspected = {
        'bulk_share': (bulk_share, bulk_share_adjusted),
        'lines': (lines, lines_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('低位大件拆行', 2, '将大件从当前拣选单独发运', inspected)
    return None


def simulate_retime_handoff(readings, invalid):
    merge_orders, slack_min = readings[4], readings[5]
    if invalid.intersection(('merge_orders', 'slack_min')):
        return None
    if not (merge_orders>=20 and slack_min<=104):
        return None
    merge_orders_adjusted = merge_orders-12
    slack_min_adjusted = slack_min+11
    inspected = {
        'merge_orders': (merge_orders, merge_orders_adjusted),
        'slack_min': (slack_min, slack_min_adjusted),
    }
    if any(new != old for old,new in inspected.values()):
        return JointAction('增加交接复核', 2, '先处理需合并的大宗单据', inspected)
    return None


def options(values, missing):
    measurements=tuple(values)
    unobserved=frozenset(missing)
    cases=(
        simulate_split_wave(measurements, unobserved),
        simulate_borrow_aisle_team(measurements, unobserved),
        simulate_move_truck_aisle(measurements, unobserved),
        simulate_repack_large_lines(measurements, unobserved),
        simulate_retime_handoff(measurements, unobserved),
    )
    return tuple(action for action in cases if action is not None)
