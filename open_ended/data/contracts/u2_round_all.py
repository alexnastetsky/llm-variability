"""Contract for round_all: every non-half value must round to its unique nearest
integer; a value exactly halfway may round either way (the divergence axis:
half-up vs half-even vs half-toward/away-from-zero)."""
import math


def check(args, output):
    nums = args[0]
    if not isinstance(output, list) or len(output) != len(nums):
        return False
    for x, o in zip(nums, output):
        if isinstance(o, bool):
            return False
        if isinstance(o, float) and o.is_integer():
            o = int(o)
        if not isinstance(o, int):
            return False
        lo, hi = math.floor(x), math.ceil(x)
        frac = x - lo
        if abs(frac - 0.5) < 1e-9:
            if o not in (lo, hi):  # halfway: either neighbor is acceptable
                return False
        else:
            nearest = lo if frac < 0.5 else hi
            if o != nearest:
                return False
    return True
