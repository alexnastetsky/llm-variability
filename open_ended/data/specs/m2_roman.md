# roman numerals (two files)

Implement across **two files**:

- `core.py` — holds the Roman-numeral symbol table.
- `api.py` — imports from `core` (use an absolute import, e.g. `from core import ...`)
  and exposes the entry function:

  `def to_roman(n: int) -> str`

Convert an integer `n` in the range **1..3999** to its standard Roman numeral, using
subtractive notation: `IV`=4, `IX`=9, `XL`=40, `XC`=90, `CD`=400, `CM`=900. Symbol
values: `I`=1, `V`=5, `X`=10, `L`=50, `C`=100, `D`=500, `M`=1000.
