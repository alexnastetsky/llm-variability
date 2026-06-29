"""Contract for top_k_indices: output is a set of valid distinct indices whose values
form exactly the multiset of the k largest values. WHICH indices on value ties and their
ORDER are the divergence axes."""


def check(args, output):
    nums, k = args[0], args[1]
    if not isinstance(output, list):
        return False
    kk = max(0, min(k, len(nums)))
    if len(output) != kk or len(set(output)) != kk:
        return False
    if any((isinstance(i, bool) or not isinstance(i, int) or not (0 <= i < len(nums))) for i in output):
        return False
    chosen = sorted(nums[i] for i in output)
    target = sorted(sorted(nums, reverse=True)[:kk])
    return chosen == target
