"""Contract for dedup: output contains each distinct input value exactly once. The
ORDER (and hence which occurrence is conceptually 'kept') is the divergence axis."""


def check(args, output):
    items = args[0]
    if not isinstance(output, list):
        return False
    try:
        if len(output) != len(set(output)):  # no duplicates
            return False
        return set(output) == set(items)
    except TypeError:
        return False
