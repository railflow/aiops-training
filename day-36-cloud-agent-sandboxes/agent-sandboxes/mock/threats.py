"""How the mock understands a command. It is a MODEL of what dangerous commands do, written for teaching.

Nothing here executes a dangerous command. `interpret` turns the text into a list of effects; `world.py` decides what each effect
would reach on a bare machine and inside a sandbox. Commands that match no rule are reported as unknown, never run.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

TYPOSQUATS = {"reqeusts", "python-dateutl", "colourama", "urlib3"}
HOST = r"([a-z0-9][a-z0-9.-]*\.[a-z]{2,})"


@dataclass(frozen=True)
class Effect:
    kind: str  # delete, read, net, spawn, burn, remote_code, install_malicious, auth_use, hang
    arg: str = ""
    detail: str = ""


def interpret(command: str) -> list:
    c = command.strip()
    effects: list = []
    if re.search(r":\(\)\s*\{.*\|.*&.*\}\s*;\s*:", c):
        return [Effect("spawn", "unbounded")]
    m = re.search(r"\brm\s+-[a-zA-Z]*[rR][a-zA-Z]*\s+(/\*?|~/?\*?|\$HOME/?\*?)(\s|$)", c)
    if m:
        effects.append(Effect("delete", "/" if m.group(1).startswith("/") else "~"))
    for path in re.findall(r"(~/\.ssh/[\w.-]+|~/\.aws/credentials|/etc/shadow)", c):
        effects.append(Effect("read", path))
    for path in re.findall(r"(/tenants/[\w./-]+)", c):
        effects.append(Effect("read", path))
    for path in re.findall(r"\b(src/[\w./-]+\.py)\b", c):
        if re.match(r"\s*cat\b", c):
            effects.append(Effect("read", path))
    if re.search(r"(?<![\w./-])(printenv|env)\b(?!\s*=)|\$\{?[A-Z_]*(KEY|TOKEN|SECRET)[A-Z_]*\}?", c) and not re.search(r"-H\s+[\"'][^\"']*\$", c):
        effects.append(Effect("read", "env:*"))
    auth = re.search(r"-H\s+[\"']Authorization:[^\"']*\$\{?([A-Z_]+)\}?[\"']", c)
    net = re.search(r"\b(curl|wget|nc|ncat|scp)\b[^|;&]*?(?:https?://)?" + HOST, c, re.I)
    if net and re.search(r"\|\s*(sh|bash)\b", c):
        effects.append(Effect("net", net.group(2).lower(), "download"))
        effects.append(Effect("remote_code", net.group(2).lower()))
    elif net and auth:
        method = (re.search(r"-X\s+([A-Z]+)", c) or [None, "GET"])[1]
        effects.append(Effect("auth_use", net.group(2).lower(), f"{auth.group(1)} {method}"))
    elif net:
        effects.append(Effect("net", net.group(2).lower(), "send" if re.search(r"-d\b|--data|--upload|@-|-T\b", c) else "get"))
    pip = re.search(r"\bpip3?\s+install\s+([\w.-]+)", c)
    if pip and pip.group(1).lower() in TYPOSQUATS:
        effects.append(Effect("install_malicious", pip.group(1).lower()))
    if re.search(r"\byes\b\s*>\s*/dev/null|while\s+true|\bdd\s+if=/dev/zero|\bstress\b", c):
        effects.append(Effect("burn"))
    if re.search(r"\bsleep\s+\d{4,}", c):
        effects.append(Effect("hang"))
    return effects
