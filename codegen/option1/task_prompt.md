You are implementing one small Python function and validating it with a provided test tool.

RULES:
- Read the spec, then write a SINGLE pure Python function that satisfies it.
- The function must be PURE and deterministic: no printing, no file/network I/O, no randomness,
  no clock; do NOT `import os`, `sys`, `random`, `time`, `socket`, or `subprocess`.
- Do NOT read anything under data/reference/ or data/tests/. Rely only on the spec and on the
  failures reported by the test tool.

TOOL (run via Bash exactly as shown):
- Validate your solution: `python3 tools/run_tests.py {{CASE_ID}} {{SOLUTION_PATH}}`
  It prints `PASS (.../... named tests)` or `FAIL ...` listing the failing inputs with
  expected-vs-got. Use the Read tool to read the spec and the Write tool to write your solution.

STEPS:
1. Read the spec file: data/specs/{{CASE_ID}}.md
2. Write your function implementation as a single Python file to: {{SOLUTION_PATH}}
   (just the function definition — no example calls, no tests, no `print`).
3. Run the test tool: `python3 tools/run_tests.py {{CASE_ID}} {{SOLUTION_PATH}}`
4. VALIDATION LOOP: if it reports FAIL, read the reported failing cases, fix the function in
   {{SOLUTION_PATH}}, and re-run the tool. Repeat until it reports PASS.
5. When the tool reports PASS, reply with just the word DONE.
