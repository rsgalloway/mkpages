# CLI Reference

## Synopsis

```bash
mkpages build [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--url URL] [--baseurl PATH]
mkpages export [PATH] --output OUTPUT_FILE [--format {docx,pdf,zip}]
mkpages serve [--output .mkpages] [--host 127.0.0.1] [--port 4000]
mkpages preview [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--url URL] [--baseurl PATH] [--host 127.0.0.1] [--port 4000]
mkpages [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--url URL] [--baseurl PATH] [--host 127.0.0.1] [--port 4000]
```

## Commands

- [build](build.md): Generate a Jekyll source tree from a Markdown folder tree.
- [serve](serve.md): Serve an existing generated site through Jekyll.
- [preview](preview.md): Build, watch, and serve a Markdown folder tree.
- [export](export.md): Create a PDF, DOCX, or rendered static site ZIP.

A bare content path is a shortcut for `mkpages preview PATH`. See
[preview](preview.md) for details.

## Shared arguments

### `PATH`

For `mkpages build` and `mkpages preview`, `PATH` is optional and defaults to
the current directory.

For `mkpages export`, `PATH` is also optional and identifies the content root
to export.

## Shared options

### `--output`

Choose the generated Jekyll source directory. The default is `.mkpages`.

`--output` applies to `mkpages build`, `mkpages serve`, and `mkpages preview`.
For `mkpages export`, `--output` names the required output file; see
[export](export.md).

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

### `--url` and `--baseurl`

Override the matching values in `mkpages.yml` for one build. `--url` must be
an `http://` or `https://` origin. `--baseurl` is an optional deployment
subpath such as `/project`.

These options are useful in CI when the deployment platform supplies the
canonical URL at build time. See [GitHub Pages](github-pages.md) for an
example using `actions/configure-pages`.

### `mkpages.yml`

The optional `mkpages.yml` file at the content root can set site-wide values
such as:

- `title`
- `description`
- `url`
- `baseurl`
- `theme`
- `favicon`
- `navigation`

`favicon` should be a relative path inside the content root, for example
`assets/favicon.png`. `mkpages` copies that file through and adds a favicon
link tag to the generated layout.

Set `url` to your deployed site origin, such as `https://mkpages.dev`, when
you want social card metadata to use absolute asset URLs for crawlers like X.
Set `baseurl` when the site is hosted from a subpath.
