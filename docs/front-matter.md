# Front Matter

`mkpages` preserves YAML front matter from Markdown pages and adds `layout` and
`title` when they are absent. Some fields are used by `mkpages`; other valid
Jekyll fields are passed through unchanged.

## Example

```yaml
---
title: The File I Didn't Know Was an API
description: A small interface can be more powerful than it looks.
date: 2026-08-22
order: 10
featured: true
tags:
  - API
  - files
permalink: /blog/the-file-i-didnt-know-was-an-api/
---
```

## Fields used by mkpages

- `title`: the page title. If omitted, `mkpages` uses the first H1 or derives a
  title from the filename.
- `layout`: the Jekyll layout. If omitted, `mkpages` adds `layout: default`.
- `description`: the summary shown in generated content cards.
- `excerpt`: used as a card summary when `description` is absent.
- `order`: an integer used to order content cards. Entries with an `order`
  value appear first, in ascending order.
- `date`: orders content cards when `order` does not decide their position.
- `featured`: use `featured: true` to include the page when a `:::cards`
  directive has `featured=true`.
- `tags`: a YAML list rendered on generated content cards, up to three tags.

For example, this directive lists featured pages from the `blog` folder:

```text
:::cards source=blog featured=true
```

## Fields used by Jekyll

`permalink` overrides the default route generated from a Markdown filename:

```yaml
permalink: /blog/the-file-i-didnt-know-was-an-api/
```

For example, `blog/2026-08-22-the-file-i-didnt-know-was-an-api.md` normally
uses `/blog/2026-08-22-the-file-i-didnt-know-was-an-api/`; the `permalink`
above publishes it at `/blog/the-file-i-didnt-know-was-an-api/`.

Other valid Jekyll front-matter fields are also preserved. `mkpages` only
interprets the fields listed above, so use simple scalar values and YAML lists
for metadata that needs to affect generated cards or their ordering.
