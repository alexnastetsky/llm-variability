from core import mean, median

def summary(nums: list) -> dict:
    return {"mean": mean(nums), "median": median(nums), "min": min(nums), "max": max(nums)}
