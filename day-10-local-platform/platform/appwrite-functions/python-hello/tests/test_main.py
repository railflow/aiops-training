import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fakectx import make_context  # noqa: E402
from main import main  # noqa: E402


def test_default_greeting():
    out = main(make_context())
    assert json.loads(out["body"]) == {"message": "Hello, world!", "runtime": "python"}


def test_named_greeting_and_log():
    ctx = make_context(query={"name": "Ada"})
    out = main(ctx)
    assert json.loads(out["body"])["message"] == "Hello, Ada!"
    assert ctx.logs


def test_ping():
    assert main(make_context(path="/ping"))["body"] == "pong"
