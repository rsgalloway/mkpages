# `mkpages build`

```bash
mkpages build [PATH] [--output .mkpages] [--theme NAME_OR_PATH] [--url URL] [--baseurl PATH]
```

Generate a Jekyll source tree from a Markdown folder tree. `PATH` defaults to
the current directory and the generated output defaults to `.mkpages`.

Hidden files and directories under the content root are ignored by default.

## Examples

Generate a site from the repository root:

```bash
mkpages build
```

Generate from `docs/` with an explicit stylesheet:

```bash
mkpages build docs/ --output .mkpages --theme ./custom.css
```

Use a bundled theme:

```bash
mkpages build docs/ --theme dark
```

See the [CLI reference](index.md) for shared options and [Theming](../theming.md)
for theme precedence.
