# `mkpages preview`

```bash
mkpages preview [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--url URL] [--baseurl PATH] [--host 127.0.0.1] [--port 4000]
```

Build a Markdown folder tree, watch it for changes, and serve it through Jekyll
with live reload. It combines [`mkpages build`](build.md) and
[`mkpages serve`](serve.md).

Edits to non-hidden files under the content root trigger a fresh build. Changes
to `mkpages.yml` also restart Jekyll so its generated configuration is reloaded.

## Examples

```bash
mkpages preview docs/ --theme dark
```

A bare content path is a shortcut for `preview`:

```bash
mkpages docs/ --theme dark
```
