# mkpages

`mkpages` turns an existing Markdown folder tree into a generated Jekyll source
tree.

It is designed to be a thin wrapper around Jekyll rather than a new static site
generator. Markdown stays as content, folders stay as structure, and CSS stays
as presentation.

## Why it exists

Many repositories already have useful documentation, notes, or content in
plain `.md` files. `mkpages` helps publish that material through Jekyll and
GitHub Pages without forcing the repository into a Jekyll-first layout.

## What it does

- Discovers Markdown files under a chosen content root
- Preserves folder structure relative to that root
- Rewrites local Markdown links to generated pretty routes
- Copies non-Markdown assets through to the generated site
- Injects minimal front matter where needed
- Writes a small Jekyll layout, config, includes, and stylesheet

## Start here

- [Getting Started](getting-started.md)
- [CLI Reference](cli-reference.md)
- [Routing Rules](routing.md)
- [Theming](theming.md)
- [GitHub Pages](github-pages.md)

## Dogfooding

This documentation is intentionally written under `docs/` so `mkpages` can
generate its own site:

```bash
mkpages build docs/
```

For local preview through Jekyll:

```bash
mkpages build docs/
mkpages serve
```
