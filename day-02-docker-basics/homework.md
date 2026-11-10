# Day 2: Docker basics: homework

Assignment text only. Hints, model answers, grading rubrics and graded-exercise data are not part of this repository.

Work in `~/heyjob-labs/day02/`. Commit after each exercise.

```bash
mkdir -p ~/heyjob-labs/day02 && cd ~/heyjob-labs/day02
cp -r ~/aiops-training/day-02-docker-basics/python-hello ~/aiops-training/day-02-docker-basics/java-hello ~/aiops-training/day-02-docker-basics/go-hello .
```

### Exercise 1: Container lifecycle log

**Do:** with `nginx:1.27`, run a container `hw-web` on host port 8090 and record commands and outputs in `lifecycle.md`: start and `curl`; read logs; `docker exec` in and edit `/usr/share/nginx/html/index.html` to say `Hello <your name>`; `docker stop` then `docker start` and `curl`; `docker rm -f`, run again and `curl`; finally repeat with a **bind mount** (`-v "$(pwd)/site:/usr/share/nginx/html:ro"`) so the page survives removal.

**Deliverable:** `lifecycle.md` plus a 3-sentence explanation of why the edit survived `stop/start` but not `rm`.

### Exercise 2: Three images, compared

**Do:** build all four images (`hello-py:1.0`, `hello-java:1.0`, `hello-java:jlink`, `hello-go:1.0`) and make `sizes.md`, a table with image, size, layer count (`docker history IMAGE | wc -l` minus header), and "has a shell?".

**Deliverable:** `sizes.md` with real numbers plus a paragraph: which image is smallest and why, what did you give up, which would you choose for a production Go service.

### Exercise 3: Break and observe the build cache

**Do:** in your `python-hello` copy: (1) build `hello-py:cache1` twice and save the second log; (2) edit `hello.py` and rebuild as `cache2`; (3) add `RUN pip install --no-cache-dir flask==3.0.3` **above** `COPY hello.py .`, change `hello.py`, rebuild; then move the install **below** `COPY` and repeat. Compare times.

**Deliverable:** `cache.md` with trimmed logs and the rule you found, in your own words.

### Exercise 4: Registries

**Do:** start `registry:2`, tag and push `hello-go:1.0` and `hello-py:1.0` to it, prove it with `curl localhost:5000/v2/_catalog`; push `hello-py:1.0` to **your** Docker Hub account; delete the local copies and `docker pull` them back from each registry.

**Deliverable:** `registry.md` with commands, the catalog and tag-list output, and your Docker Hub repo URL.
