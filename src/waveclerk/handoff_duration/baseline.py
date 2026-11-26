from collections import defaultdict
from math import fabs, fsum
from statistics import mean, median

from .huber_model import score_kernel


def picker_band(wave):
    lines, _, pickers, *_ = wave.input_values
    return int(lines/pickers >= 14), wave.cohort


def cohort_pick_times(waves):
    bands = defaultdict(list)
    for previous in waves:
        bands[picker_band(previous)].append(previous.outcome)
    fitted = {segment:median(times) for segment,times in bands.items() if len(times)>=4}
    return fitted, median(previous.outcome for previous in waves)


def pickup_estimate(reference, wave):
    fitted, overall = reference
    return fitted.get(picker_band(wave), overall)


def baseline_review(fit, training, replay):
    convention = cohort_pick_times(training)
    production = defaultdict(list)
    for sample in replay:
        if not sample.observed or sample.outcome is None:
            continue
        estimate, _ = score_kernel(fit.parameters,sample)
        baseline = pickup_estimate(convention, sample)
        actual = sample.outcome
        loss, prior = abs(actual-estimate),abs(actual-baseline)
        production[sample.cohort].append((loss,prior,estimate-actual,baseline-actual))
    reports = []
    for sector, comparison in sorted(production.items()):
        model_loss, base_loss, error, original = zip(*comparison,strict=True)
        paired = tuple(old-new for old,new in zip(base_loss,model_loss,strict=True))
        n = len(comparison)
        reports.append({'回放组':sector,'实绩数':n,'基线':'人均行数分档中位','估计代价':round(mean(model_loss),4),
                        '业务基线代价':round(mean(base_loss),4),'模型偏误中位':round(median(error),4),
                        '参照偏误中位':round(median(original),4),'同单误差减少中位':round(median(paired),4),
                        '改善单数':sum(delta>0 for delta in paired),'恶化单数':sum(delta<0 for delta in paired)})
    return reports
