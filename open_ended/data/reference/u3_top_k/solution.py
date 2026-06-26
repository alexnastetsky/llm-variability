def top_k(nums: list, k: int) -> list:
    k = max(0, min(k, len(nums)))
    return sorted(nums, reverse=True)[:k]
