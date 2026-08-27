<div class="gridline-home-hero">
  <img src="logo.svg" alt="mkpages logo" width="500">
  <p><code>mkpages</code> turns an existing Markdown folder tree into a generated Jekyll source tree.</p>
  <pre class="gridline-install-command"><code>pip install -U mkpages</code></pre>
</div>

It is designed to be a thin wrapper around Jekyll rather than a new static site
generator. Markdown stays as content, folders stay as structure, and CSS stays
as presentation.

## Why it exists

Many repositories already have useful documentation, notes, or content in
plain `.md` files. `mkpages` helps publish that material through Jekyll and
GitHub Pages without forcing the repository into a Jekyll-first layout.

:::cards columns=3 panel=true title="What it does"
- **Discovers Markdown**: Finds files under the chosen content root.
- **Preserves structure**: Keeps the source folder hierarchy intact.
- **Rewrites local links**: Converts Markdown links to generated pretty routes.
- **Copies assets**: Carries non-Markdown files into the generated site.
- **Adds front matter**: Injects the minimal Jekyll metadata when needed.
- **Builds the shell**: Writes the layout, config, includes, and stylesheet.
:::

<section class="card-panel gridline-start-here">
  <header class="card-panel-header">
    <h2 class="card-panel-title">Start here</h2>
  </header>
  <ul>
    <li><a href="getting-started/">Getting Started</a></li>
    <li><a href="cli/">CLI Reference</a></li>
    <li><a href="routing/">Routing Rules</a></li>
    <li><a href="theming/">Theming</a></li>
    <li><a href="front-matter/">Front Matter</a></li>
    <li><a href="github-pages/">GitHub Pages</a></li>
  </ul>
</section>

## Dogfooding

This documentation is intentionally written under `docs/` so `mkpages` can
generate its own site:

```bash
mkpages build docs/
```

For local preview through Jekyll:

```bash
mkpages preview docs/
```
