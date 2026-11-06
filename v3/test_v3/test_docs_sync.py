"""Docs must not drift from code."""
import re
from pathlib import Path

V3 = Path(__file__).resolve().parents[1]


def test_every_placeholder_param_is_documented_and_vice_versa():
    code = set()
    for f in ("params.py", "scene_entities.py"):
        for line in (V3 / "src" / "retrofit_v3" / f).read_text().splitlines():
            m = re.match(r"\s+(\w+):.*# PLACEHOLDER", line)
            if m:
                code.add(m.group(1))
    doc = (V3 / "docs" / "placeholders.md").read_text()
    documented = set(re.findall(r"^\| `(\w+)` \|", doc, flags=re.M))
    assert code, "no placeholders found"
    assert code == documented, (code ^ documented)


def test_frame_schema_documents_every_field():
    from retrofit_v3.frames import BuildingFrame, Frame, SeriesPoint
    doc = (V3 / "docs" / "frame-schema.md").read_text()
    for td in (Frame, BuildingFrame, SeriesPoint):
        for field in td.__annotations__:
            assert f"`{field}`" in doc, field
