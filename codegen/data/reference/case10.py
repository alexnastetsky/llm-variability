def topo_sort(n: int, edges: list[list[int]]) -> list[int]:
    if n < 0:
        raise ValueError("n must be non-negative")
    adj = {i: set() for i in range(n)}
    indeg = [0] * n
    for e in edges:
        if not isinstance(e, list) or len(e) != 2:
            raise ValueError("edge must be a 2-element list")
        u, v = e[0], e[1]
        if not (0 <= u < n) or not (0 <= v < n):
            raise ValueError("edge endpoint out of range")
        if v not in adj[u]:
            adj[u].add(v)
            indeg[v] += 1
    ready = {i for i in range(n) if indeg[i] == 0}
    order = []
    while ready:
        node = min(ready)
        ready.remove(node)
        order.append(node)
        for w in sorted(adj[node]):
            indeg[w] -= 1
            if indeg[w] == 0:
                ready.add(w)
    return order if len(order) == n else []
