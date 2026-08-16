# Theming

In v1, a theme is primarily a CSS file.

## Default behavior

If no custom theme is provided, `mkpages` writes a bundled default stylesheet
to `assets/site.css`.

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
mkpages docs/ --output .mkpages
```

uses `docs/theme.css`.

## Override with `--theme`

If there is no `theme.css` at the content root, you can pass a CSS file
explicitly:

```bash
mkpages docs/ --theme ./themes/my-site.css
```

See [CLI Reference](cli-reference.md) for the full option summary.
