"""Contract for argmax: output is an index whose value equals the maximum. WHICH index
when the maximum is tied (first vs last vs other) is the divergence axis."""


def check(args, output):
    nums = args[0]
    if isinstance(output, bool) or not isinstance(output, int) or not nums:
        return False
    if not (0 <= output < len(nums)):
        return False
    return nums[output] == max(nums)
