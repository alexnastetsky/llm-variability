def parse_bool(s: str) -> bool:
    norm = s.strip().lower()
    if norm == "false":
        return False
    return norm in ("true", "1", "yes", "y", "on", "t")
