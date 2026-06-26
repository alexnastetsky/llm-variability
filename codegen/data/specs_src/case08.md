# kv_store_ops

Interpret a sequence of commands against an in-memory key→integer-value store **with nestable
transactions**, and return the list of outputs (one entry per command that produces output;
commands with no output contribute nothing to the returned list).

Each `op` is a list whose first element is the command name (a string):

- `["SET", key, value]` — set string `key` to integer `value`. No output.
- `["GET", key]` — output the value for `key`, or the string `"NULL"` if `key` is unset.
- `["DELETE", key]` — unset `key`. No output. Deleting a missing key is a no-op (no output, no error).
- `["COUNT", value]` — output the number of keys whose **effective** value equals integer `value`.
- `["BEGIN"]` — open a new transaction (transactions nest). No output.
- `["COMMIT"]` — merge **all** open transactions into the permanent store and close them; output
  `"OK"`. If there is no open transaction, output `"NO TRANSACTION"` and change nothing.
- `["ROLLBACK"]` — discard the **innermost** open transaction and close just that one; output `"OK"`.
  If there is no open transaction, output `"NO TRANSACTION"`.

Semantics pinned:

- `GET`/`COUNT` always reflect the **current effective state**: the permanent store overlaid by all
  open transactions in order (innermost last).
- A `DELETE` inside a transaction must shadow an outer/permanent value (a later `GET` returns
  `"NULL"`), but a `ROLLBACK` restores it; a `COMMIT` makes the deletion permanent.
- `COMMIT` flattens **every** open level (not just the innermost) and leaves zero open transactions.
- `COUNT` counts keys whose effective value equals the queried value; deleted/unset keys don't count.
- An **unknown command**, a command of the **wrong arity**, or a `SET`/`COUNT` whose value argument
  is **not an int** raises `ValueError`. A `bool` is **not** accepted as an int value (reject
  `True`/`False`).
- Return a list whose elements are ints (numeric `GET`/`COUNT` results) or strings (`"NULL"`, `"OK"`,
  `"NO TRANSACTION"`), in command order.
