# GitHub Pages

`mkpages` is designed to fit a Jekyll-based GitHub Pages workflow.

## Typical flow

1. Install Python
2. Install `mkpages`
3. Run `mkpages docs/ --output .mkpages`
4. Build the generated Jekyll source
5. Deploy the resulting site

## Example workflow

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: "3.11"

- run: python -m pip install mkpages

- run: mkpages docs/ --output .mkpages

- uses: actions/jekyll-build-pages@v1
  with:
    source: ./.mkpages
    destination: ./_site
```

## Why this works well

- your repository keeps its own Markdown layout
- generated output stays disposable
- Jekyll still handles rendering
- GitHub Pages remains the deployment target
