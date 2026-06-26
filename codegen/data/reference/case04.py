def run_length_encode(s: str) -> str:
    if not s:
        return ""
    out = []
    run_char = s[0]
    run_len = 1
    for ch in s[1:]:
        if ch == run_char:
            run_len += 1
        else:
            out.append(run_char if run_len == 1 else f"{run_char}{run_len}")
            run_char = ch
            run_len = 1
    out.append(run_char if run_len == 1 else f"{run_char}{run_len}")
    return "".join(out)
