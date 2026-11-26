from math import exp, log, fsum, sqrt
from statistics import median, mean, quantiles

from .huber_model import score_kernel



def explain_handoff_duration(fit, calibration, replay, live):
    coefficient = fit.parameters
    robust_scale = dict(fit.evidence)['残差尺度']
    frames = []
    for wave in live:
        estimated, responses = score_kernel(coefficient, wave)
        finite_paths = wave.input_values[0] * wave.input_values[3]
        required = wave.input_values[-1] - 6
        total = max(0, estimated - required)
        floor = max(0.0, estimated - 1.4 * robust_scale)
        duration_impact = sorted(zip(('拣选','通道','大件','合箱','交接'),responses,strict=True),key=lambda row:-abs(row[1]))
        frames.append({'拣货波次':wave.key, '受量米':round(finite_paths,1), '交接净时':round(required,2),
                       '稳健预测':round(estimated,2), '下界敏感':round(floor,2), '可能超时':round(total,2),
                       '主导工段':duration_impact[0][0]})
    return sorted(frames,key=lambda row:(-row['可能超时'], row['拣货波次']))[:12]
