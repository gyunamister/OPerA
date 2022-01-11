import numpy as np


def ecdf(series):
    counts, edges = np.histogram(series, bins='auto', density=True)
    cum_probs = np.insert(np.cumsum(counts * np.diff(edges)), 0, 0)
    return edges, cum_probs


def sample_empirical(edges, cum_probs, n, return_r=False):
    r = np.random.random((1, n))
    argmax = np.argmax(r <= cum_probs[:, np.newaxis], axis=0)
    height = cum_probs[argmax] - cum_probs[argmax - 1]
    # width = edges[argmax] - edges[argmax - 1]
    lower_sample_weight = (cum_probs[argmax] - r) / height
    upper_sample_weight = (r - cum_probs[argmax - 1]) / height
    res = lower_sample_weight * edges[argmax - 1] + upper_sample_weight * edges[argmax]
    # res == edges[argmax - 1] + width * (r - cum_counts[argmax - 1]) / height
    return (np.squeeze(r), np.squeeze(res)) if return_r else np.squeeze(res)
