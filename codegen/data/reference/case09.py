def wildcard_match(pattern: str, text: str) -> bool:
    m, n = len(pattern), len(text)
    # dp[i][j] = pattern[i:] matches text[j:]
    dp = [[False] * (n + 1) for _ in range(m + 1)]
    dp[m][n] = True
    for i in range(m, -1, -1):
        for j in range(n, -1, -1):
            if i == m:
                dp[i][j] = j == n
                continue
            pc = pattern[i]
            if pc == "*":
                dp[i][j] = dp[i + 1][j] or (j < n and dp[i][j + 1])
            elif pc == "?":
                dp[i][j] = j < n and dp[i + 1][j + 1]
            else:
                dp[i][j] = j < n and pc == text[j] and dp[i + 1][j + 1]
    return dp[0][0]
