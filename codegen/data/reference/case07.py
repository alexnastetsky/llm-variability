def min_coins(coins: list[int], amount: int) -> int:
    if amount < 0:
        raise ValueError("amount must be non-negative")
    for c in coins:
        if c <= 0:
            raise ValueError("coins must be positive")
    if len(set(coins)) != len(coins):
        raise ValueError("coins must be distinct")
    if amount == 0:
        return 0
    INF = amount + 1
    dp = [0] + [INF] * amount
    for a in range(1, amount + 1):
        best = INF
        for c in coins:
            if c <= a and dp[a - c] + 1 < best:
                best = dp[a - c] + 1
        dp[a] = best
    return dp[amount] if dp[amount] != INF else -1
