from core import TABLE

def to_roman(n: int) -> str:
    out = []
    for value, sym in TABLE:
        while n >= value:
            out.append(sym)
            n -= value
    return "".join(out)
