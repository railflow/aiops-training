"""The two worlds a command can land in: a bare machine, or a sandbox with the properties the providers document.

The numbers (a 256-process limit, a timeout, an egress allow-list) are the lab's assumptions, not measurements of any provider.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from common.spec import SandboxSpec
from mock.threats import Effect

FAKE_SECRETS = {"GITHUB_TOKEN": "ghp_FAKE-not-a-real-token", "OPENAI_API_KEY": "sk-FAKE-not-a-real-key"}
PLACEHOLDER = "dtn_secret_PLACEHOLDER"
PID_LIMIT = 256


def host_files() -> dict:
    return {
        "~/.ssh/id_ed25519": "FAKE-PRIVATE-KEY-NOT-REAL",
        "~/.aws/credentials": "aws_access_key_id=FAKE",
        "~/Documents/taxes-2025.pdf": "FAKE",
        "~/projects/other-client/.env": "DB_URL=FAKE",
        "~/projects/blog/index.md": "FAKE",
        "/tenants/tenant-b/work/.env": "OTHER_TENANT_SECRET=FAKE",
    }


@dataclass
class Outcome:
    host_files_deleted: int = 0
    sandbox_files_deleted: int = 0
    leaked: list = field(default_factory=list)
    placeholders_leaked: list = field(default_factory=list)
    blocked: list = field(default_factory=list)
    credential_abused: list = field(default_factory=list)
    other_tenant_read: bool = False
    machine_frozen: bool = False
    pid_limit_hit: bool = False
    cpu_pegged: bool = False
    cpu_capped: bool = False
    billed_seconds: float = 0.0
    notes: list = field(default_factory=list)
    unknown: bool = False

    def summary(self) -> str:
        parts = []
        if self.host_files_deleted:
            parts.append(f"{self.host_files_deleted} of your files deleted")
        if self.sandbox_files_deleted:
            parts.append("sandbox filesystem wiped (host untouched)")
        if self.leaked:
            parts.append("LEAKED " + ", ".join(self.leaked))
        if self.placeholders_leaked:
            parts.append("only placeholders left: " + ", ".join(self.placeholders_leaked))
        if self.blocked:
            parts.append("blocked: " + ", ".join(sorted(set(self.blocked))))
        if self.credential_abused:
            parts.append("REAL credential used: " + ", ".join(self.credential_abused))
        if self.other_tenant_read:
            parts.append("read another tenant's data")
        if self.machine_frozen:
            parts.append("machine frozen, needs a reboot")
        if self.pid_limit_hit:
            parts.append(f"process limit ({PID_LIMIT}) hit, sandbox killed at timeout")
        if self.cpu_pegged:
            parts.append("CPU pegged until you notice and kill it")
        if self.cpu_capped:
            parts.append(f"CPU capped, sandbox killed at its {int(self.billed_seconds)} s timeout (billed for all of it)")
        if self.unknown:
            parts.append("unknown command, not run")
        return "; ".join(parts) or ("no effect: " + "; ".join(self.notes) if self.notes else "no effect")


class World:
    isolated = False

    def __init__(self, spec: SandboxSpec, secrets_brokered: bool = False) -> None:
        self.spec = spec
        self.files = host_files()
        self.out = Outcome()
        self.held: list = []
        self.brokered = secrets_brokered

    def env_value(self, name: str) -> str:
        return FAKE_SECRETS.get(name, "")

    def egress_allowed(self, host: str) -> bool:
        return True

    def apply(self, effects: list) -> Outcome:
        for e in effects:
            getattr(self, "on_" + e.kind)(e)
        return self.out

    def on_delete(self, e: Effect) -> None:
        self.out.host_files_deleted += len(self.files)
        self.files.clear()

    def on_read(self, e: Effect) -> None:
        if e.arg == "env:*":
            self.held.extend(FAKE_SECRETS)
        elif e.arg.startswith("/tenants/"):
            if e.arg in self.files:
                self.out.other_tenant_read = True
                self.held.append("tenant-b data")
        elif e.arg.startswith("src/"):
            self.held.append("repository source")
        elif e.arg in self.files:
            self.held.append(e.arg)

    def on_net(self, e: Effect) -> None:
        carried, self.held = self.held, []
        if not self.egress_allowed(e.arg):
            self.out.blocked.append(e.arg)
            return
        if e.detail == "send" or carried:
            self.out.leaked.extend(f"{c} -> {e.arg}" for c in carried)

    def on_remote_code(self, e: Effect) -> None:
        self.held.extend(["~/.ssh/id_ed25519", *FAKE_SECRETS])
        self.on_net(Effect("net", e.arg, "send"))

    def on_install_malicious(self, e: Effect) -> None:
        self.held.extend(FAKE_SECRETS)
        self.on_net(Effect("net", "collector.evil.example", "send"))

    def on_auth_use(self, e: Effect) -> None:
        secret, method = e.detail.split()
        if not self.egress_allowed(e.arg):
            self.out.blocked.append(e.arg)
        else:
            self.out.credential_abused.append(f"{secret} on {method} {e.arg}")

    def on_spawn(self, e: Effect) -> None:
        self.out.machine_frozen = True

    def on_burn(self, e: Effect) -> None:
        self.out.cpu_pegged = True

    def on_hang(self, e: Effect) -> None:
        self.out.billed_seconds = float("inf")


class BareWorld(World):
    """Your laptop, or a CI runner, or a plain subprocess: everything the user can reach is reachable."""

    def env_value(self, name: str) -> str:
        return FAKE_SECRETS.get(name, "")

    def on_install_malicious(self, e: Effect) -> None:
        self.out.notes.append(f"{e.arg} ran its install script on your machine")
        super().on_install_malicious(e)


class SandboxWorld(World):
    isolated = True

    def __init__(self, spec: SandboxSpec, secrets_brokered: bool = True) -> None:
        super().__init__(spec, secrets_brokered)
        self.files = {"/work/repo/README.md": "x", "/work/repo/src/inventory/stock.py": "x"}
        self.hosts_for_secret = {s.env_name: s.hosts for s in spec.secrets}

    def egress_allowed(self, host: str) -> bool:
        n = self.spec.network
        if n.mode == "allow-all":
            return True
        if n.mode == "deny-all":
            return False
        return any(host == a or (a.startswith("*.") and host.endswith(a[1:])) for a in n.allow)

    def on_delete(self, e: Effect) -> None:
        self.out.sandbox_files_deleted += len(self.files)
        self.files.clear()

    def on_read(self, e: Effect) -> None:
        if e.arg == "env:*":
            names = list(self.hosts_for_secret) or []
            self.held.extend(names)
            self.out.placeholders_leaked.extend(names)
        elif e.arg.startswith("src/"):
            self.held.append("repository source")
        else:
            self.out.notes.append(f"{e.arg} does not exist inside the sandbox")

    def on_net(self, e: Effect) -> None:
        carried = [c for c in self.held if c not in self.hosts_for_secret]
        placeholders = [c for c in self.held if c in self.hosts_for_secret]
        self.held = []
        if not self.egress_allowed(e.arg):
            self.out.blocked.append(e.arg)
            return
        if e.detail == "send" or carried or placeholders:
            self.out.leaked.extend(f"{c} -> {e.arg}" for c in carried)

    def on_remote_code(self, e: Effect) -> None:
        self.held.extend(self.hosts_for_secret)
        self.out.placeholders_leaked.extend(self.hosts_for_secret)
        self.on_net(Effect("net", e.arg, "send"))

    def on_install_malicious(self, e: Effect) -> None:
        self.out.notes.append(f"{e.arg} installed, but its code runs inside the sandbox")
        self.held.extend(self.hosts_for_secret)
        self.out.placeholders_leaked.extend(self.hosts_for_secret)
        self.on_net(Effect("net", "collector.evil.example", "send"))

    def on_auth_use(self, e: Effect) -> None:
        secret, method = e.detail.split()
        if not self.egress_allowed(e.arg):
            self.out.blocked.append(e.arg)
        elif e.arg in self.hosts_for_secret.get(secret, ()):
            self.out.credential_abused.append(f"{secret} on {method} {e.arg}")
        else:
            self.out.notes.append("the request carried a placeholder, not the credential")

    def on_spawn(self, e: Effect) -> None:
        self.out.pid_limit_hit = True
        self.out.billed_seconds = float(self.spec.timeout_s)

    def on_burn(self, e: Effect) -> None:
        self.out.cpu_capped = True
        self.out.billed_seconds = float(self.spec.timeout_s)

    def on_hang(self, e: Effect) -> None:
        self.out.billed_seconds = float(self.spec.timeout_s)
