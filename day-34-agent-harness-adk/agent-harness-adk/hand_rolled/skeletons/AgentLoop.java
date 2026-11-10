import java.util.*;
import java.util.concurrent.*;

/** The agent loop of one Job in Java. Same cases as agent_loop.py, minus JSON and HTTP plumbing (use Jackson and java.net.http). Compile check: javac AgentLoop.java */
public class AgentLoop {
    record Call(String name, Map<String, Object> args) {}
    record Reply(String text, List<Call> calls, String error, double costUsd) {}
    record Message(String role, String text, Call call, Map<String, Object> result) {}

    static class RateLimited extends RuntimeException { final long retryAfterMs; RateLimited(long ms) { retryAfterMs = ms; } }

    interface Model { Reply complete(List<Message> history) throws RateLimited; }
    interface Tool { Map<String, Object> run(Map<String, Object> args) throws Exception; }

    final Model model;
    final Map<String, Tool> tools;
    final int maxSteps = 30;
    final double budgetUsd = 0.25;
    final long stepTimeoutMs = 120_000, jobDeadlineMs = 900_000;
    final ExecutorService pool = Executors.newCachedThreadPool(r -> { Thread t = new Thread(r); t.setDaemon(true); return t; });
    volatile boolean cancelled;

    AgentLoop(Model model, Map<String, Tool> tools) {
        this.model = model;
        this.tools = tools;
        Runtime.getRuntime().addShutdownHook(new Thread(() -> cancelled = true)); // Kubernetes sends SIGTERM, then waits terminationGracePeriodSeconds
    }

    Reply completeWithBackoff(List<Message> history) throws InterruptedException {
        for (int n = 0; ; n++) {
            try {
                return model.complete(history);
            } catch (RateLimited e) {
                if (n == 5) throw new IllegalStateException("model unavailable"); // map to a retryable exit code
                Thread.sleep(Math.max(e.retryAfterMs, (long) (Math.min(30_000, 500L << n) * (0.5 + Math.random() / 2))));
            }
        }
    }

    Map<String, Object> dispatch(Call call) {
        Tool tool = tools.get(call.name());
        if (tool == null) return Map.of("error", "unknown tool " + call.name() + "; tools are " + tools.keySet());
        Future<Map<String, Object>> f = pool.submit(() -> tool.run(call.args()));
        try {
            return f.get(stepTimeoutMs, TimeUnit.MILLISECONDS);
        } catch (TimeoutException e) {
            f.cancel(true);
            return Map.of("error", call.name() + " timed out");
        } catch (Exception e) {
            return Map.of("error", String.valueOf(e.getCause() != null ? e.getCause() : e)); // a tool bug becomes a message, not a crash
        }
    }

    String run(List<Message> history) throws InterruptedException {
        long deadline = System.currentTimeMillis() + jobDeadlineMs;
        double spent = 0;
        int malformed = 0;
        Deque<String> recent = new ArrayDeque<>();
        for (int step = 0; ; step++) {
            if (cancelled) return "cancelled";
            if (step >= maxSteps) return "max_steps";
            if (spent >= budgetUsd) return "budget_exhausted";
            if (System.currentTimeMillis() > deadline) return "deadline";
            Reply reply = completeWithBackoff(compact(history));
            spent += reply.costUsd();
            if (reply.error() != null) {
                if (++malformed >= 3) return "malformed_output";
                history.add(new Message("user", "Your last reply was rejected: " + reply.error(), null, null));
                continue;
            }
            if (reply.calls().isEmpty()) return "done";
            Call call = reply.calls().get(0);
            history.add(new Message("assistant", reply.text(), call, null));
            history.add(new Message("tool", null, call, dispatch(call)));
            recent.addLast(call.name() + call.args());
            if (recent.size() > 3) recent.removeFirst();
            if (recent.size() == 3 && new HashSet<>(recent).size() == 1) return "stuck_loop";
            checkpoint(history); // write to a volume that outlives the pod, then rename: a crash must not leave half a file
        }
    }

    List<Message> compact(List<Message> history) { return history; } // elide old tool results once the context nears the limit
    void checkpoint(List<Message> history) { /* serialise history and counters to /state/<repo>.json atomically */ }

    public static void main(String[] args) throws Exception {
        Model scripted = h -> new Reply("done", List.of(), null, 0.001);
        System.out.println(new AgentLoop(scripted, Map.of()).run(new ArrayList<>()));
    }
}
