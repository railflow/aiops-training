import json
import os

import classify
import evaluate
import make_dataset

DATA = os.path.join(os.path.dirname(__file__), "..", "decision", "dataset.jsonl")


def test_dataset_is_deterministic_and_matches_the_committed_file():
    rows = make_dataset.make(300, 7)
    assert rows == [json.loads(line) for line in open(DATA)]
    assert {r["label"] for r in rows} == {"flaky", "real"}


def test_decide_bands():
    assert evaluate.decide(0.9, 0.75, 0.35) == "auto_flaky"
    assert evaluate.decide(0.2, 0.75, 0.35) == "auto_real"
    assert evaluate.decide(0.5, 0.75, 0.35) == "human"


def test_precision_recall_hand_computed():
    rows = [{"label": "flaky"}, {"label": "flaky"}, {"label": "real"}, {"label": "real"}]
    p, r, tp, fp, fn = evaluate.prf(rows, [True, False, True, False])
    assert (tp, fp, fn) == (1, 1, 1) and p == 0.5 and r == 0.5


def test_output_contract_of_heuristic():
    out = classify.classify_heuristic(json.loads(open(DATA).readline()))
    assert set(out) == {"label", "probability", "reasons"} and 0 <= out["probability"] <= 1 and out["reasons"]


def test_review_band_trades_automation_for_precision():
    rows = [json.loads(line) for line in open(DATA)]
    probs = [classify.classify_heuristic(r)["probability"] for r in rows]
    narrow = evaluate.evaluate(rows, probs, 0.5, 0.5)
    wide = evaluate.evaluate(rows, probs, 0.75, 0.35)
    assert narrow["human_share"] == 0 and wide["human_share"] > 0
    assert wide["precision"] > narrow["precision"]


def test_sweep_precision_rises_and_recall_falls_with_threshold():
    rows = [json.loads(line) for line in open(DATA)]
    s = evaluate.sweep(rows, [classify.classify_heuristic(r)["probability"] for r in rows])
    assert s[-1][2] < s[0][2] and s[-1][1] > s[0][1]


def test_jev_combination_math():
    answers = {"flaky": {"noul": 1.0}, "history": {"noul": 1.0}, "retry": {"noul": 1.0}, "touches": {"noul": 0.0}}
    assert classify.combine_jev_answers(answers)["probability"] == 1.0
    answers = {k: {"noul": 0.0} for k in ("flaky", "history", "retry")} | {"touches": {"noul": 1.0}}
    assert classify.combine_jev_answers(answers)["label"] == "real"


def test_jev_request_and_response_shape_against_a_fake_server(fake_server, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    fake_server.answer = staticmethod(lambda body: {"model": body["model"], "usage": {"cost": 1e-6},
                                                    "answers": {k: {"type": "noul", "noul": 0.9 if k != "touches" else 0.1} for k in body["questions"]}})
    rec = json.loads(open(DATA).readline())
    out = classify.classify_jev(rec, url=fake_server.url + "/api/alpha/decisions")
    sent = fake_server.seen[0]["body"]
    assert set(sent["questions"]) == {"flaky", "history", "retry", "touches"} and sent["state"]["error"] == rec["error"]
    assert out["label"] == "flaky" and out["cost"] == 1e-6 and len(out["reasons"]) == 4
