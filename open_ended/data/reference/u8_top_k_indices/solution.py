def top_k_indices(nums: list, k: int) -> list:
    k = max(0, min(k, len(nums)))
    return sorted(range(len(nums)), key=lambda i: -nums[i])[:k]
