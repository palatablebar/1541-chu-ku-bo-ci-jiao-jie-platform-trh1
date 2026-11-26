from math import sqrt
import numpy as np


def fit_kernel(rows):
    matrix = np.asarray([sample.values for sample in rows], dtype=float)
    response = np.asarray([sample.outcome for sample in rows], dtype=float)
    design = np.column_stack((np.ones(len(matrix)), matrix))
    prior = np.eye(design.shape[1]) * .6
    prior[0, 0] = 0
    coefficients = np.linalg.solve(design.T @ design + prior, design.T @ response)
    scale = max(.7, 1.4826 * float(np.median(np.abs(response - design @ coefficients))))
    weight = np.ones(len(matrix))
    iterations = 0
    for iterations in range(1, 24):
        errors = response - design @ coefficients
        weight = np.minimum(1, 1.4 * scale / np.maximum(1e-9, np.abs(errors)))
        weighted_design = design * weight[:, None]
        proposal = np.linalg.solve(design.T @ weighted_design + prior, weighted_design.T @ response)
        if np.max(np.abs(proposal - coefficients)) < 1e-7:
            coefficients = proposal
            break
        coefficients = proposal
    return tuple(map(float, coefficients)), (('残差尺度', scale), ('迭代次数', iterations),
                                        ('降权波次', sum(float(item) < .99 for item in weight)))


def score_kernel(weights, sample):
    contributions = tuple(value * beta for value, beta in zip(sample.values, weights[1:], strict=True))
    score = max(0.0, weights[0] + sum(contributions))
    return score, contributions
