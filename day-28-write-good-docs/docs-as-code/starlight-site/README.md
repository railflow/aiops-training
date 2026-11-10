# Example docs site (Starlight)

The small docs-as-code project that **Day 28** builds, link-checks, containerises and deploys. The course site itself is a Next.js app (`site/`); this example teaches the pattern on Starlight, which is what many teams use for product docs.

- Five pages: a splash home, an overview, an explanation page with a Mermaid diagram, a how-to guide and a reference table.
- Same accent colours and logo as the course.
- `starlight-links-validator` fails the build on a broken internal link or anchor.
- Its own `package.json` and `package-lock.json`: nothing here is shared with `site/`.

```bash
cd day-28-write-good-docs/docs-as-code/starlight-site
npm ci
npm run dev        # http://localhost:4321/
npm run build      # writes dist/ and runs the link check
npm run preview    # serves dist/
```

The image: from the repository root, `docker build -f day-28-write-good-docs/docs-as-code/deploy/Dockerfile -t docs-site:1.0 .` (multi-stage, Node to build, unprivileged nginx on 8080 to serve). `bash day-28-write-good-docs/docs-as-code/tests/test-docs-image-context.sh` checks the build path without Docker; `REAL_DOCKER=1` also runs the real build.
