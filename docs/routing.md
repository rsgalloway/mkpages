# Routing Rules

`mkpages` preserves structure relative to the chosen content root.

## Core rules

- `index.md` maps to the containing directory
- `README.md` maps to the containing directory when `index.md` is absent
- any other `name.md` maps to `name/`
- nested structure is preserved relative to the content root

## Examples

If the command is:

```bash
mkpages .
```

then:

- `index.md` becomes `/`
- `docs/index.md` becomes `/docs/`
- `blog/post-1.md` becomes `/blog/post-1/`

If the command is:

```bash
mkpages docs/
```

then:

- `docs/index.md` becomes `/`
- `docs/getting-started.md` becomes `/getting-started/`
- `docs/examples/default.md` becomes `/examples/default/`

## Link rewriting

Relative Markdown links such as [CLI Reference](cli-reference.md) are rewritten
so they continue to work after route generation.

## Permalink overrides

The rules above determine the default route that `mkpages` generates. `mkpages`
preserves YAML front matter, so Jekyll can override that route with a
`permalink` value.

```yaml
---
permalink: /blog/my-post/
---
```

For example, `blog/my-post.md` normally uses `/blog/my-post/`, but a
`permalink` can publish it at a different path.

More front matter information is available in [Front Matter](front-matter.md).
