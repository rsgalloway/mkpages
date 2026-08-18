# CLI Reference

## Synopsis

```bash
mkpages build [PATH] [--output .mkpages] [--theme NAME_OR_PATH]
mkpages serve [--output .mkpages] [--host 127.0.0.1] [--port 4000]
mkpages preview [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--host 127.0.0.1] [--port 4000]
mkpages [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--host 127.0.0.1] [--port 4000]
```

## Arguments

### `PATH`

For `mkpages build` and `mkpages preview`, `PATH` is optional and defaults to
the current directory.

## Options

### `--output`

Choose the generated Jekyll source directory. The default is `.mkpages`.

`--output` applies to `mkpages build`, `mkpages serve`, and `mkpages preview`.

### `--theme`

Provide either a bundled theme name or a CSS file path to use as the generated
site stylesheet.

Theme precedence is:

1. `theme.css` at the content root
2. `--theme NAME_OR_PATH`
3. `theme: NAME_OR_PATH` in `mkpages.yml`
4. bundled default theme

Bundled themes:

- `default`
- `dark`
- `developer`
- `matrix`
- `minimal`
- `pulsar`
- `retro`

### `mkpages.yml`

The optional `mkpages.yml` file at the content root can set site-wide values
such as:

- `title`
- `description`
- `theme`
- `favicon`
- `navigation`

`favicon` should be a relative path inside the content root, for example
`assets/favicon.png`. `mkpages` copies that file through and adds a favicon
link tag to the generated layout.

### `serve`

Launch `jekyll serve` against the existing `.mkpages` output directory.

`mkpages serve` does not rebuild the site. Run `mkpages build` first.

When possible, `mkpages serve` also opens the preview URL in your default web
browser automatically.

This subcommand requires the `jekyll` executable to be installed and available
on `PATH`.

### `preview`

Build the chosen content root into `.mkpages` and immediately serve it through
Jekyll.

`mkpages preview` accepts the same build options as `mkpages build`, including
`--theme`, plus the same `--host` and `--port` options as `mkpages serve`.

### Bare `PATH`

If the first argument is not a known subcommand, `mkpages` treats it as a
shortcut for `mkpages preview PATH`.

### `serve --host`

Choose the bind host for the Jekyll preview server. The default is
`127.0.0.1`.

### `serve --port`

Choose the port for the Jekyll preview server. The default is `4000`.

### `build`

Generate a Jekyll source tree from the chosen content root.

`mkpages build` defaults to building into `.mkpages`.

Hidden files and hidden directories under the content root are ignored by
default.

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

Preview the generated site locally in one step:

```bash
mkpages preview docs/ --theme dark
```

Use the bare-path shortcut:

```bash
mkpages docs/ --theme dark
```

Or preview an existing generated site without rebuilding:

```bash
mkpages build docs/
mkpages serve --port 5000
```
