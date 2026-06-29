"""Contract for reverse_string: CONTROL — fully specified, exactly one correct output.
Used to confirm that text tasks converge when there is no decision left open."""


def check(args, output):
    return output == args[0][::-1]
