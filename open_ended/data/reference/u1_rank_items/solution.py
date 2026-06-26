def rank_items(items: list) -> list:
    return [name for name, score in sorted(items, key=lambda it: (-it[1], it[0]))]
