---
title: Overview
description: What this example site is and how its pages are organised (Diataxis).
---

This is the **example docs site** for Day 28 of the course. The course site itself is a Next.js app; this small Starlight project exists to teach the docs-as-code pattern: Markdown in git, a build in CI, a link check, and a container served by nginx.

## Organisation

Pages follow the four kinds of documentation from [Diátaxis](https://diataxis.fr/):

| Kind | Where | Example |
|---|---|---|
| Tutorial | `start/` | This page |
| How-to guide | `how-to/` | [Roll back a deploy](/how-to/roll-back-a-deploy/) |
| Reference | `reference/` | [Service reference](/reference/service-reference/) |
| Explanation | `start/` | [Why docs live in git](/start/why-docs-as-code/) |

## Add a page

Create a `.md` or `.mdx` file under one of the folders. The sidebar uses `autogenerate`, so **adding a file adds a page**; `sidebar.order` in the front matter sorts it.

```bash
npm run dev      # http://localhost:4321/
npm run build    # production build, includes the link check
```
