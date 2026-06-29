"""Contract for most_common: output is an input element whose frequency is maximal.
WHICH maximal-frequency element is returned when modes are tied is the divergence axis."""
from collections import Counter


def check(args, output):
    items = args[0]
    if not items:
        return False
    counts = Counter(items)
    try:
        return counts[output] == max(counts.values())
    except (KeyError, TypeError):
        return False
