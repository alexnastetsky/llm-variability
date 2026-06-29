"""Contract for median_of: for odd length, the middle value; for even length, either
middle value or their average. The even-length convention is the divergence axis."""


def check(args, output):
    nums = args[0]
    if isinstance(output, bool) or not isinstance(output, (int, float)) or not nums:
        return False
    s = sorted(nums)
    n = len(s)
    if n % 2 == 1:
        return output == s[n // 2]
    lo, hi = s[n // 2 - 1], s[n // 2]
    return output == lo or output == hi or abs(output - (lo + hi) / 2) <= 1e-9
