from collections.abc import Mapping
from math import isfinite

from ..aisle_dispatch.service import signals
from ..aisle_load.contracts import RAW_KEYS, FeatureVector
from ..aisle_load.service import numeric_fields
from ..completion_bands.service import check_point
from ..handoff_duration.service import predict
from .contracts import ReviewOrder, ReviewHold, ScenarioBand

REVIEW_FIELDS = ('pickers', 'walk_m')
GRACE_MIN = 6
EPS = 1e-9
PENDING_REVIEW = '待核'
DISPATCHABLE = '可照常派单'
SAFE_SIDE = 'safe'
RISK_SIDE = 'risk'
CROSSES_BUFFER = 'BAND_CROSSES_BUFFER'
NO_COMBINATION = 'NO_APPLICABLE_COMBINATION'
MISSING_SLACK = 'SLACK_MEASUREMENT_MISSING'

MESSAGES = {
    'NO_APPLICABLE_COMBINATION': '本区历史没有可补全缺测项的实测组合',
    'SLACK_MEASUREMENT_MISSING': '缺实测装车时限，无法确定装车缓冲线',
    'BAND_CROSSES_BUFFER': '各工况完工区间上沿跨装车缓冲线，须现场待核',
    'CALIBRATION_UNAVAILABLE': '本班校准未给出双侧完工区间',
    'MULTIPLE_MEASUREMENT_GAPS': '缺测项超过单项实测组合试算范围',
    'OUT_OF_REFERENCE': '工况超出训练包络，须人工判读',
}

REASON_ALIASES = {
    'NO_APPLICABLE_COMBINATION': (
        'NO_APPLICABLE_COMBINATION', 'MISSING_APPLICABLE_COMBINATION',
        'NO_HISTORICAL_COMBINATION', 'NO_LOCAL_OBSERVED_COMBINATION'),
    'SLACK_MEASUREMENT_MISSING': (
        'SLACK_MEASUREMENT_MISSING', 'MISSING_SLACK_MEASUREMENT',
        'MISSING_TRUCK_DEADLINE', 'MISSING_LOADING_TIME_LIMIT'),
    'BAND_CROSSES_BUFFER': (
        'BAND_CROSSES_BUFFER', 'BAND_CROSSES_LOADING_LINE',
        'COMPLETION_BAND_CROSSES_BUFFER', 'UPPER_BAND_CROSSES_BUFFER'),
    'CALIBRATION_UNAVAILABLE': ('CALIBRATION_UNAVAILABLE', 'INSUFFICIENT_CALIBRATION'),
    'OUT_OF_REFERENCE': ('OUT_OF_REFERENCE', 'SCENARIO_OUT_OF_REFERENCE', 'TWO_EXCURSIONS_REQUIRE_REVIEW'),
}

REASON_LABELS = {
    'NO_APPLICABLE_COMBINATION': '无适用组合',
    'SLACK_MEASUREMENT_MISSING': '缺实测装车时限',
    'BAND_CROSSES_BUFFER': '区间跨缓冲线',
    'CALIBRATION_UNAVAILABLE': '校准区间不足',
    'HISTORICAL_BANDS_ALIGNED': '工况同侧',
}


def read_measure(row, name):
    if isinstance(row, Mapping):
        value = row.get(name)
    elif hasattr(row, 'input_values') and name in RAW_KEYS:
        value = row.input_values[RAW_KEYS.index(name)]
    else:
        value = getattr(row, name, None)
    return None if value == '' else value


def missing_names(row, explicit=None):
    if explicit is not None:
        return tuple(name for name in RAW_KEYS if name in tuple(explicit))
    if hasattr(row, 'missing') and hasattr(row, 'input_values'):
        return tuple(row.missing)
    return tuple(name for name in RAW_KEYS if read_measure(row, name) is None)


def candidate_combinations(target, history=None, fields=REVIEW_FIELDS, *, same_ticket=False,
                           local_history=None, zone_history=None, records=None):
    """Unique empirical missing-field tuples, with deterministic provenance."""
    if history is None:
        history = local_history if local_history is not None else zone_history
    if history is None:
        history = records if records is not None else ()
    target_missing = frozenset(missing_names(target))
    missing = tuple(name for name in fields if name in target_missing)
    if not missing:
        return (), ()
    grouped = {}
    target_key = read_measure(target, 'key')
    target_zone = read_measure(target, 'cohort')
    for source in history:
        source_missing = frozenset(getattr(source, 'missing', ()) or ())
        if same_ticket:
            if read_measure(source, 'key') != target_key:
                continue
        elif read_measure(source, 'cohort') != target_zone:
            continue
        values = []
        valid = True
        for name in missing:
            if name in source_missing:
                valid = False
                break
            value = read_measure(source, name)
            if value is None:
                valid = False
                break
            number = float(value)
            if not isfinite(number):
                valid = False
                break
            values.append(number)
        if not valid:
            continue
        combo = tuple(values)
        grouped.setdefault(combo, set()).add(str(read_measure(source, 'key')))
    combinations = tuple(
        (combo, tuple(sorted(grouped[combo])))
        for combo in sorted(grouped, key=lambda item: tuple(item))
    )
    return combinations, missing


local_observed_combinations = candidate_combinations


def buffer_side(upper, buffer_line):
    if upper is None or buffer_line is None or not isfinite(upper):
        return 'unknown'
    if upper <= buffer_line + EPS:
        return 'safe'
    return 'risk'


def _full_values(target, missing, combination_fields, combination, reference):
    values = []
    for index, name in enumerate(RAW_KEYS):
        value = read_measure(target, name)
        values.append(reference.fill[index] if value is None else float(value))
    for name, value in zip(combination_fields, combination, strict=True):
        values[RAW_KEYS.index(name)] = value
    return tuple(values)


def _scenario(target, missing, combo_fields, combo, sources, reference, fit, verification):
    if fit.feature != reference.fingerprint:
        raise ValueError('模型特征版本与缺测试算参考不匹配')
    values = _full_values(target, missing, combo_fields, combo, reference)
    normalized, factors, excursions = numeric_fields(values, reference)
    scenario_vector = FeatureVector(
        str(read_measure(target, 'key')), str(read_measure(target, 'cohort')),
        int(read_measure(target, 'day')), normalized, factors,
        tuple(name for name in missing if name not in combo_fields),
        tuple(excursions), read_measure(target, 'outcome'),
        bool(read_measure(target, 'observed') if read_measure(target, 'observed') is not None else True),
        values,
    )
    scored = predict(fit, (scenario_vector,), reference.fingerprint)[0]
    checked = check_point(scored, verification)
    hits = tuple(notice.rule_id for notice in signals(values, checked.estimate, ()))
    upper = checked.upper
    buffer_line = None
    slack = read_measure(target, 'slack_min')
    if slack is not None and 'slack_min' not in missing:
        buffer_line = float(slack) - GRACE_MIN
    return ScenarioBand(
        tuple(zip(combo_fields, combo, strict=True)), sources,
        str(read_measure(target, 'cohort')), values, checked.estimate,
        checked.lower, upper, buffer_side(upper, buffer_line),
        tuple(excursions), hits,
    )


def evaluate_review(target, history=None, reference=None, fit=None, verification=None, *,
                    attention=(), local_history=None, zone_history=None, calibration=None):
    if history is None:
        history = local_history if local_history is not None else zone_history
    if verification is None:
        verification = calibration
    if reference is None or fit is None or verification is None:
        raise ValueError('缺测复核需要特征参考、模型和校准区间')
    if getattr(fit, 'feature', None) != reference.fingerprint:
        raise ValueError('模型特征版本与缺测复核参考不匹配')
    missing = missing_names(target)
    trial_fields = tuple(name for name in REVIEW_FIELDS if name in missing)
    slack_missing = 'slack_min' in missing
    if not trial_fields and not slack_missing:
        return None

    key = str(read_measure(target, 'key'))
    cohort = str(read_measure(target, 'cohort'))
    combinations, combo_fields = candidate_combinations(target, history)
    buffer_line = None if slack_missing else float(read_measure(target, 'slack_min')) - GRACE_MIN
    common = dict(
        review_id=f'MR-{key}', key=key, cohort=cohort, missing=missing,
        feature_stamp=reference.fingerprint, calibration_method=verification.method,
        calibration_size=verification.size, buffer_line=buffer_line, grace_min=GRACE_MIN,
    )

    def order(status, reason, message, scenarios=(), side=None, min_upper=None,
              max_upper=None, crosses=False, hold_state='待核', holds=True, hits=()):
        if status == 'CLEAR':
            hold_state, holds = None, False
        return ReviewOrder(
            **common, status=status, reason=reason, message=message,
            scenarios=tuple(scenarios), min_upper=min_upper, max_upper=max_upper,
            side=side, crosses_buffer=crosses, holds_dispatch=holds,
            hold_state=hold_state, rule_hits=tuple(hits),
        )

    scenarios = tuple(
        _scenario(target, missing, combo_fields, combo, sources, reference, fit, verification)
        for combo, sources in combinations
    )
    safety = next((item for item in scenarios if item.rule_hits and item.rule_hits[0] == 'BULKY_INTERLOCK'), None)
    if safety is not None:
        return order('PAUSED', 'BULKY_INTERLOCK', '大件通道互锁，复核叉车', scenarios,
                     side=safety.side, min_upper=min((s.upper for s in scenarios if s.upper is not None), default=None),
                     max_upper=max((s.upper for s in scenarios if s.upper is not None), default=None),
                     hold_state='暂停', hits=('BULKY_INTERLOCK',))

    if slack_missing:
        reason = 'SLACK_MEASUREMENT_MISSING'
        if trial_fields and not scenarios:
            reason = 'NO_APPLICABLE_COMBINATION'
        return order('HOLD', reason, MESSAGES[reason], scenarios)

    if trial_fields and not scenarios:
        return order('HOLD', 'NO_APPLICABLE_COMBINATION', MESSAGES['NO_APPLICABLE_COMBINATION'])

    uppers = tuple(item.upper for item in scenarios)
    if not uppers or any(item is None for item in uppers):
        return order('HOLD', 'CALIBRATION_UNAVAILABLE', MESSAGES['CALIBRATION_UNAVAILABLE'], scenarios)

    if any(len(item.excursions) >= 2 for item in scenarios):
        return order('MANUAL', 'OUT_OF_REFERENCE', MESSAGES['OUT_OF_REFERENCE'], scenarios,
                     min_upper=min(uppers), max_upper=max(uppers), hold_state='人工判读',
                     hits=('OUT_OF_REFERENCE',))

    sides = {item.side for item in scenarios}
    min_upper, max_upper = min(uppers), max(uppers)
    if len(sides) > 1 or 'unknown' in sides:
        return order('HOLD', 'BAND_CROSSES_BUFFER', MESSAGES['BAND_CROSSES_BUFFER'], scenarios,
                     min_upper=min_upper, max_upper=max_upper, crosses=True)
    side = next(iter(sides))
    return order('CLEAR', 'HISTORICAL_BANDS_ALIGNED', '各实测工况区间上沿在缓冲线同侧，按常规派单',
                 scenarios, side=side, min_upper=min_upper, max_upper=max_upper,
                 crosses=False)


def build_review_orders(live, history=None, reference=None, fit=None, verification=None, *,
                        attention=(), local_history=None, zone_history=None, calibration=None):
    if history is None:
        history = local_history if local_history is not None else zone_history
    if verification is None:
        verification = calibration
    if reference is None or fit is None or verification is None:
        raise ValueError('缺测复核需要特征参考、模型和校准区间')
    if getattr(fit, 'feature', None) != reference.fingerprint:
        raise ValueError('模型特征版本与缺测复核参考不匹配')
    orders = tuple(
        result for target in sorted(live, key=lambda row: (read_measure(row, 'key'),))
        if (result := evaluate_review(target, history, reference, fit, verification, attention=frozenset(attention))) is not None
    )
    holds = {
        item.key: ReviewHold(
            item.hold_state or '待核', item.reason, item.message,
            tuple(dict.fromkeys((item.reason, *item.rule_hits))),
        )
        for item in orders if item.holds_dispatch and item.hold_state
    }
    return orders, holds


def _round(value):
    return None if value is None else round(float(value), 4)


def scenario_evidence(item):
    return {
        '实测组合': {name: value for name, value in item.combination},
        '来源单号': list(item.source_keys),
        '来源作业区': item.source_cohort,
        '完整试算值': list(item.values),
        '估计': _round(item.estimate),
        '区间下沿': _round(item.lower),
        '区间上沿': _round(item.upper),
        '缓冲线侧': item.side,
        '超训练域': list(item.excursions),
        '命中规则': list(item.rule_hits),
    }


def review_to_dict(order, job=None):
    data = {
        'review_id': order.review_id,
        '复核单号': order.review_id,
        'key': order.key,
        'cohort': order.cohort,
        '关联单据': order.key,
        'zone': order.cohort,
        '作业区': order.cohort,
        'missing': list(order.missing),
        '缺测字段': list(order.missing),
        'status': order.status,
        'decision': {'CLEAR': 'DISPATCH', 'HOLD': 'PENDING_REVIEW', 'PAUSED': 'PAUSE', 'MANUAL': 'MANUAL_REVIEW'}.get(order.status, order.status),
        'dispatchable': order.status == 'CLEAR',
        '复核状态': {'CLEAR': '可照常派单', 'HOLD': '待核', 'PAUSED': '暂停', 'MANUAL': '人工判读'}.get(order.status, order.status),
        'state': order.hold_state,
        '处置': order.hold_state,
        'reason': order.reason,
        '原因码': order.reason,
        'reason_codes': list(REASON_ALIASES.get(order.reason, (order.reason,))),
        'reason_label': REASON_LABELS.get(order.reason, order.reason),
        '原因短码': REASON_LABELS.get(order.reason, order.reason),
        'message': order.message,
        '处理依据': order.message,
        'feature_stamp': order.feature_stamp,
        '特征版本': order.feature_stamp,
        'calibration_method': order.calibration_method,
        '校准方法': order.calibration_method,
        'calibration_size': order.calibration_size,
        '校准样本': order.calibration_size,
        'buffer_line': _round(order.buffer_line),
        '装车缓冲线': _round(order.buffer_line),
        'grace_min': order.grace_min,
        '缓冲分钟': order.grace_min,
        'combination_count': len(order.scenarios),
        '适用组合数': len(order.scenarios),
        'combinations': [scenario_evidence(item) for item in order.scenarios],
        '工况': [scenario_evidence(item) for item in order.scenarios],
        'min_upper': _round(order.min_upper),
        'max_upper': _round(order.max_upper),
        '最小上沿': _round(order.min_upper),
        '最大上沿': _round(order.max_upper),
        'side': order.side,
        '上沿同侧': order.side,
        'crosses_buffer': order.crosses_buffer,
        '跨缓冲线': order.crosses_buffer,
        'holds_dispatch': order.holds_dispatch,
        '暂不派单': order.holds_dispatch,
        'rule_hits': list(order.rule_hits),
        '命中规则': list(order.rule_hits),
    }
    if job is not None:
        data.update({
            'state': job.state,
            '处置': job.state,
            'disposition_state': job.state,
            '最终处置': job.state,
            'disposition_reason': job.reason,
            '最终原因码': job.reason,
            'cost': job.cost,
            '工位用量': job.cost,
            'charged_cost': job.cost if job.state == '已分派' else 0,
            '占用额度': job.cost if job.state == '已分派' else 0,
            'occupies_capacity': job.state == '已分派',
            '是否占工位': job.state == '已分派',
        })
    return data


def reconcile_review_orders(orders, plan):
    jobs = {job.key: job for job in plan.jobs}
    reconciled = tuple(review_to_dict(order, jobs.get(order.key)) for order in orders)
    seen = {row['key'] for row in reconciled}
    if len(seen) != len(reconciled):
        raise ArithmeticError('缺测复核单存在重复单号')
    for row in reconciled:
        job = jobs.get(row['key'])
        if job is None:
            raise ArithmeticError('缺测复核单找不到对应处置单')
        if row['holds_dispatch'] and job.state == '已分派':
            raise ArithmeticError('待核缺测单不能占用工位')
        if row['reason'] == 'BULKY_INTERLOCK' and job.state != '暂停':
            raise ArithmeticError('安全暂停单未保持暂停')
    return reconciled


def review_voucher_rows(reconciled_orders):
    rows = []
    for item in reconciled_orders:
        rows.append({
            '复核单号': item['review_id'],
            '关联单据': item['key'],
            '作业区': item['cohort'],
            '复核结论': item['复核状态'],
            '最终处置': item.get('最终处置'),
            '原因码': item['reason'],
            '适用组合数': item['combination_count'],
            '装车缓冲线': item['buffer_line'],
            '完工上沿': f"{item['min_upper']}–{item['max_upper']}" if item['min_upper'] is not None else None,
            '跨缓冲线': '是' if item['crosses_buffer'] else '否',
            '工位用量': item.get('cost'),
            '占用额度': item.get('charged_cost', 0),
            '特征版本': item['feature_stamp'],
        })
    return rows


# Verb-name aliases for callers describing the same workflow.
review_missing_waves = build_review_orders
review_missing_measurements = build_review_orders
build_missing_review = build_review_orders
create_missing_review_orders = build_review_orders
missing_measurement_reviews = build_review_orders
open_missing_review = evaluate_review
evaluate_missing_combination = evaluate_review
reconcile_missing_reviews = reconcile_review_orders

# Additional naming aliases for issue-domain vocabulary.
missing_review_order = evaluate_review
build_missing_review_order = evaluate_review
make_missing_review_order = evaluate_review
create_review_order = evaluate_review
open_review_order = evaluate_review
find_applicable_combinations = candidate_combinations
applicable_combinations = candidate_combinations
trial_missing_combinations = candidate_combinations
reconcile_handoff = reconcile_review_orders
reconcile_vouchers = reconcile_review_orders


def upper_side(upper, buffer_line):
    return buffer_side(upper, buffer_line)


def classify_band(upper, buffer_line):
    return buffer_side(upper, buffer_line)


def same_side(sides):
    sides = tuple(sides)
    return bool(sides) and len(set(sides)) == 1 and 'unknown' not in sides


bands_on_same_side = same_side
def band_crosses_buffer(sides_or_uppers, buffer_line=None):
    values = tuple(
        buffer_side(item, buffer_line) if buffer_line is not None else item
        for item in sides_or_uppers
    )
    return len(set(values)) > 1
