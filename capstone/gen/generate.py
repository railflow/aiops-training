#!/usr/bin/env python3
"""Deterministic fallback generator: stamps small repositories with planted bugs, no model and no tokens.

  python3 generate.py --out ./repos --count 5 --seed 42                  # five repos across the five languages, plus repos.csv
  python3 generate.py --out ./repos --lang python --domain billing --name billing-py-001 --seed 7 --filler 40

What you get per repo: source with a few ordinary functions, `filler` generated helpers (bulk), a handful of tests that cover only
part of it, pinned vulnerable dependencies, a fake hardcoded secret (assembled at run time so THIS repository never contains the
pattern), and a `<repo>.planted-issues.json` answer key (kept outside the repo): id, file, line range, category and severity of every planted bug.
The answer keys are written OUTSIDE the repos (default ../answer-keys/<repo>.planted-issues.json) so agents cloning a repo cannot read them.
Each repo is its own git repository with a small, dated, deterministic commit history. Same --seed and arguments give the same repos.

The AI-generated route (gen/prompts/ and gen_with_claude.sh) produces larger, more realistic repos; this one is the free, repeatable one.
Languages: python, node, java, go, dotnet. Verified here by building and testing: python, node, java. go and dotnet are generated but were NOT
compiled on the author's machine (no toolchain installed): treat them as untested.
"""
import argparse
import csv
import json
import os
import random
import subprocess
import sys
from pathlib import Path

LANGS = ["python", "node", "java", "go", "dotnet"]
SHORT = {"python": "py", "node": "js", "java": "java", "go": "go", "dotnet": "cs"}

# name: (Entity, plural, a numeric field, a text field)
DOMAINS = {
    "inventory": ("Item", "items", "quantity", "sku"),
    "billing": ("Invoice", "invoices", "amount", "customer"),
    "csv-importer": ("Row", "rows", "columns", "header"),
    "url-shortener": ("Link", "links", "clicks", "slug"),
    "booking": ("Reservation", "reservations", "nights", "guest"),
    "payroll": ("Payslip", "payslips", "hours", "employee"),
    "shipping": ("Parcel", "parcels", "weight", "address"),
    "ticketing": ("Ticket", "tickets", "priority", "title"),
    "loyalty": ("Account", "accounts", "points", "member"),
    "catalog": ("Product", "products", "price", "name"),
    "scheduler": ("Job", "jobs", "retries", "cron"),
    "notifications": ("Message", "messages", "attempts", "recipient"),
}

# ---------------------------------------------------------------------------------------------------------------------------
# Planted bugs. @E@ = Entity, @e@ = entity (lower), @n@ = numeric field, @t@ = text field. Each: (id, category, severity, description, lines)
# ---------------------------------------------------------------------------------------------------------------------------
# Fake credentials, assembled at run time so THIS file never holds a complete secret-shaped string, while the generated repos
# do (a scanner must find them). Not the AWS documentation example: gitleaks allow-lists values ending in EXAMPLE.
AWS_ID = '"' + "AKIA" + "QWERTYUIOPASDFGH" + '"'
AWS_SECRET = '"' + "k3Jd9xQ2mZp7Lw4N" + "8vRz4KpW0sYb6HdJ" + "1cTe5UaF" + '"'

PY = [
    ("off-by-one", "medium", "paginate drops the last element of every page",
     ["def paginate_@e@(items, page, size):", "    start = page * size", "    return items[start:start + size - 1]"]),
    ("null-handling", "high", "normalize_@t@ crashes on a missing value",
     ["def normalize_@t@(value):", "    return value.strip().title()"]),
    ("divide-by-zero", "medium", "average_@n@ divides by zero on an empty list",
     ["def average_@n@(values):", "    return sum(values) / len(values)"]),
    ("bad-parsing", "medium", "split on comma breaks quoted fields",
     ["def parse_@e@_line(line):", "    return line.split(',')"]),
    ("timezone", "medium", "mixes naive local time with UTC timestamps",
     ["def is_expired_@e@(iso_timestamp):", "    from datetime import datetime", "    return datetime.fromisoformat(iso_timestamp) < datetime.now()"]),
    ("race-condition", "high", "shared counter incremented from threads with no lock",
     ["COUNTER = {'value': 0}", "", "def next_@e@_id():", "    current = COUNTER['value']", "    COUNTER['value'] = current + 1", "    return current + 1"]),
    ("sql-injection", "high", "query built by string formatting from user input, no validation",
     ["def find_@e@_sql(@t@):", "    return \"SELECT * FROM @e@ WHERE @t@ = '%s'\" % @t@"]),
    ("hardcoded-secret", "high", "fake cloud credentials committed in source (course fixture, not real)",
     ["AWS_ACCESS_KEY_ID = " + AWS_ID, "AWS_SECRET_ACCESS_KEY = " + AWS_SECRET]),
    ("deprecated-api", "low", "datetime.utcnow() is deprecated and returns a naive datetime",
     ["def stamp_@e@():", "    from datetime import datetime", "    return datetime.utcnow().isoformat()"]),
]

JS = [
    ("off-by-one", "medium", "paginate drops the last element of every page",
     ["function paginate@E@(items, page, size) {", "  const start = page * size;", "  return items.slice(start, start + size - 1);", "}"]),
    ("null-handling", "high", "normalize@T@ throws on a missing value",
     ["function normalize@T@(value) {", "  return value.trim().toUpperCase();", "}"]),
    ("divide-by-zero", "medium", "average@N@ returns NaN on an empty array",
     ["function average@N@(values) {", "  return values.reduce((a, b) => a + b, 0) / values.length;", "}"]),
    ("bad-parsing", "medium", "parseInt without radix or validation accepts garbage",
     ["function parse@N@(text) {", "  return parseInt(text);", "}"]),
    ("timezone", "medium", "compares a UTC ISO string to local midnight",
     ["function isToday@E@(iso) {", "  const d = new Date(iso);", "  const now = new Date();", "  return d.getDate() === now.getDate();", "}"]),
    ("race-condition", "high", "read-modify-write across an await lets two calls clobber each other",
     ["let counter = 0;", "async function next@E@Id(save) {", "  const current = counter;", "  await save(current + 1);", "  counter = current + 1;", "  return counter;", "}"]),
    ("sql-injection", "high", "query built by template string from user input, no validation",
     ["function find@E@Sql(@t@) {", "  return `SELECT * FROM @e@ WHERE @t@ = '${@t@}'`;", "}"]),
    ("hardcoded-secret", "high", "fake cloud credentials committed in source (course fixture, not real)",
     ["const AWS_ACCESS_KEY_ID = " + AWS_ID + ";", "const AWS_SECRET_ACCESS_KEY = " + AWS_SECRET + ";"]),
    ("deprecated-api", "low", "Buffer constructor is deprecated (unsafe)",
     ["function legacyBuffer(text) {", "  return new Buffer(text);", "}"]),
]

JAVA = [
    ("off-by-one", "medium", "paginate drops the last element of every page",
     ["    public static <T> java.util.List<T> paginate(java.util.List<T> items, int page, int size) {", "        int start = page * size;",
      "        return items.subList(start, Math.min(items.size(), start + size - 1));", "    }"]),
    ("null-handling", "high", "normalize throws NullPointerException on a missing value",
     ["    public static String normalize@T@(String value) {", "        return value.trim().toUpperCase();", "    }"]),
    ("integer-overflow", "high", "total multiplies two ints and overflows silently",
     ["    public static int totalCents(int unitCents, int @n@) {", "        return unitCents * @n@;", "    }"]),
    ("bad-parsing", "medium", "swallows NumberFormatException and returns 0",
     ["    public static int parse@N@(String text) {", "        try {", "            return Integer.parseInt(text);", "        } catch (NumberFormatException e) {", "            return 0;", "        }", "    }"]),
    ("timezone", "medium", "SimpleDateFormat uses the JVM default time zone and is not thread-safe",
     ["    private static final java.text.SimpleDateFormat FORMAT = new java.text.SimpleDateFormat(\"yyyy-MM-dd HH:mm\");",
      "    public static String format@E@Time(java.util.Date when) {", "        return FORMAT.format(when);", "    }"]),
    ("race-condition", "high", "unsynchronised counter",
     ["    private static int counter = 0;", "    public static int next@E@Id() {", "        counter++;", "        return counter;", "    }"]),
    ("sql-injection", "high", "query built by concatenation from user input, no validation",
     ["    public static String find@E@Sql(String @t@) {", "        return \"SELECT * FROM @e@ WHERE @t@ = '\" + @t@ + \"'\";", "    }"]),
    ("hardcoded-secret", "high", "fake cloud credentials committed in source (course fixture, not real)",
     ["    public static final String AWS_ACCESS_KEY_ID = " + AWS_ID + ";", "    public static final String AWS_SECRET_ACCESS_KEY = " + AWS_SECRET + ";"]),
    ("deprecated-api", "low", "boxing constructor is deprecated for removal",
     ["    @SuppressWarnings(\"removal\")", "    public static Integer legacyBox(int v) {", "        return new Integer(v);", "    }"]),
]

GO = [
    ("off-by-one", "medium", "Paginate drops the last element of every page",
     ["func Paginate@E@(items []string, page, size int) []string {", "\tstart := page * size", "\tend := start + size - 1", "\tif end > len(items) {", "\t\tend = len(items)", "\t}", "\treturn items[start:end]", "}"]),
    ("null-handling", "high", "Normalize dereferences a nil pointer",
     ["func Normalize@T@(value *string) string {", "\treturn strings.ToUpper(strings.TrimSpace(*value))", "}"]),
    ("integer-overflow", "high", "Total multiplies int32 values and overflows silently",
     ["func TotalCents(unitCents, @n@ int32) int32 {", "\treturn unitCents * @n@", "}"]),
    ("bad-parsing", "medium", "ignores the strconv error and returns 0",
     ["func Parse@N@(text string) int {", "\tn, _ := strconv.Atoi(text)", "\treturn n", "}"]),
    ("timezone", "medium", "compares time.Now() in local time with a UTC timestamp's wall clock",
     ["func IsToday@E@(ts time.Time) bool {", "\tnow := time.Now()", "\treturn ts.Day() == now.Day()", "}"]),
    ("race-condition", "high", "counter incremented from goroutines with no mutex or atomic",
     ["var counter int", "", "func Next@E@ID() int {", "\tcounter++", "\treturn counter", "}"]),
    ("sql-injection", "high", "query built by Sprintf from user input, no validation",
     ["func Find@E@SQL(@t@ string) string {", "\treturn fmt.Sprintf(\"SELECT * FROM @e@ WHERE @t@ = '%s'\", @t@)", "}"]),
    ("hardcoded-secret", "high", "fake cloud credentials committed in source (course fixture, not real)",
     ["var AWSAccessKeyID = " + AWS_ID, "var AWSSecretAccessKey = " + AWS_SECRET]),
    ("deprecated-api", "low", "io/ioutil is deprecated since Go 1.16",
     ["func LegacyRead(r io.Reader) ([]byte, error) {", "\treturn ioutil.ReadAll(r)", "}"]),
]

CS = [
    ("off-by-one", "medium", "Paginate drops the last element of every page",
     ["    public static List<T> Paginate@E@<T>(List<T> items, int page, int size)", "    {", "        int start = page * size;",
      "        return items.GetRange(start, Math.Min(items.Count - start, size - 1));", "    }"]),
    ("null-handling", "high", "Normalize throws NullReferenceException on a missing value",
     ["    public static string Normalize@T@(string value)", "    {", "        return value.Trim().ToUpper();", "    }"]),
    ("integer-overflow", "high", "unchecked int multiplication overflows silently",
     ["    public static int TotalCents(int unitCents, int @n@)", "    {", "        return unchecked(unitCents * @n@);", "    }"]),
    ("bad-parsing", "medium", "swallows FormatException and returns 0",
     ["    public static int Parse@N@(string text)", "    {", "        try { return int.Parse(text); }", "        catch (FormatException) { return 0; }", "    }"]),
    ("timezone", "medium", "compares DateTime.Now (local) with a UTC value",
     ["    public static bool IsExpired@E@(DateTime utcExpiry)", "    {", "        return utcExpiry < DateTime.Now;", "    }"]),
    ("race-condition", "high", "non-atomic counter shared between threads",
     ["    private static int _counter = 0;", "    public static int Next@E@Id()", "    {", "        _counter++;", "        return _counter;", "    }"]),
    ("sql-injection", "high", "query built by interpolation from user input, no validation",
     ["    public static string Find@E@Sql(string @t@)", "    {", "        return $\"SELECT * FROM @e@ WHERE @t@ = '{@t@}'\";", "    }"]),
    ("hardcoded-secret", "high", "fake cloud credentials committed in source (course fixture, not real)",
     ["    public static readonly string AwsAccessKeyId = " + AWS_ID + ";", "    public static readonly string AwsSecretAccessKey = " + AWS_SECRET + ";"]),
    ("deprecated-api", "low", "WebClient is obsolete",
     ["    public static string LegacyDownload(string url)", "    {", "        return new System.Net.WebClient().DownloadString(url);", "    }"]),
]
LIBS = {"python": PY, "node": JS, "java": JAVA, "go": GO, "dotnet": CS}

VULN_DEPS = {  # known-vulnerable pins: confirm with `trivy fs`, then fix them in Day 23
    "python": ["requests==2.31.0", "urllib3==1.26.18", "jinja2==3.1.2"],
    "node": {"lodash": "4.17.20", "minimist": "1.2.5"},
    "java": [("org.apache.logging.log4j", "log4j-core", "2.14.1"), ("org.apache.commons", "commons-text", "1.9")],
    "go": [("golang.org/x/crypto", "v0.14.0")],
    "dotnet": [("Newtonsoft.Json", "12.0.1")],
}


class Repo:
    def __init__(self, name, lang, domain, seed):
        self.name, self.lang, self.domain, self.seed = name, lang, domain, seed
        self.files = {}      # path -> list of lines
        self.planted = []    # dicts

    def put(self, path, lines):
        self.files[path] = list(lines)

    def append(self, path, lines):
        cur = self.files.setdefault(path, [])
        start = len(cur) + 1
        cur.extend(lines)
        return start, len(cur)


def sub(lines, d):
    out = []
    for ln in lines:
        for k, v in d.items():
            ln = ln.replace(k, v)
        out.append(ln)
    return out


def names(domain):
    E, plural, n, t = DOMAINS[domain]
    return {"@E@": E, "@e@": E.lower(), "@N@": n.capitalize(), "@n@": n, "@T@": t.capitalize(), "@t@": t}


def pick_bugs(rng, lang, count):
    lib = LIBS[lang]
    idx = sorted(rng.sample(range(len(lib)), min(count, len(lib))))
    must = [i for i, b in enumerate(lib) if b[0] in ("hardcoded-secret", "null-handling")]   # every repo gets a secret and a null bug
    for m in must:
        if m not in idx:
            idx.append(m)
    return [lib[i] for i in sorted(set(idx))]


def plant(repo, path, bug, d, header_gap=True):
    cat, sev, desc, lines = bug
    body = sub(lines, d)
    cur = repo.files.setdefault(path, [])
    if header_gap and cur and cur[-1] != "":
        cur.append("")
    start, end = repo.append(path, body)
    repo.planted.append({"id": f"{repo.name}-P{len(repo.planted) + 1:02d}", "file": path, "line_start": start, "line_end": end,
                         "category": cat, "severity": sev, "description": sub([desc], d)[0]})
    cur.append("")


# ---------------------------------------------------------------------------------------------------------------------------
# Per-language builders
# ---------------------------------------------------------------------------------------------------------------------------
def add_flaky(repo, path, t, block, desc, category="flaky-test"):
    start = len(t) + 1
    t.extend(block)
    repo.planted.append({"id": f"{repo.name}-P{len(repo.planted) + 1:02d}", "file": path, "line_start": start, "line_end": len(t),
                         "category": category, "severity": "low", "description": desc})


def build_python(repo, rng, filler, bugs):
    d = names(repo.domain); E, e = d["@E@"], d["@e@"]
    pkg = e + "_service"
    repo.put(f"{pkg}/__init__.py", [])
    core = [f'"""{E} service core ({repo.domain})."""', "", "",
            f"def create_{e}({d['@t@']}, {d['@n@']}):", f'    """Create a {e} record."""',
            f"    if not {d['@t@']}:", f'        raise ValueError("{d["@t@"]} is required")',
            f"    return {{'{d['@t@']}': {d['@t@']}, '{d['@n@']}': {d['@n@']}}}", "", "",
            f"def describe_{e}(record):", f"    return f\"{{record['{d['@t@']}']}} ({{record['{d['@n@']}']}})\"", ""]
    repo.put(f"{pkg}/core.py", core)
    repo.put(f"{pkg}/helpers.py", [f'"""Generated helpers for {e}."""', ""])
    for i in range(filler):
        repo.append(f"{pkg}/helpers.py", ["", f"def validate_{e}_{i}(value):", f'    """Validate field {i} of a {e} (generated)."""',
                                         "    if value is None:", f'        raise ValueError("{e} field {i} is required")',
                                         "    text = str(value).strip()", f"    if len(text) > {20 + i}:", f'        raise ValueError("{e} field {i} is too long")',
                                         "    return text", ""])
    repo.put(f"{pkg}/rules.py", [f'"""Business rules for {e}."""', ""])
    for b in bugs:
        plant(repo, f"{pkg}/rules.py", b, d)
    t = [f"from {pkg}.core import create_{e}, describe_{e}", f"from {pkg} import helpers", "", "",
         f"def test_create_{e}():", f"    rec = create_{e}('a', 1)", f"    assert rec['{d['@t@']}'] == 'a'", "", "",
         f"def test_describe_{e}():", f"    assert describe_{e}(create_{e}('a', 1)) == 'a (1)'", ""]
    for i in range(0, filler, 4):  # cover only a quarter of the helpers
        t += ["", f"def test_validate_{i}():", f"    assert helpers.validate_{e}_{i}(' x ') == 'x'", ""]
    t.append("")
    add_flaky(repo, "tests/test_core.py", t, ["def test_jitter_stays_in_range():", "    import random", "    assert random.random() < 0.9"],
              "assertion on random.random() fails about one run in ten")
    t.append("")
    repo.put("tests/test_core.py", t)
    repo.put("requirements.txt", VULN_DEPS["python"])
    repo.put("requirements-dev.txt", ["-r requirements.txt", "pytest==9.2.0", "pytest-cov"])
    repo.put("pytest.ini", ["[pytest]", "pythonpath = ."])


def build_node(repo, rng, filler, bugs):
    d = names(repo.domain); E, e = d["@E@"], d["@e@"]
    repo.put("package.json", [json.dumps({
        "name": repo.name, "version": "1.0.0", "private": True, "type": "commonjs",
        "scripts": {"test": "node --test"}, "dependencies": VULN_DEPS["node"]}, indent=2)])
    repo.put("src/core.js", [f"// {E} service core ({repo.domain})", "",
                             f"function create{E}({d['@t@']}, {d['@n@']}) {{", f"  if (!{d['@t@']}) throw new Error('{d['@t@']} is required');",
                             f"  return {{ {d['@t@']}, {d['@n@']} }};", "}", "", f"module.exports = {{ create{E} }};", ""])
    helpers = [f"// Generated helpers for {e}", ""]
    for i in range(filler):
        helpers += [f"function validate{E}{i}(value) {{", "  if (value === null || value === undefined) {", f"    throw new Error('{e} field {i} is required');", "  }",
                    "  const text = String(value).trim();", f"  if (text.length > {20 + i}) {{", f"    throw new Error('{e} field {i} is too long');", "  }", "  return text;", "}", ""]
    helpers.append("module.exports = { " + ", ".join(f"validate{E}{i}" for i in range(filler)) + " };" if filler else "module.exports = {};")
    repo.put("src/helpers.js", helpers + [""])
    repo.put("src/rules.js", [f"// Business rules for {e}", ""])
    exports = []
    for b in bugs:
        plant(repo, "src/rules.js", b, d)
    names_ = []
    for ln in repo.files["src/rules.js"]:
        for kw in ("function ", "async function "):
            if ln.startswith(kw):
                names_.append(ln[len(kw):].split("(")[0])
        if ln.startswith("const ") or ln.startswith("let "):
            pass
    repo.append("src/rules.js", ["module.exports = { " + ", ".join(sorted(set(names_))) + " };", ""])
    t = ["const test = require('node:test');", "const assert = require('node:assert');", f"const {{ create{E} }} = require('../src/core');",
         f"const helpers = require('../src/helpers');", "", f"test('create{E}', () => {{", f"  assert.strictEqual(create{E}('a', 1).{d['@t@']}, 'a');", "});", ""]
    for i in range(0, filler, 4):
        t += [f"test('validate {i}', () => {{", f"  assert.strictEqual(helpers.validate{E}{i}(' x '), 'x');", "});", ""]
    add_flaky(repo, "test/core.test.js", t, ["test('jitter stays in range', () => {", "  assert.ok(Math.random() < 0.9);", "});"],
              "assertion on Math.random() fails about one run in ten")
    t.append("")
    repo.put("test/core.test.js", t)


def build_java(repo, rng, filler, bugs):
    d = names(repo.domain); E, e = d["@E@"], d["@e@"]
    pkg = "com.example." + e
    base = "src/main/java/" + pkg.replace(".", "/")
    tbase = "src/test/java/" + pkg.replace(".", "/")
    deps = "\n".join(f"    <dependency><groupId>{g}</groupId><artifactId>{a}</artifactId><version>{v}</version></dependency>" for g, a, v in VULN_DEPS["java"])
    repo.put("pom.xml", f"""<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>com.example</groupId><artifactId>{repo.name}</artifactId><version>1.0.0</version><packaging>jar</packaging>
  <properties><maven.compiler.source>17</maven.compiler.source><maven.compiler.target>17</maven.compiler.target><project.build.sourceEncoding>UTF-8</project.build.sourceEncoding></properties>
  <dependencies>
{deps}
    <dependency><groupId>org.junit.jupiter</groupId><artifactId>junit-jupiter</artifactId><version>5.10.2</version><scope>test</scope></dependency>
  </dependencies>
  <build><plugins>
    <plugin><groupId>org.apache.maven.plugins</groupId><artifactId>maven-surefire-plugin</artifactId><version>3.2.5</version></plugin>
    <plugin><groupId>org.jacoco</groupId><artifactId>jacoco-maven-plugin</artifactId><version>0.8.12</version>
      <executions>
        <execution><goals><goal>prepare-agent</goal></goals></execution>
        <execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>
      </executions></plugin>
  </plugins></build>
</project>
""".splitlines())
    repo.put(f"{base}/Core.java", [f"package {pkg};", "", "public final class Core {", "    private Core() {}", "",
                                   f"    public static String create{E}(String {d['@t@']}, int {d['@n@']}) {{",
                                   f"        if ({d['@t@']} == null || {d['@t@']}.isEmpty()) throw new IllegalArgumentException(\"{d['@t@']} is required\");",
                                   f"        return {d['@t@']} + \":\" + {d['@n@']};", "    }", "}", ""])
    h = [f"package {pkg};", "", "public final class Helpers {", "    private Helpers() {}", ""]
    for i in range(filler):
        h += [f"    public static String validate{E}{i}(Object value) {{", "        if (value == null) {", f"            throw new IllegalArgumentException(\"{e} field {i} is required\");",
              "        }", "        String text = value.toString().trim();", f"        if (text.length() > {20 + i}) {{", f"            throw new IllegalArgumentException(\"{e} field {i} is too long\");",
              "        }", "        return text;", "    }", ""]
    h.append("}")
    repo.put(f"{base}/Helpers.java", h + [""])
    repo.put(f"{base}/Rules.java", [f"package {pkg};", "", "public final class Rules {", "    private Rules() {}", ""])
    for b in bugs:
        plant(repo, f"{base}/Rules.java", b, d, header_gap=False)
    repo.append(f"{base}/Rules.java", ["}", ""])
    t = [f"package {pkg};", "", "import org.junit.jupiter.api.Test;", "import static org.junit.jupiter.api.Assertions.*;", "", "class CoreTest {",
         "    @Test", f"    void create() {{ assertEquals(\"a:1\", Core.create{E}(\"a\", 1)); }}", ""]
    for i in range(0, filler, 4):
        t += ["    @Test", f"    void validate{i}() {{ assertEquals(\"x\", Helpers.validate{E}{i}(\" x \")); }}", ""]
    add_flaky(repo, f"{tbase}/CoreTest.java", t, ["    @Test", "    void jitterStaysInRange() { assertTrue(Math.random() < 0.9); }"],
              "assertion on Math.random() fails about one run in ten")
    t += ["}", ""]
    repo.put(f"{tbase}/CoreTest.java", t)


def build_go(repo, rng, filler, bugs):
    d = names(repo.domain); E, e = d["@E@"], d["@e@"]
    pkg = e
    repo.put("go.mod", [f"module example.com/{repo.name}", "", "go 1.22", ""] + [f"require {m} {v}" for m, v in VULN_DEPS["go"]] + [""])
    repo.put("core.go", [f"package {pkg}", "", "import \"errors\"", "", f"func Create{E}({d['@t@']} string, {d['@n@']} int) (string, error) {{",
                         f"\tif {d['@t@']} == \"\" {{", f"\t\treturn \"\", errors.New(\"{d['@t@']} is required\")", "\t}",
                         f"\treturn {d['@t@']}, nil", "}", ""])
    g = [f"package {pkg}", "", "import (", "\t\"fmt\"", "\t\"strings\"", ")", "", "var _ = fmt.Sprintf", "var _ = strings.TrimSpace", ""]
    for i in range(filler):
        g += [f"func Validate{E}{i}(value string) (string, error) {{", "\ttext := strings.TrimSpace(value)", "\tif text == \"\" {", f"\t\treturn \"\", fmt.Errorf(\"{e} field {i} is required\")", "\t}",
              f"\tif len(text) > {20 + i} {{", f"\t\treturn \"\", fmt.Errorf(\"{e} field {i} is too long\")", "\t}", "\treturn text, nil", "}", ""]
    repo.put("helpers.go", g)
    repo.put("rules.go", [f"package {pkg}", "", "import (", "\t\"fmt\"", "\t\"io\"", "\t\"io/ioutil\"", "\t\"strconv\"", "\t\"strings\"", "\t\"time\"", ")", "",
                          "var _ = fmt.Sprintf", "var _ = io.EOF", "var _ = ioutil.ReadAll", "var _ = strconv.Itoa", "var _ = strings.ToUpper", "var _ = time.Now", ""])
    for b in bugs:
        plant(repo, "rules.go", b, d)
    t = [f"package {pkg}", "", "import (", "\t\"math/rand\"", "\t\"testing\"", ")", "", f"func TestCreate{E}(t *testing.T) {{", f"\tgot, err := Create{E}(\"a\", 1)",
         "\tif err != nil || got != \"a\" {", "\t\tt.Fatalf(\"unexpected %v %v\", got, err)", "\t}", "}", ""]
    for i in range(0, filler, 4):
        t += [f"func TestValidate{i}(t *testing.T) {{", f"\tif got, _ := Validate{E}{i}(\" x \"); got != \"x\" {{", "\t\tt.Fatal(got)", "\t}", "}", ""]
    add_flaky(repo, "core_test.go", t, ["func TestJitterStaysInRange(t *testing.T) {", "\tif rand.Float64() >= 0.9 {", "\t\tt.Fatal(\"unlucky\")", "\t}", "}"],
              "assertion on rand.Float64() fails about one run in ten")
    t.append("")
    repo.put("core_test.go", t)


def build_dotnet(repo, rng, filler, bugs):
    d = names(repo.domain); E, e = d["@E@"], d["@e@"]
    ns = "Example." + E
    pk = "\n".join(f'    <PackageReference Include="{n}" Version="{v}" />' for n, v in VULN_DEPS["dotnet"])
    repo.put("App/App.csproj", f"""<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework><Nullable>disable</Nullable><ImplicitUsings>enable</ImplicitUsings><RootNamespace>{ns}</RootNamespace></PropertyGroup>
  <ItemGroup>
{pk}
  </ItemGroup>
</Project>
""".splitlines())
    repo.put("App/Core.cs", [f"namespace {ns};", "", "public static class Core", "{",
                             f"    public static string Create{E}(string {d['@t@']}, int {d['@n@']})", "    {",
                             f"        if (string.IsNullOrEmpty({d['@t@']})) throw new ArgumentException(\"{d['@t@']} is required\");",
                             f"        return {d['@t@']} + \":\" + {d['@n@']};", "    }", "}", ""])
    h = [f"namespace {ns};", "", "public static class Helpers", "{"]
    for i in range(filler):
        h += [f"    public static string Validate{E}{i}(object value)", "    {", f"        if (value == null) throw new ArgumentException(\"{e} field {i} is required\");",
              "        var text = value.ToString().Trim();", f"        if (text.Length > {20 + i}) throw new ArgumentException(\"{e} field {i} is too long\");", "        return text;", "    }", ""]
    h.append("}")
    repo.put("App/Helpers.cs", h + [""])
    repo.put("App/Rules.cs", [f"namespace {ns};", "", "public static class Rules", "{"])
    for b in bugs:
        plant(repo, "App/Rules.cs", b, d, header_gap=False)
        repo.files["App/Rules.cs"].append("")
    repo.append("App/Rules.cs", ["}", ""])
    repo.put("Tests/Tests.csproj", """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup><TargetFramework>net8.0</TargetFramework><ImplicitUsings>enable</ImplicitUsings><IsPackable>false</IsPackable></PropertyGroup>
  <ItemGroup>
    <PackageReference Include="Microsoft.NET.Test.Sdk" Version="17.9.0" />
    <PackageReference Include="xunit" Version="2.7.0" />
    <PackageReference Include="xunit.runner.visualstudio" Version="2.5.7" />
    <PackageReference Include="coverlet.collector" Version="6.0.2" />
  </ItemGroup>
  <ItemGroup><ProjectReference Include="..\\App\\App.csproj" /></ItemGroup>
</Project>
""".splitlines())
    t = [f"using {ns};", "using Xunit;", "", "public class CoreTests", "{", "    [Fact]", f"    public void Create() => Assert.Equal(\"a:1\", Core.Create{E}(\"a\", 1));", ""]
    for i in range(0, filler, 4):
        t += ["    [Fact]", f"    public void Validate{i}() => Assert.Equal(\"x\", Helpers.Validate{E}{i}(\" x \"));", ""]
    add_flaky(repo, "Tests/CoreTests.cs", t, ["    [Fact]", "    public void JitterStaysInRange() => Assert.True(Random.Shared.NextDouble() < 0.9);"],
              "assertion on Random.Shared fails about one run in ten")
    t += ["}", ""]
    repo.put("Tests/CoreTests.cs", t)


BUILDERS = {"python": build_python, "node": build_node, "java": build_java, "go": build_go, "dotnet": build_dotnet}


def write_repo(repo, out_root, keys_dir, git=True):
    root = out_root / repo.name
    if root.exists():
        raise SystemExit(f"{root} already exists; refusing to overwrite (delete it or choose another --out)")
    for path, lines in repo.files.items():
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines).rstrip("\n") + "\n" if lines else "")
    manifest = {"repo": repo.name, "language": repo.lang, "domain": repo.domain, "seed": repo.seed, "generator": "gen/generate.py (fallback, no model)",
                "issues": repo.planted}
    keys_dir.mkdir(parents=True, exist_ok=True)
    (keys_dir / f"{repo.name}.planted-issues.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (root / ".gitignore").write_text("\n".join({"python": [".venv/", "__pycache__/", ".pytest_cache/", ".coverage", "reports/"], "node": ["node_modules/", "reports/"],
                                                "java": ["target/", "reports/"], "go": ["reports/"], "dotnet": ["bin/", "obj/", "reports/", "TestResults/"]}[repo.lang]) + "\n")
    (root / "README.md").write_text(f"# {repo.name}\n\nA {repo.lang} {repo.domain} service from the course capstone."
                                    "\n\n```bash\nbuild.sh build test secure\n```\n")
    if git:
        commit_history(root, repo)
    return root


def commit_history(root, repo):
    env = dict(os.environ, GIT_AUTHOR_NAME="Course Generator", GIT_AUTHOR_EMAIL="generator@example.com",
               GIT_COMMITTER_NAME="Course Generator", GIT_COMMITTER_EMAIL="generator@example.com")

    def git(*args, date=None):
        e = dict(env)
        if date:
            e["GIT_AUTHOR_DATE"] = e["GIT_COMMITTER_DATE"] = date
        subprocess.run(["git", *args], cwd=root, env=e, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    git("init", "-q", "-b", "main")
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and ".git/" not in p.as_posix())
    meta = [f for f in files if f in (".gitignore", "README.md") or f.endswith(("pom.xml", "package.json", "go.mod", ".csproj", "requirements.txt", "requirements-dev.txt", "pytest.ini", ".sln"))]
    tests = [f for f in files if "test" in f.lower() and f not in meta]
    rest = [f for f in files if f not in meta and f not in tests]
    stages = [("Initial project skeleton and dependencies", meta, "2026-01-12T09:00:00+0000"),
              ("Add core logic and helpers", rest, "2026-02-03T14:30:00+0000"),
              ("Add first unit tests", tests, "2026-02-20T11:15:00+0000")]
    for msg, fs, date in stages:
        if fs:
            git("add", "--", *fs)
            git("commit", "-q", "-m", msg, date=date)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default="repos", help="directory to create repos in")
    ap.add_argument("--count", type=int, default=0, help="generate this many repos, cycling through languages and domains")
    ap.add_argument("--lang", choices=LANGS)
    ap.add_argument("--domain", choices=sorted(DOMAINS))
    ap.add_argument("--name")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--filler", type=int, default=24, help="generated helper functions per repo (bulk): about 10 lines each")
    ap.add_argument("--bugs", type=int, default=6, help="planted bugs per repo (plus a secret and a null bug, always, and a flaky test)")
    ap.add_argument("--team-count", type=int, default=4)
    ap.add_argument("--keys-dir", default=None, help="where the answer keys go (default: <out>/../answer-keys); NEVER inside the repos")
    ap.add_argument("--no-git", action="store_true")
    ap.add_argument("--csv", default=None, help="write/append a repos.csv manifest here (default: <out>/../repos.csv when --count is used)")
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    keys_dir = Path(a.keys_dir) if a.keys_dir else out.resolve().parent / "answer-keys"
    jobs = []
    if a.count:
        domains = sorted(DOMAINS)
        for i in range(a.count):
            lang = LANGS[i % len(LANGS)]
            dom = domains[(i * 7 + a.seed) % len(domains)]
            jobs.append((lang, dom, f"{dom}-{SHORT[lang]}-{i + 1:03d}"))
    else:
        if not (a.lang and a.domain):
            ap.error("give --count, or both --lang and --domain")
        jobs.append((a.lang, a.domain, a.name or f"{a.domain}-{a.lang}-001"))
    rows = []
    for idx, (lang, dom, name) in enumerate(jobs):
        rng = random.Random(f"{a.seed}:{name}")
        repo = Repo(name, lang, dom, a.seed)
        BUILDERS[lang](repo, rng, a.filler, pick_bugs(rng, lang, a.bugs))
        root = write_repo(repo, out, keys_dir, git=not a.no_git)
        loc = sum(len(v) for k, v in repo.files.items())
        print(f"{name:28s} {lang:7s} {dom:14s} files={len(repo.files):3d} lines={loc:5d} planted={len(repo.planted)}")
        rows.append({"name": name, "language": lang, "domain": dom, "owner_team": f"team-{chr(97 + idx % a.team_count)}", "path": str(root)})
    csv_path = Path(a.csv) if a.csv else (out.parent / "repos.csv" if a.count else None)
    if csv_path:
        exists = csv_path.exists()
        with csv_path.open("a", newline="") as f:
            w = csv.DictWriter(f, lineterminator="\n", fieldnames=["name", "language", "domain", "owner_team", "path"])
            if not exists:
                w.writeheader()
            w.writerows(rows)
        print(f"wrote {csv_path}")


if __name__ == "__main__":
    main()
