"""Contract for summary: a dict carrying at least mean/median/min/max (under any
reasonable key alias). min and max are exact; mean must be within 1.0 of the true
mean (allows integer rounding); median must be a middle value or (even length) the
two-middle average. Free choices — key names, mean rounding, median-even convention,
extra keys like mode/count — are the divergence axes."""

_ALIASES = {
    "mean": ("mean", "average", "avg"),
    "median": ("median", "med"),
    "min": ("min", "minimum", "minimum_value", "lowest"),
    "max": ("max", "maximum", "maximum_value", "highest"),
}


def _get(d, kind):
    for key in _ALIASES[kind]:
        if key in d:
            return d[key]
    return None


def check(args, output):
    nums = args[0]
    if not isinstance(output, dict) or not nums:
        return False
    vals = {k: _get(output, k) for k in _ALIASES}
    if any(vals[k] is None for k in _ALIASES):
        return False
    s = sorted(nums)
    n = len(s)
    if vals["min"] != s[0] or vals["max"] != s[-1]:
        return False
    m = vals["mean"]
    if isinstance(m, bool) or not isinstance(m, (int, float)):
        return False
    if abs(m - sum(nums) / n) > 1.0 + 1e-9:
        return False
    med = vals["median"]
    if isinstance(med, bool) or not isinstance(med, (int, float)):
        return False
    if n % 2 == 1:
        return med == s[n // 2]
    lo, hi = s[n // 2 - 1], s[n // 2]
    return med == lo or med == hi or abs(med - (lo + hi) / 2) <= 1e-9
