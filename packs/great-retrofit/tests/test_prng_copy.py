"""packs/great-retrofit/prng.js is a pack-local copy of v3/js/prng.js (the pack folder must be self-contained for `pack build`).
The copy must stay byte-identical, and must pass the shared PRNG vectors on its own."""
import shutil
import subprocess
from pathlib import Path

import pytest

PACK = Path(__file__).resolve().parents[1]
V3 = PACK.parents[1] / "v3"


def test_pack_prng_is_identical_to_v3_prng():
    assert (PACK / "prng.js").read_bytes() == (V3 / "js" / "prng.js").read_bytes(), \
        "packs/great-retrofit/prng.js differs from v3/js/prng.js: copy v3/js/prng.js over it (cp v3/js/prng.js packs/great-retrofit/prng.js)"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_pack_prng_passes_shared_vectors():
    # test_prng.js requires ./prng.js and reads ../test_v3/vectors/prng.json: run it against the pack copy in a temp layout
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        (t / "js").mkdir()
        (t / "test_v3").symlink_to(V3 / "test_v3")
        shutil.copy(PACK / "prng.js", t / "js" / "prng.js")
        shutil.copy(V3 / "js" / "test_prng.js", t / "js" / "test_prng.js")
        r = subprocess.run(["node", str(t / "js" / "test_prng.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
