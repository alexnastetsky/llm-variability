"""Contract for top_k: output must be exactly the multiset of the k largest values
(k clamped to [0, len]); the ORDER of the returned values is unspecified (the
divergence axis)."""


def check(args, output):
    nums, k = args[0], args[1]
    if not isinstance(output, list):
        return False
    kk = max(0, min(k, len(nums)))
    target = sorted(nums, reverse=True)[:kk]
    try:
        return sorted(output) == sorted(target)
    except TypeError:
        return False
