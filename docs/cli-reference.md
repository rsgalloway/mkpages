# CLI Reference

## Synopsis

```bash
mkpages build [PATH] [--output .mkpages] [--theme PATH]
mkpages serve [--host 127.0.0.1] [--port 4000]
```

## Arguments

### `PATH`

For `mkpages build`, `PATH` is optional and defaults to the current directory.

## Options

### `--output`

Choose the generated Jekyll source directory. The default is `.mkpages`.

`--output` applies to `mkpages build`.

### `--theme`

Provide either a bundled theme name or a CSS file path to use as the generated
site stylesheet.

Theme precedence is:

1. `theme.css` at the content root
2. `--theme NAME_OR_PATH`
3. bundled default theme

Bundled themes:

- `default`
- `dark`
- `minimal`

### `serve`

Launch `jekyll serve` against the existing `.mkpages` output directory.

`mkpages serve` does not rebuild the site. Run `mkpages build` first.

When possible, `mkpages serve` also opens the preview URL in your default web
browser automatically.

This subcommand requires the `jekyll` executable to be installed and available
on `PATH`.

### `serve --host`

Choose the bind host for the Jekyll preview server. The default is
`127.0.0.1`.

### `serve --port`

Choose the port for the Jekyll preview server. The default is `4000`.

### `build`

Generate a Jekyll source tree from the chosen content root.

`mkpages build` defaults to building into `.mkpages`.

## Examples

Generate a site from the repository root:

```bash
mkpages build
```

Generate a site from `docs/`:

```bash
mkpages build docs/
```

Use an explicit theme:

```bash
mkpages build docs/ --output .mkpages --theme ./custom.css
```

Use a bundled dark theme:

```bash
mkpages build docs/ --theme dark
```

Preview the generated site locally through Jekyll:

```bash
mkpages build docs/
mkpages serve --port 5000
```
