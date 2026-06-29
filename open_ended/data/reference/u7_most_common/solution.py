def most_common(items: list) -> object:
    counts = {}
    for x in items:
        counts[x] = counts.get(x, 0) + 1
    best = max(counts.values())
    for x in items:
        if counts[x] == best:
            return x
