`pack.schema.json` is a **copy** of `schemas/pack.schema.json` from the paperdolls repo, branch `main`, commit `f23f9d4` (2026-11-06; the dashboard, P6 channels and terrain are in it).
It is the fallback for `test_pack.py` when the paperdolls validator is not reachable (it also needs the `jsonschema` package). The paperdolls validator is the reference: it enforces
rules the schema cannot. Refresh the copy when the spec changes.
