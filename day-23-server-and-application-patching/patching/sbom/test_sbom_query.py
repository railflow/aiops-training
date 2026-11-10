from pathlib import Path

import sbom_query as q

SAMPLES = str(Path(__file__).parent / "samples")


def test_version_ordering():
    assert q.is_older("2.14.1", "2.17.0")
    assert not q.is_older("2.17.0", "2.17.0")
    assert not q.is_older("2.17.1", "2.17.0")
    assert q.is_older("2.9", "2.17.0")  # numeric, not string, comparison
    assert q.is_older("2.17", "2.17.1")  # missing parts count as zero


def test_finds_old_log4j(capsys):
    code = q.main([SAMPLES, "--name", "log4j-core", "--below", "2.17.0"])
    out = capsys.readouterr().out
    assert code == 1
    assert "orders-api" in out and "legacy-batch" in out
    assert "billing" not in out and "web" not in out


def test_clean_when_threshold_is_low():
    assert q.main([SAMPLES, "--name", "log4j-core", "--below", "2.0"]) == 0


def test_empty_directory(tmp_path):
    assert q.main([str(tmp_path), "--name", "x", "--below", "1"]) == 2


def test_name_normalisation():
    assert q.normalize("Jinja2") == "jinja2"
    assert q.normalize("python_dateutil") == q.normalize("python-dateutil")
