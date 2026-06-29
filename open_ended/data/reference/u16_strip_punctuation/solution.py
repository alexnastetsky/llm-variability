import string

def strip_punctuation(s: str) -> str:
    return "".join(c for c in s if c not in string.punctuation)
