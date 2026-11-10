// Crash lab: the same coverage agent, with the process killed at awkward moments.
//   node lab/crash-lab.mjs plain            # a plain in-memory loop (no Eve): dies and starts over
//   node lab/crash-lab.mjs eve-parked ...   # Eve (real `eve start`, local world, scripted model): resumes
// Each scenario prints what happened and asserts it, so a non-zero exit means the story did not hold.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { setTimeout as sleep } from "node:timers/promises";
import { ROOT, Server, assert, count, forge, ledger, newLabDir, registeredSleeps, resetWorkflowData, say } from "./lib.mjs";

const PORT = 3121;
const TASK = (repo, plan = "full") => `Improve test coverage. plan=${plan} repo=${repo}`;
const section = (title) => say(`\n=== ${title} ===`);

function runPlain(dir, repo, env = {}) {
  return new Promise((resolve) => {
    const child = spawn(process.execPath, [join(ROOT, "plain", "plain-loop.ts"), repo], {
      env: { ...process.env, LAB_DIR: dir, LAB_APPROVAL_WAIT_MS: "8000", ...env }, stdio: ["ignore", "pipe", "pipe"],
    });
    let out = "";
    child.stdout.on("data", (d) => (out += d));
    child.on("exit", (code) => resolve({ code, out: out.trim() }));
  });
}

function approvePlain(dir, repo) {
  mkdirSync(join(dir, "approvals"), { recursive: true });
  writeFileSync(join(dir, "approvals", repo), "approved");
}

async function plain() {
  section("PLAIN LOOP: a person approved the pull request, then the process died before it ran");
  let dir = newLabDir("plain");
  approvePlain(dir, "billing-001");
  let r = await runPlain(dir, "billing-001", { LAB_DIE_AT: "open_pr:before" });
  say(`  run 1: exit ${r.code ?? "killed by SIGKILL"}; the approval was consumed: approval_consumed x${count(dir, "approval_consumed")}`);
  r = await runPlain(dir, "billing-001", { LAB_APPROVAL_WAIT_MS: "2000" });
  say(`  run 2 (restart): exit ${r.code}; it redid the work and is asking again: approval_requested x${count(dir, "approval_requested")}`);
  approvePlain(dir, "billing-001");
  r = await runPlain(dir, "billing-001");
  say(`  run 3 (second click): exit ${r.code}: ${r.out}`);
  assert(count(dir, "done", "run_tests") === 6, "run_tests finished 6 times for 2 needed: every restart began at step 1");
  assert(count(dir, "done", "write_test_file") === 3, "the test file was written 3 times");
  assert(count(dir, "approval_requested") === 3, "the human was asked three times for one pull request");
  assert(forge(dir).length === 1, "(one pull request, only because this tool is idempotent)");

  section("PLAIN LOOP: crash after the pull request was created, with a non-idempotent tool");
  dir = newLabDir("plain-pr");
  approvePlain(dir, "billing-002");
  await runPlain(dir, "billing-002", { LAB_DIE_AT: "open_pr:after", LAB_NO_IDEMPOTENCY: "1" });
  approvePlain(dir, "billing-002");
  await runPlain(dir, "billing-002", { LAB_NO_IDEMPOTENCY: "1" });
  say(`  pull requests in the forge: ${forge(dir).length}`);
  assert(forge(dir).length === 2, "two pull requests for one repository");
}

async function withServer(name, env, fn) {
  resetWorkflowData();
  const dir = newLabDir(name);
  const server = new Server(PORT, { LAB_DIR: dir, ...env });
  try {
    await server.start();
    await fn(server, dir, async (extraEnv = {}) => {
      server.env = { ...server.env, ...extraEnv };
      await server.start();
    });
  } finally {
    server.kill9();
  }
}

async function eveParked() {
  section("EVE, killed while parked at the approval gate");
  await withServer("parked", { LAB_STEP_MS: "200" }, async (server, dir, restart) => {
    const sid = await server.createSession(TASK("billing-001"));
    const s = await server.waitFor(sid, (st) => st.open.length > 0);
    say(`  session ${sid.slice(0, 18)}... is parked on approval ${s.open[0].interactionId}`);
    say(`  ledger before the kill: ${ledger(dir).filter((e) => e.event === "done").map((e) => e.tool).join(", ")}`);
    server.kill9();
    say("  kill -9 on the whole server process group");
    await sleep(500);
    await restart();
    say("  server restarted (new process)");
    const after = await server.state(sid);
    assert(after.open.length === 1 && after.open[0].interactionId === s.open[0].interactionId, "the same approval request is still open after the restart");
    await server.approve(sid, s.open[0].interactionId);
    const end = await server.waitFor(sid, (st) => st.done);
    say(`  reply: ${end.reply}`);
    assert(count(dir, "done", "run_tests") === 2 && count(dir, "done", "write_test_file") === 1, "no finished step ran again");
    assert(forge(dir).length === 1, "one pull request");
    const pids = new Set(ledger(dir).map((e) => e.pid));
    assert(pids.size === 2, "the steps ran in two different processes (before and after the kill)");
  });
}

async function eveStepCrash() {
  section("EVE, process dies in the middle of a tool call (after its effect, before the step was saved)");
  await withServer("step", { LAB_STEP_MS: "200", LAB_DIE_AT: "write_test_file:after" }, async (server, dir, restart) => {
    const sid = await server.createSession(TASK("billing-002"));
    assert(await server.waitForDeath(), "the server killed itself inside write_test_file");
    await restart({ LAB_DIE_AT: "" });
    const s = await server.waitFor(sid, (st) => st.open.length > 0);
    const interrupted = s.facts.filter((f) => f.type === "call.settled" && f.data.outcome === "abandoned");
    say(`  the interrupted call was recorded as: ${JSON.stringify(interrupted.map((f) => f.data))}`);
    say(`  write_test_file started ${count(dir, "start", "write_test_file")}x, finished ${count(dir, "done", "write_test_file")}x`);
    assert(interrupted.length === 1, "eve recorded the interrupted call as abandoned (step-interrupted)");
    assert(count(dir, "done", "run_tests") === 2 && count(dir, "done", "git_commit") === 1, "the steps before and after it ran once each");
    assert(count(dir, "start", "write_test_file") === 2, "the tool call ran again: eve told the model the call may not have taken effect, and the model repeated it");
    await server.approve(sid, s.open[0].interactionId);
    await server.waitFor(sid, (st) => st.done);
    assert(forge(dir).length === 1, "one pull request, because write_test_file is idempotent");
  });
}

async function evePrCrash() {
  for (const naive of [false, true]) {
    section(`EVE, process dies right after the pull request was created (${naive ? "NAIVE tool, no dedupe" : "idempotent tool"})`);
    await withServer(`pr-${naive}`, { LAB_STEP_MS: "100", LAB_DIE_AT: "open_pr:after", ...(naive ? { LAB_NO_IDEMPOTENCY: "1" } : {}) }, async (server, dir, restart) => {
      const sid = await server.createSession(TASK("billing-003"));
      let s = await server.waitFor(sid, (st) => st.open.length > 0);
      await server.approve(sid, s.open[0].interactionId);
      assert(await server.waitForDeath(), "the server died inside open_pr, after the forge call");
      say(`  pull requests so far: ${forge(dir).length}`);
      await restart({ LAB_DIE_AT: "" });
      for (let i = 0; i < 5; i++) {
        s = await server.waitFor(sid, (st) => st.done || st.open.length > 0);
        if (s.done) break;
        say(`  eve asks for approval again (${s.open[0].interactionId}); the model wants to repeat the call. Approving.`);
        await server.approve(sid, s.open[0].interactionId);
        await sleep(800);
      }
      say(`  reply: ${s.reply}; pull requests in the forge: ${forge(dir).length}`);
      assert(forge(dir).length === (naive ? 2 : 1), naive ? "TWO pull requests: durability did not make the naive tool exactly-once" : "ONE pull request: the stable key made the repeat harmless");
    });
  }
}

async function eveSleep() {
  section("EVE workflow tool: retries with a delay, then a durable sleep that spans a kill -9");
  await withServer("sleep", { LAB_SLEEP: "12s" }, async (server, dir, restart) => {
    const t0 = Date.now();
    const sid = await server.createSession(TASK("ci-001", "ci"));
    for (let i = 0; i < 100 && count(dir, "ci_query_attempt", undefined, "ci-001") < 3; i++) await sleep(200);
    assert(count(dir, "ci_query_attempt", undefined, "ci-001") === 3, "the step failed twice with RetryableError and succeeded on attempt 3");
    for (let i = 0; i < 100 && registeredSleeps() === 0; i++) await sleep(100);
    assert(registeredSleeps() === 1, "the 12 s sleep is registered as a durable wait in the workflow store");
    server.kill9();
    say(`  kill -9 at +${((Date.now() - t0) / 1000).toFixed(1)}s, during the 12 s sleep; waiting 14 s with the server dead`);
    await sleep(14000);
    await restart();
    const t1 = Date.now();
    const s = await server.waitFor(sid, (st) => st.done, 30000);
    say(`  restarted; the run finished ${((Date.now() - t1) / 1000).toFixed(1)}s after the restart. reply: ${s.reply}`);
    assert(Date.now() - t1 < 8000, "the timer had already elapsed while the process was dead, so the run continued at once");
    assert(count(dir, "ci_query_attempt") === 3, "the first step did not run again after the restart");
    assert(count(dir, "ci_final_read") === 1, "the step after the sleep ran once, in the new process");
  });
}

async function eveFanout() {
  section("EVE fan-out: 8 repositories, concurrency 4, kill -9 mid-run, one repository fails for good");
  const repos = Array.from({ length: 8 }, (_, i) => `repo-${String(i + 1).padStart(3, "0")}`);
  await withServer("fanout", { LAB_STEP_MS: "400", LAB_FAIL_REPO: "repo-005" }, async (server, dir, restart) => {
    const sessions = new Map();
    const start = async (repo) => sessions.set(repo, await server.createSession(TASK(repo)));
    const queue = [...repos];
    let killed = false;
    const results = new Map();
    const tick = async () => {
      const running = [...sessions.keys()].filter((r) => !results.has(r));
      while (running.length < 4 && queue.length) { const repo = queue.shift(); await start(repo); running.push(repo); }
      for (const repo of running) {
        const s = await server.state(sessions.get(repo));
        if (s.open.length) await server.approve(sessions.get(repo), s.open[0].interactionId);
        if (s.done) results.set(repo, s.reply ?? "(no reply)");
      }
    };
    while (results.size < repos.length) {
      await tick();
      if (!killed && count(dir, "done", "git_commit") >= 2 && count(dir, "done") >= 10) {
        killed = true;
        say(`  kill -9 with ${results.size} sessions finished, ${sessions.size - results.size} in flight (${ledger(dir).filter((e) => e.event === "done").length} tool steps done so far), ${queue.length} repositories not started`);
        server.kill9();
        await sleep(500);
        await restart();
        say("  server restarted; the orchestrator did nothing special: it keeps polling the same session ids");
      }
      await sleep(300);
    }
    for (const [repo, reply] of results) say(`  ${repo}: ${reply}`);
    const failed = [...results].filter(([, r]) => r.startsWith("FAILED")).map(([r]) => r);
    assert(failed.length === 1 && failed[0] === "repo-005", "partial failure: exactly the injected repository failed");
    assert(forge(dir).length === 7, "7 pull requests, one per healthy repository, none duplicated");
    assert(repos.filter((r) => r !== "repo-005").every((r) => count(dir, "done", "git_commit", r) === 1), "every healthy repository was committed exactly once");
  });
}

const scenarios = { plain, "eve-parked": eveParked, "eve-step-crash": eveStepCrash, "eve-pr-crash": evePrCrash, "eve-sleep": eveSleep, "eve-fanout": eveFanout };
const wanted = process.argv.slice(2);
const names = wanted.length === 0 || wanted[0] === "all" ? Object.keys(scenarios) : wanted;
let failed = 0;
for (const name of names) {
  if (!scenarios[name]) { say(`unknown scenario ${name}; choose from ${Object.keys(scenarios).join(", ")}`); process.exit(2); }
  try { await scenarios[name](); } catch (e) { failed++; say(`  ${e.message}`); }
}
say(failed ? `\n${failed} scenario(s) FAILED` : "\nall scenarios held");
process.exit(failed ? 1 : 0);
