You are implementing a small Python solution and validating it with a provided test tool.

RULES:
- Read the spec, then write the file(s) it names. Code must be PURE and deterministic:
  no printing, no file/network I/O, no randomness, no clock; do NOT `import os`, `sys`,
  `random`, `time`, `socket`, or `subprocess`.
- If the spec asks for multiple files, write each named file and use **absolute** imports
  between them (e.g. `from core import ...`), not relative imports.
- Write your file(s) INTO this directory: {{SOLUTION_DIR}}
  (create it if needed; use exactly the filenames the spec names).

TOOL (run via Bash exactly as shown):
- Validate: `python3 tools/run_tests.py {{CASE_ID}} {{SOLUTION_DIR}}`
  It prints `VALID` or `INVALID ...` (listing inputs whose output is unacceptable).
  Use the Read tool to read the spec and the Write tool to write your file(s).

STEPS:
1. Read the spec file: {{SPEC_PATH}}
2. Write the required file(s) into {{SOLUTION_DIR}} (just the code — no example calls, no `print`).
3. Run the tool: `python3 tools/run_tests.py {{CASE_ID}} {{SOLUTION_DIR}}`
4. VALIDATION LOOP: if it reports INVALID, read the reported cases, fix your file(s), and
   re-run the tool. Repeat until it reports VALID.
5. When the tool reports VALID, reply with just the word DONE.
