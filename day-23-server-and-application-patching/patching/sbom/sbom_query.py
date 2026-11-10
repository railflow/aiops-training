#!/usr/bin/env python3
"""Answer "who runs <package> older than <version>?" from a directory of CycloneDX JSON SBOMs.

    python3 sbom_query.py samples --name log4j-core --below 2.17.0

Exit status: 0 when nothing matches, 1 when at least one SBOM contains a match, 2 on bad input.
That makes it usable as a gate as well as a question.
"""
import argparse
import json
import re
import sys
from pathlib import Path


def parse_version(text):
    """Turn '2.14.1' or '2.17.0-rc1' into a comparable tuple of ints (non-numeric parts are ignored).

    Good enough for the semver-like versions in the examples. Real ecosystems (Debian epochs, Python
    pre-releases, Maven qualifiers) need an ecosystem-aware comparison; do not trust this blindly.
    """
    parts = re.findall(r"\d+", text.split("-")[0])
    if not parts:
        raise ValueError(f"cannot parse version {text!r}")
    return tuple(int(p) for p in parts)


def is_older(version, limit):
    a, b = parse_version(version), parse_version(limit)
    width = max(len(a), len(b))
    pad = lambda t: t + (0,) * (width - len(t))
    return pad(a) < pad(b)


def normalize(name):
    """Package names differ in case and separators between tools (Jinja2 vs jinja2, python_dateutil vs python-dateutil)."""
    return re.sub(r"[-_.]+", "-", name).lower()


def find_matches(sbom, name, below):
    app = sbom.get("metadata", {}).get("component", {}).get("name", "unknown")
    hits = []
    for comp in sbom.get("components", []):
        if normalize(comp.get("name", "")) == normalize(name) and comp.get("version") and is_older(comp["version"], below):
            hits.append({"app": app, "name": name, "group": comp.get("group", ""), "version": comp["version"]})
    return hits


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("directory", help="directory containing *.json CycloneDX SBOMs")
    ap.add_argument("--name", required=True, help="component name; case and -/_/. differences are ignored (for example log4j-core)")
    ap.add_argument("--below", required=True, help="report versions strictly older than this (for example 2.17.0)")
    args = ap.parse_args(argv)

    files = sorted(Path(args.directory).glob("*.json"))
    if not files:
        print(f"no SBOM files in {args.directory}", file=sys.stderr)
        return 2
    hits = []
    for f in files:
        try:
            hits += find_matches(json.loads(f.read_text()), args.name, args.below)
        except (ValueError, json.JSONDecodeError) as exc:
            print(f"skipping {f.name}: {exc}", file=sys.stderr)
    for h in hits:
        print(f"{h['app']}\t{h['group']}:{h['name']}\t{h['version']}")
    print(f"{len(hits)} of {len(files)} SBOMs contain {args.name} older than {args.below}", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
