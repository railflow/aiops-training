// The agent loop of one Job in Go. Same cases as agent_loop.py, minus JSON and HTTP plumbing (encoding/json and net/http cover both).
// Compile check: go vet ./... in this folder (needs a go.mod; see the README).
package main

import (
	"context"
	"errors"
	"fmt"
	"math/rand"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type Call struct {
	Name string
	Args map[string]any
}
type Reply struct {
	Text    string
	Calls   []Call
	Err     string
	CostUSD float64
}
type Message struct {
	Role, Text string
	Call       *Call
	Result     map[string]any
}

var ErrRateLimited = errors.New("429 too many requests")

type Model interface {
	Complete(ctx context.Context, history []Message) (Reply, error)
}
type Tool func(ctx context.Context, args map[string]any) (map[string]any, error)

const (
	maxSteps      = 30
	budgetUSD     = 0.25
	stepTimeout   = 120 * time.Second
	jobDeadline   = 15 * time.Minute
	maxMalformed  = 3
	maxModelTries = 6
)

func completeWithBackoff(ctx context.Context, m Model, h []Message) (Reply, error) {
	for n := 0; ; n++ {
		r, err := m.Complete(ctx, h)
		if !errors.Is(err, ErrRateLimited) {
			return r, err
		}
		if n == maxModelTries-1 {
			return Reply{}, errors.New("model unavailable") // map to a retryable exit code
		}
		wait := time.Duration(float64(min(30*time.Second, 500*time.Millisecond<<n)) * (0.5 + rand.Float64()/2))
		select {
		case <-time.After(wait):
		case <-ctx.Done():
			return Reply{}, ctx.Err()
		}
	}
}

func dispatch(ctx context.Context, tools map[string]Tool, c Call) map[string]any {
	t, ok := tools[c.Name]
	if !ok {
		return map[string]any{"error": "unknown tool " + c.Name}
	}
	ctx, cancel := context.WithTimeout(ctx, stepTimeout)
	defer cancel()
	out := make(chan map[string]any, 1)
	go func() {
		defer func() { // a panicking tool must not kill the loop
			if r := recover(); r != nil {
				out <- map[string]any{"error": fmt.Sprint(r)}
			}
		}()
		res, err := t(ctx, c.Args)
		if err != nil {
			res = map[string]any{"error": err.Error()}
		}
		out <- res
	}()
	select {
	case res := <-out:
		return res
	case <-ctx.Done():
		return map[string]any{"error": c.Name + " timed out"}
	}
}

func run(ctx context.Context, m Model, tools map[string]Tool, history []Message) string {
	ctx, stop := signal.NotifyContext(ctx, syscall.SIGTERM) // Kubernetes sends SIGTERM, then waits terminationGracePeriodSeconds
	defer stop()
	ctx, cancel := context.WithTimeout(ctx, jobDeadline)
	defer cancel()
	spent, malformed := 0.0, 0
	var recent []string
	for step := 0; ; step++ {
		switch {
		case ctx.Err() != nil:
			return "cancelled_or_deadline"
		case step >= maxSteps:
			return "max_steps"
		case spent >= budgetUSD:
			return "budget_exhausted"
		}
		reply, err := completeWithBackoff(ctx, m, compact(history))
		if err != nil {
			return "retryable"
		}
		spent += reply.CostUSD
		if reply.Err != "" {
			if malformed++; malformed >= maxMalformed {
				return "malformed_output"
			}
			history = append(history, Message{Role: "user", Text: "Your last reply was rejected: " + reply.Err})
			continue
		}
		if len(reply.Calls) == 0 {
			return "done"
		}
		call := reply.Calls[0]
		history = append(history, Message{Role: "assistant", Text: reply.Text, Call: &call}, Message{Role: "tool", Call: &call, Result: dispatch(ctx, tools, call)})
		recent = append(recent, fmt.Sprint(call))
		if len(recent) > 3 {
			recent = recent[1:]
		}
		if len(recent) == 3 && recent[0] == recent[1] && recent[1] == recent[2] {
			return "stuck_loop"
		}
		checkpoint(history) // write to a volume that outlives the pod, then rename: a crash must not leave half a file
	}
}

func compact(h []Message) []Message { return h } // elide old tool results once the context nears the limit
func checkpoint(h []Message)        {}           // serialise history and counters to /state/<repo>.json atomically

type scripted struct{}

func (scripted) Complete(context.Context, []Message) (Reply, error) { return Reply{Text: "done"}, nil }

func main() {
	fmt.Fprintln(os.Stdout, run(context.Background(), scripted{}, nil, nil))
}
