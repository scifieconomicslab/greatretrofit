`pack.schema.json` is a **copy** of `schemas/pack.schema.json` from the paperdolls repo, branch `claude/model-packs-6a7453`, commit `cfbcce9`
(`git show claude/model-packs-6a7453:schemas/pack.schema.json`). It is the fallback for `test_pack.py` when the paperdolls validator is not reachable
(it also needs the `jsonschema` package). The paperdolls validator is the reference: it enforces rules the schema cannot. Refresh the copy when the spec changes.
