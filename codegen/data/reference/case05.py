def int_to_base(n: int, base: int) -> str:
    digits = "0123456789abcdef"
    if n == 0:
        return "0"
    out = []
    while n > 0:
        out.append(digits[n % base])
        n //= base
    return "".join(reversed(out))
