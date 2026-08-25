# `mkpages serve`

```bash
mkpages serve [--output .mkpages] [--host 127.0.0.1] [--port 4000]
```

Serve an existing generated site through `jekyll serve --livereload`.
`mkpages serve` does not rebuild the site, so run [`mkpages build`](build.md)
first.

The `jekyll` executable must be installed and available on `PATH`. When
possible, mkpages opens the preview URL in your browser and Jekyll refreshes it
when files change inside the generated output directory.

## Example

```bash
mkpages build docs/
mkpages serve --port 5000
```

`--host` selects the bind address; the default is `127.0.0.1`. `--port`
defaults to `4000`.
