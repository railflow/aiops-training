"""python lab/what_could_go_wrong.py : run each hostile command on a bare machine and in a sandbox, in the offline mock."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lab.scenarios import SCENARIOS, run_scenario  # noqa: E402


def main() -> int:
    print("MODEL, not measurement: the mock encodes what sandboxes document; it executes no dangerous command.\n")
    wrong = 0
    for s in SCENARIOS:
        bare, boxed = run_scenario(s, False), run_scenario(s, True)
        print(f"== {s.title}\n   command : {s.command}\n   bare    : {bare.summary()}\n   sandbox : {boxed.summary()}")
        print(f"   verdict : {'contained' if s.sandbox_solves else 'NOT SOLVED BY THE SANDBOX'}. {s.why}\n")
        bad = bool(boxed.host_files_deleted or boxed.machine_frozen or boxed.other_tenant_read) or (s.sandbox_solves and (boxed.leaked or boxed.credential_abused))
        if bad:
            wrong += 1
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
