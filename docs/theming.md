# Theming

In v1, a theme is primarily a CSS file.

## Default behavior

If no custom theme is provided, `mkpages` writes the bundled `default`
stylesheet to `assets/site.css`.

## Bundled themes

`mkpages` currently ships with:

- `default`
- `dark`
- `minimal`

Select one with:

```bash
mkpages build docs/ --theme dark
mkpages build docs/ --theme minimal
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

See [CLI Reference](cli-reference.md) for the full option summary.
