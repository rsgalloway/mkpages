# GitHub Pages

`mkpages` is designed to fit a Jekyll-based GitHub Pages workflow.

## Typical flow

1. Install Python
2. Install `mkpages`
3. Run `mkpages build docs/ --output .mkpages`
4. Build the generated Jekyll source
5. Deploy the resulting site

## Workflow with automatic site URL

GitHub Pages knows the configured hostname before the site is built. Give
`actions/configure-pages` an `id`, then pass its `host` and `base_path` outputs
to `mkpages`. Prefixing the hostname with `https://` ensures social-card image
URLs use HTTPS without hard-coding a domain in `mkpages.yml`.

```yaml
name: Deploy Pages

on:
  push:
    branches: [main]

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - id: pages
        uses: actions/configure-pages@v5
      - run: python -m pip install mkpages
      - run: >-
          mkpages build docs/ --output .mkpages
          --url "https://${{ steps.pages.outputs.host }}"
          --baseurl "${{ steps.pages.outputs.base_path }}"
      - uses: actions/jekyll-build-pages@v1
        with:
          source: ./.mkpages
          destination: ./_site
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./_site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v4
```

`host` is the configured hostname, such as `mkpages.dev`; `base_path` is empty
for a custom domain or user site, and is typically `/repository-name` for a
project site. The CLI options override `url` and `baseurl` in `mkpages.yml`
only for that build.

## Why this works well

- your repository keeps its own Markdown layout
- generated output stays disposable
- Jekyll still handles rendering
- GitHub Pages remains the deployment target
