# bad-script: what not to build

`month_end.py` is a five-step batch with a hand-rolled retry loop and a state file. Day 27 uses it to show what is lost when the process dies.

```bash
STEP_SECONDS=1 python3 month_end.py BATCH-2026-11      # let it start, then press Ctrl+C (or kill it) while step 4 prints "sent to ..."
cat outbox.log                                          # who got an email so far
STEP_SECONDS=1 python3 month_end.py BATCH-2026-11      # restart: step 4 starts again from customer 1
sort outbox.log | uniq -d                               # the duplicates: customers who were emailed twice
rm -f state.json outbox.log                            # reset
```
