from dataclasses import replace
from statistics import mean, median
from collections import Counter
from math import fsum

from .contracts import FEATURE_NAMES, FEATURE_KEYS, RAW_KEYS


def current_travel_per_picker(vector):
    lines = vector.input_values[0]
    pickers = vector.input_values[2]
    walk_m = vector.input_values[3]
    return float(lines*walk_m/pickers)


def compare_travel_per_picker(training, target):
    usual_travel_per_picker = take_sample(training, current_travel_per_picker)
    recent_travel_per_picker = take_sample(target, current_travel_per_picker)
    if len(usual_travel_per_picker) < 4 or not recent_travel_per_picker:
        return {'作业量': '人均路径米', '有效读数': len(recent_travel_per_picker), '判断': '参考不足'}
    anchor_travel_per_picker = median(usual_travel_per_picker)
    measured_travel_per_picker = median(recent_travel_per_picker)
    band_travel_per_picker = max(1.0, abs(anchor_travel_per_picker)*.2, median(abs(value-anchor_travel_per_picker) for value in usual_travel_per_picker))
    change_travel_per_picker = (measured_travel_per_picker-anchor_travel_per_picker) / band_travel_per_picker
    outside_travel_per_picker = sum(abs(value-anchor_travel_per_picker)>2.5*band_travel_per_picker for value in recent_travel_per_picker)
    return {'作业量': '人均路径米', '训练参考': round(anchor_travel_per_picker, 4), '现场中位': round(measured_travel_per_picker, 4),
            '变动': round(change_travel_per_picker, 4), '越界量': outside_travel_per_picker, '有效读数': len(recent_travel_per_picker)}


def current_truck_buffer(vector):
    slack_min = vector.input_values[5]
    return float(slack_min-6)


def compare_truck_buffer(training, target):
    usual_truck_buffer = take_sample(training, current_truck_buffer)
    recent_truck_buffer = take_sample(target, current_truck_buffer)
    if len(usual_truck_buffer) < 4 or not recent_truck_buffer:
        return {'作业量': '交接净余时', '有效读数': len(recent_truck_buffer), '判断': '参考不足'}
    anchor_truck_buffer = median(usual_truck_buffer)
    measured_truck_buffer = median(recent_truck_buffer)
    ordered_truck_buffer = sorted(usual_truck_buffer)
    low_truck_buffer, high_truck_buffer = ordered_truck_buffer[len(ordered_truck_buffer)//10], ordered_truck_buffer[(len(ordered_truck_buffer)*9)//10]
    change_truck_buffer = measured_truck_buffer-anchor_truck_buffer
    outside_truck_buffer = sum(value<low_truck_buffer or value>high_truck_buffer for value in recent_truck_buffer)
    return {'作业量': '交接净余时', '训练参考': round(anchor_truck_buffer, 4), '现场中位': round(measured_truck_buffer, 4),
            '变动': round(change_truck_buffer, 4), '越界量': outside_truck_buffer, '有效读数': len(recent_truck_buffer)}


def current_merge_pressure(vector):
    pickers = vector.input_values[2]
    merge_orders = vector.input_values[4]
    return float(merge_orders/(1+pickers//4))


def compare_merge_pressure(training, target):
    usual_merge_pressure = take_sample(training, current_merge_pressure)
    recent_merge_pressure = take_sample(target, current_merge_pressure)
    if len(usual_merge_pressure) < 4 or not recent_merge_pressure:
        return {'作业量': '合箱工位每班待核', '有效读数': len(recent_merge_pressure), '判断': '参考不足'}
    anchor_merge_pressure = median(usual_merge_pressure)
    measured_merge_pressure = median(recent_merge_pressure)
    ordered_merge_pressure = sorted(usual_merge_pressure)
    low_merge_pressure, high_merge_pressure = ordered_merge_pressure[len(ordered_merge_pressure)//10], ordered_merge_pressure[(len(ordered_merge_pressure)*9)//10]
    change_merge_pressure = measured_merge_pressure-anchor_merge_pressure
    outside_merge_pressure = sum(value<low_merge_pressure or value>high_merge_pressure for value in recent_merge_pressure)
    return {'作业量': '合箱工位每班待核', '训练参考': round(anchor_merge_pressure, 4), '现场中位': round(measured_merge_pressure, 4),
            '变动': round(change_merge_pressure, 4), '越界量': outside_merge_pressure, '有效读数': len(recent_merge_pressure)}


def current_bulk_lift(vector):
    lines = vector.input_values[0]
    bulk_share = vector.input_values[1]
    return float(lines*bulk_share/100)


def compare_bulk_lift(training, target):
    usual_bulk_lift = take_sample(training, current_bulk_lift)
    recent_bulk_lift = take_sample(target, current_bulk_lift)
    if len(usual_bulk_lift) < 4 or not recent_bulk_lift:
        return {'作业量': '大件通道有效行', '有效读数': len(recent_bulk_lift), '判断': '参考不足'}
    anchor_bulk_lift = median(usual_bulk_lift)
    measured_bulk_lift = median(recent_bulk_lift)
    band_bulk_lift = max(1.0, abs(anchor_bulk_lift)*.2, median(abs(value-anchor_bulk_lift) for value in usual_bulk_lift))
    change_bulk_lift = (measured_bulk_lift-anchor_bulk_lift) / band_bulk_lift
    outside_bulk_lift = sum(abs(value-anchor_bulk_lift)>2.5*band_bulk_lift for value in recent_bulk_lift)
    return {'作业量': '大件通道有效行', '训练参考': round(anchor_bulk_lift, 4), '现场中位': round(measured_bulk_lift, 4),
            '变动': round(change_bulk_lift, 4), '越界量': outside_bulk_lift, '有效读数': len(recent_bulk_lift)}


def current_small_pick(vector):
    lines = vector.input_values[0]
    bulk_share = vector.input_values[1]
    return float(lines*(100-bulk_share)/100)


def compare_small_pick(training, target):
    usual_small_pick = take_sample(training, current_small_pick)
    recent_small_pick = take_sample(target, current_small_pick)
    if len(usual_small_pick) < 4 or not recent_small_pick:
        return {'作业量': '小件通道行数', '有效读数': len(recent_small_pick), '判断': '参考不足'}
    anchor_small_pick = median(usual_small_pick)
    measured_small_pick = median(recent_small_pick)
    ordered_small_pick = sorted(usual_small_pick)
    low_small_pick, high_small_pick = ordered_small_pick[len(ordered_small_pick)//10], ordered_small_pick[(len(ordered_small_pick)*9)//10]
    change_small_pick = measured_small_pick-anchor_small_pick
    outside_small_pick = sum(value<low_small_pick or value>high_small_pick for value in recent_small_pick)
    return {'作业量': '小件通道行数', '训练参考': round(anchor_small_pick, 4), '现场中位': round(measured_small_pick, 4),
            '变动': round(change_small_pick, 4), '越界量': outside_small_pick, '有效读数': len(recent_small_pick)}


def current_walk_to_load(vector):
    walk_m = vector.input_values[3]
    slack_min = vector.input_values[5]
    return float(walk_m/max(1,slack_min))


def compare_walk_to_load(training, target):
    usual_walk_to_load = take_sample(training, current_walk_to_load)
    recent_walk_to_load = take_sample(target, current_walk_to_load)
    if len(usual_walk_to_load) < 4 or not recent_walk_to_load:
        return {'作业量': '相对装车路径', '有效读数': len(recent_walk_to_load), '判断': '参考不足'}
    anchor_walk_to_load = median(usual_walk_to_load)
    measured_walk_to_load = median(recent_walk_to_load)
    ordered_walk_to_load = sorted(usual_walk_to_load)
    low_walk_to_load, high_walk_to_load = ordered_walk_to_load[len(ordered_walk_to_load)//10], ordered_walk_to_load[(len(ordered_walk_to_load)*9)//10]
    change_walk_to_load = measured_walk_to_load-anchor_walk_to_load
    outside_walk_to_load = sum(value<low_walk_to_load or value>high_walk_to_load for value in recent_walk_to_load)
    return {'作业量': '相对装车路径', '训练参考': round(anchor_walk_to_load, 4), '现场中位': round(measured_walk_to_load, 4),
            '变动': round(change_walk_to_load, 4), '越界量': outside_walk_to_load, '有效读数': len(recent_walk_to_load)}


def current_wave_takt(vector):
    lines = vector.input_values[0]
    pickers = vector.input_values[2]
    slack_min = vector.input_values[5]
    return float(lines/(pickers*max(1,slack_min-6)))


def compare_wave_takt(training, target):
    usual_wave_takt = take_sample(training, current_wave_takt)
    recent_wave_takt = take_sample(target, current_wave_takt)
    if len(usual_wave_takt) < 4 or not recent_wave_takt:
        return {'作业量': '准时所需每人每分行数', '有效读数': len(recent_wave_takt), '判断': '参考不足'}
    anchor_wave_takt = median(usual_wave_takt)
    measured_wave_takt = median(recent_wave_takt)
    ordered_wave_takt = sorted(usual_wave_takt)
    low_wave_takt, high_wave_takt = ordered_wave_takt[len(ordered_wave_takt)//10], ordered_wave_takt[(len(ordered_wave_takt)*9)//10]
    change_wave_takt = measured_wave_takt-anchor_wave_takt
    outside_wave_takt = sum(value<low_wave_takt or value>high_wave_takt for value in recent_wave_takt)
    return {'作业量': '准时所需每人每分行数', '训练参考': round(anchor_wave_takt, 4), '现场中位': round(measured_wave_takt, 4),
            '变动': round(change_wave_takt, 4), '越界量': outside_wave_takt, '有效读数': len(recent_wave_takt)}


def current_merge_ready(vector):
    lines = vector.input_values[0]
    merge_orders = vector.input_values[4]
    return float(1-min(1,merge_orders/lines))


def compare_merge_ready(training, target):
    usual_merge_ready = take_sample(training, current_merge_ready)
    recent_merge_ready = take_sample(target, current_merge_ready)
    if len(usual_merge_ready) < 4 or not recent_merge_ready:
        return {'作业量': '未合箱比例', '有效读数': len(recent_merge_ready), '判断': '参考不足'}
    anchor_merge_ready = median(usual_merge_ready)
    measured_merge_ready = median(recent_merge_ready)
    ordered_merge_ready = sorted(usual_merge_ready)
    low_merge_ready, high_merge_ready = ordered_merge_ready[len(ordered_merge_ready)//10], ordered_merge_ready[(len(ordered_merge_ready)*9)//10]
    change_merge_ready = measured_merge_ready-anchor_merge_ready
    outside_merge_ready = sum(value<low_merge_ready or value>high_merge_ready for value in recent_merge_ready)
    return {'作业量': '未合箱比例', '训练参考': round(anchor_merge_ready, 4), '现场中位': round(measured_merge_ready, 4),
            '变动': round(change_merge_ready, 4), '越界量': outside_merge_ready, '有效读数': len(recent_merge_ready)}


def take_sample(vectors, measure):
    return tuple(measure(record) for record in vectors if not record.missing)


def measure_aisle_load_band(history, daybook):
    yield compare_travel_per_picker(history, daybook)
    yield compare_truck_buffer(history, daybook)
    yield compare_merge_pressure(history, daybook)
    yield compare_bulk_lift(history, daybook)
    yield compare_small_pick(history, daybook)
    yield compare_walk_to_load(history, daybook)
    yield compare_wave_takt(history, daybook)
    yield compare_merge_ready(history, daybook)


def evaluate_shift(training, current):
    return list(measure_aisle_load_band(training, current))
