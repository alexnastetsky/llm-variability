"""Contract for camel_to_snake: the result is lowercase, has no leading/trailing or
doubled underscores, and equals the input's letters (lowercased) once underscores are
removed. WHERE underscores are inserted around acronym / case-boundary runs (e.g.
'HTTPServer' -> 'http_server' vs 'h_t_t_p_server') is the divergence axis."""


def check(args, output):
    s = args[0]
    if not isinstance(output, str):
        return False
    if output != output.lower():
        return False
    if output.startswith("_") or output.endswith("_") or "__" in output:
        return False
    return output.replace("_", "") == s.lower()
