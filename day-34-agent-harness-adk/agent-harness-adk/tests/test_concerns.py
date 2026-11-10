import asyncio
import sys

import pytest

from tests.conftest import ROOT

sys.path.insert(0, str(ROOT / "tools"))
import count_concerns as C  # noqa: E402


def test_every_concern_in_the_catalogue_is_present_and_markers_balance():
    result = C.count()
    assert sorted(result["lines"]) == [f"C{n:02d}" for n in range(1, 19)]
    assert all(sum(v.values()) > 0 for v in result["lines"].values())


def test_counter_skips_comments_docstrings_and_nested_regions_belong_to_the_inner_one(tmp_path):
    (tmp_path / "hand_rolled").mkdir()
    (tmp_path / "hand_rolled" / "a.py").write_text('"""doc\nstring"""\n# >> C01 outer\nx = 1\n# a comment\n\n# >> C02 inner\ny = 2\nz = 3\n# << C02\nw = 4\n# << C01\nrest = 5\n')
    result = C.count(tmp_path)
    assert result["lines"]["C01"]["hand_rolled"] == 2 and result["lines"]["C02"]["hand_rolled"] == 2 and result["everything_else"]["hand_rolled"] == 1


def test_unbalanced_markers_are_an_error(tmp_path):
    (tmp_path / "adk").mkdir()
    (tmp_path / "adk" / "a.py").write_text("# >> C01 x\na = 1\n")
    with pytest.raises(ValueError, match="never closed"):
        C.count(tmp_path)


def test_parallel_agent_runs_branches_concurrently_and_merges(tmp_path):
    from adk import parallel_batch

    out = asyncio.run(parallel_batch.run(["a", "b", "c"], str(tmp_path)))
    assert len(out["reports"]) == 3 and all("% covered" in r for r in out["reports"])
    assert out["authors"][:3] == ["scan_0", "scan_1", "scan_2"]  # all three started before any finished its second step
    assert out["merged"].count("% covered") == 3
