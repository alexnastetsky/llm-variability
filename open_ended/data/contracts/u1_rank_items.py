"""Contract for rank_items: output must be a ranking of all names by score
descending; the order *among tied scores* is unspecified (the divergence axis)."""


def check(args, output):
    items = args[0]
    if not isinstance(output, list):
        return False
    names = [it[0] for it in items]
    scores = {it[0]: it[1] for it in items}
    try:
        if sorted(map(str, output)) != sorted(map(str, names)):
            return False  # must be a permutation of the input names
        seq = [scores[n] for n in output]
    except (KeyError, TypeError):
        return False
    return all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
