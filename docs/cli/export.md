# `mkpages export`

```bash
mkpages export [PATH] --output OUTPUT_FILE [--format {docx,pdf,zip}]
```

Create a portable artifact from a Markdown folder tree. `PATH` defaults to the
current directory. mkpages infers the format from the output extension, or you
can set it explicitly with `--format`.

## Formats

- `.docx`: Combine the Markdown tree into one Word document.
- `.pdf`: Combine the Markdown tree into one PDF document.
- `.zip`: Archive the rendered static HTML site and its assets, not the
  Markdown source files.

Document ordering is deterministic: `index.md` comes first in each directory,
then the remaining Markdown files alphabetically, followed by subdirectories
alphabetically and recursively.

## Pandoc for PDF and DOCX

PDF and DOCX exports use the `pandoc` executable detected on `PATH` at runtime.
Pandoc is an optional external system dependency: a normal `pip install mkpages`
does not install it, and `build`, `serve`, and ZIP export do not require it.

Install Pandoc using the instructions for your operating system in the official
[Pandoc installation guide](https://pandoc.org/installing.html), then confirm it
is available:

```bash
pandoc --version
```

DOCX is generated directly by Pandoc. PDF exports use Pandoc's default PDF
behavior, which may require a separate PDF engine on the host. mkpages does not
bundle an engine; if one is unavailable, it reports Pandoc's error so you can
install or configure an appropriate backend.

## Importing a ZIP into Confluence Cloud

The rendered-site ZIP can be used as a starting point for moving a documentation
tree into Confluence Cloud. Confluence's HTML importer creates a new space from
an HTML ZIP, so use a disposable test space first and review the converted pages
before treating it as a migration workflow.

```bash
mkpages export docs/ --output docs.zip
```

In Confluence Cloud, go to **Spaces**, choose **Import from other tools**, then
select **HTML** and upload `docs.zip`. You need permission to create a space to
start the import. See Atlassian's
[HTML import guide](https://support.atlassian.com/confluence-cloud/docs/import-data-from-html-to-confluence/)
for the current steps and requirements.

The ZIP contains rendered HTML and assets, not Confluence-native content. Check
page hierarchy, links, images, and any custom styling or JavaScript after import;
those details may need Confluence-specific cleanup. For an existing space or a
repeatable publishing pipeline, use a Confluence-specific importer or API-based
integration rather than relying on this one-time HTML import.

## Examples

```bash
mkpages export docs/ --output docs.docx
mkpages export docs/ --output docs.pdf
mkpages export docs/ --output docs.zip
```

Override the format when the output filename does not have a recognized
extension:

```bash
mkpages export docs/ --output artifact.bin --format pdf
```
