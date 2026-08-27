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
    <li><img src="../assets/theme-default.png" alt="Preview of the default theme"><code>default</code><span>Warm editorial serif</span></li>
    <li><img src="../assets/theme-dark.png" alt="Preview of the dark theme"><code>dark</code><span>Polished dark docs</span></li>
    <li><img src="../assets/theme-developer.png" alt="Preview of the developer theme"><code>developer</code><span>Developer-blog dark layout</span></li>
    <li><img src="../assets/theme-gridline.png" alt="Preview of the gridline theme"><code>gridline</code><span>Blue-black technical notebook</span></li>
    <li><img src="../assets/theme-matrix.png" alt="Preview of the matrix theme"><code>matrix</code><span>Neon green terminal atmosphere</span></li>
    <li><img src="../assets/theme-minimal.png" alt="Preview of the minimal theme"><code>minimal</code><span>Stripped-back monochrome writing</span></li>
    <li><img src="../assets/theme-pulsar.png" alt="Preview of the pulsar theme"><code>pulsar</code><span>Moody dark product-blog cards</span></li>
    <li><img src="../assets/theme-retro.png" alt="Preview of the retro theme"><code>retro</code><span>Amber terminal paper</span></li>
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
