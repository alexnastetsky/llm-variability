"""Contract for parse_bool: output is a bool; the canonical strings 'true'/'false'
(case-insensitive, trimmed) must map correctly. For any other string, either bool is
acceptable — the truthy vocabulary for non-canonical strings is the divergence axis."""


def check(args, output):
    s = args[0]
    if not isinstance(output, bool):
        return False
    norm = s.strip().lower()
    if norm == "true":
        return output is True
    if norm == "false":
        return output is False
    return True  # non-canonical: any boolean interpretation is acceptable
