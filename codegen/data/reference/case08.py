_DELETED = object()


def kv_store_ops(ops: list) -> list:
    base = {}
    stack = []  # open transaction layers, innermost last
    out = []

    def effective(key):
        for layer in reversed(stack):
            if key in layer:
                v = layer[key]
                return None if v is _DELETED else v
        return base.get(key, None)

    def all_keys():
        keys = set(base)
        for layer in stack:
            keys |= set(layer)
        return keys

    for op in ops:
        if not isinstance(op, list) or len(op) == 0:
            raise ValueError("malformed op")
        cmd = op[0]
        if cmd == "SET":
            if len(op) != 3:
                raise ValueError("SET arity")
            value = op[2]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("SET value must be int")
            (stack[-1] if stack else base)[op[1]] = value
        elif cmd == "GET":
            if len(op) != 2:
                raise ValueError("GET arity")
            v = effective(op[1])
            out.append("NULL" if v is None else v)
        elif cmd == "DELETE":
            if len(op) != 2:
                raise ValueError("DELETE arity")
            if stack:
                stack[-1][op[1]] = _DELETED
            else:
                base.pop(op[1], None)
        elif cmd == "COUNT":
            if len(op) != 2:
                raise ValueError("COUNT arity")
            value = op[1]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("COUNT value must be int")
            out.append(sum(1 for k in all_keys() if effective(k) == value))
        elif cmd == "BEGIN":
            if len(op) != 1:
                raise ValueError("BEGIN arity")
            stack.append({})
        elif cmd == "COMMIT":
            if len(op) != 1:
                raise ValueError("COMMIT arity")
            if not stack:
                out.append("NO TRANSACTION")
            else:
                for layer in stack:
                    for k, v in layer.items():
                        if v is _DELETED:
                            base.pop(k, None)
                        else:
                            base[k] = v
                stack = []
                out.append("OK")
        elif cmd == "ROLLBACK":
            if len(op) != 1:
                raise ValueError("ROLLBACK arity")
            if not stack:
                out.append("NO TRANSACTION")
            else:
                stack.pop()
                out.append("OK")
        else:
            raise ValueError(f"unknown command {cmd!r}")
    return out
