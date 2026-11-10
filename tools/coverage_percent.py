#!/usr/bin/env python3
"""Print the overall coverage percentage found in a Cobertura (pytest-cov) or JaCoCo XML report."""
import sys
import xml.etree.ElementTree as ET


def percent(path):
    root = ET.parse(path).getroot()
    if root.tag == "coverage":
        return float(root.attrib["line-rate"]) * 100
    if root.tag == "report":
        for counter in root.findall("counter"):
            if counter.attrib["type"] == "INSTRUCTION":
                missed, covered = int(counter.attrib["missed"]), int(counter.attrib["covered"])
                return 100.0 * covered / (missed + covered)
    raise ValueError(f"unrecognised coverage report format in {path}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: coverage_percent.py REPORT.xml")
    print(f"{percent(sys.argv[1]):.1f}")
