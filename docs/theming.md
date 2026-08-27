# Theming

In v1, a theme is primarily a CSS file.

## Default behavior

If no custom theme is provided, `mkpages` writes the bundled `default`
stylesheet to `assets/site.css`.

`mkpages` currently ships with:

<section class="card-panel gridline-theme-list">
  <header class="card-panel-header">
    <h2 class="card-panel-title">Bundled themes</h2>
  </header>
  <ul>
    <li><code>default</code><span>Warm editorial serif</span></li>
    <li><code>dark</code><span>Polished dark docs</span></li>
    <li><code>developer</code><span>Developer-blog dark layout</span></li>
    <li><code>gridline</code><span>Blue-black technical notebook</span></li>
    <li><code>matrix</code><span>Neon green terminal atmosphere</span></li>
    <li><code>minimal</code><span>Stripped-back monochrome writing</span></li>
    <li><code>pulsar</code><span>Moody dark product-blog cards</span></li>
    <li><code>retro</code><span>Amber terminal paper</span></li>
  </ul>
</section>

Select one with:

```bash
mkpages build docs/ --theme dark
mkpages build docs/ --theme minimal
mkpages build docs/ --theme retro
```

You can also set a bundled theme in `mkpages.yml`:

```yaml
theme: dark
```

This is useful when you want the content root itself to stay just Markdown plus
configuration.

## Override with `theme.css`

If the content root contains `theme.css`, that file wins automatically.

Example tree:

```text
docs/
  index.md
  theme.css
```

Then:

```bash
mkpages build docs/ --output .mkpages
```

uses `docs/theme.css`.

## Override with `--theme`

If there is no `theme.css` at the content root, you can pass either a bundled
theme name or a CSS file path explicitly:

```bash
mkpages build docs/ --theme ./themes/my-site.css
```

See [CLI Reference](cli/index.md) for the full option summary.
