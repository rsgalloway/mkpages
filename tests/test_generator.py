"""Tests for mkpages site generation."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

from mkpages import __version__, cli
from mkpages.generator import (
    DEV_RELOAD_TOKEN_PATH,
    OUTPUT_MARKER,
    SOCIAL_CARD_PATH,
    MkpagesError,
    build_page_map,
    generate_site,
    rewrite_local_links,
)


class RouteMappingTests(unittest.TestCase):
    """Route mapping behavior."""

    def test_build_page_map_handles_index_readme_and_regular_pages(self) -> None:
        page_map = build_page_map(
            [
                PurePosixPath("index.md"),
                PurePosixPath("docs/index.md"),
                PurePosixPath("docs/guide.md"),
                PurePosixPath("nested/README.md"),
                PurePosixPath("nested/index.md"),
            ]
        )

        self.assertEqual(page_map[PurePosixPath("index.md")].route_url, "/")
        self.assertEqual(page_map[PurePosixPath("docs/index.md")].route_url, "/docs/")
        self.assertEqual(page_map[PurePosixPath("docs/guide.md")].route_url, "/docs/guide/")
        self.assertEqual(page_map[PurePosixPath("nested/index.md")].route_url, "/nested/")
        self.assertEqual(page_map[PurePosixPath("nested/README.md")].route_url, "/nested/README/")

    def test_rewrite_local_links_updates_markdown_and_assets(self) -> None:
        page_map = build_page_map(
            [
                PurePosixPath("docs/index.md"),
                PurePosixPath("docs/guide.md"),
                PurePosixPath("docs/examples/README.md"),
            ]
        )
        page = page_map[PurePosixPath("docs/guide.md")]

        content = (
            "[Home](index.md)\n"
            "[Examples](examples/README.md#demo)\n"
            "![Logo](../images/logo.png)\n"
            "[External](https://example.com)\n"
        )
        rewritten = rewrite_local_links(content, page, page_map)

        self.assertIn("[Home](../)", rewritten)
        self.assertIn("[Examples](../examples/#demo)", rewritten)
        self.assertIn("![Logo](../../images/logo.png)", rewritten)
        self.assertIn("[External](https://example.com)", rewritten)


class GenerationTests(unittest.TestCase):
    """End-to-end generation checks."""

    def setUp(self) -> None:
        self.tempdir = Path(tempfile.mkdtemp(prefix="mkpages-test-"))
        self.content_root = self.tempdir / "docs"
        self.output_dir = self.tempdir / ".mkpages"
        self.content_root.mkdir()

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir)

    def test_generate_site_writes_expected_tree(self) -> None:
        (self.content_root / "index.md").write_text(
            "# Home\n\n"
            "## Featured\n\n"
            ":::cards source=projects featured=true limit=1 columns=2\n"
            ":::\n\n"
            "See [Guide](guide.md).\n",
            encoding="utf-8",
        )
        (self.content_root / "guide.md").write_text(
            "# Guide\n\n![Logo](images/logo.png)\n",
            encoding="utf-8",
        )
        projects_dir = self.content_root / "projects"
        projects_dir.mkdir()
        (projects_dir / "envstack.md").write_text(
            "---\n"
            'title: "envstack"\n'
            'description: "Layered environment configuration."\n'
            "featured: true\n"
            "tags:\n"
            "  - python\n"
            "  - tooling\n"
            "---\n\n"
            "# envstack\n",
            encoding="utf-8",
        )
        (self.content_root / "mkpages.yml").write_text(
            "title: Test Docs\n"
            "description: Test site description\n"
            "theme: dark\n"
            "favicon: images/favicon.png\n"
            "navigation:\n"
            "  - label: Home\n"
            "    href: /\n"
            "  - label: Guide\n"
            "    href: /guide/\n"
            "  - label: GitHub\n"
            "    href: https://github.com/example/project\n",
            encoding="utf-8",
        )
        images_dir = self.content_root / "images"
        images_dir.mkdir()
        (images_dir / "logo.png").write_bytes(b"png")
        (images_dir / "favicon.png").write_bytes(b"ico")

        result = generate_site(self.content_root, self.output_dir)

        self.assertEqual(result.pages_written, 3)
        self.assertEqual(result.assets_copied, 2)
        self.assertTrue((self.output_dir / ".mkpages-output").exists())
        self.assertTrue((self.output_dir / "_config.yml").exists())
        self.assertTrue((self.output_dir / "_layouts" / "default.html").exists())
        self.assertTrue((self.output_dir / "_includes" / "site_header.html").exists())
        self.assertTrue((self.output_dir / "assets" / "site.css").exists())
        self.assertTrue((self.output_dir / "guide" / "index.md").exists())
        self.assertTrue((self.output_dir / "images" / "logo.png").exists())
        self.assertTrue((self.output_dir / "images" / "favicon.png").exists())
        self.assertTrue((self.output_dir / "_includes" / "site_footer.html").exists())
        self.assertTrue((self.output_dir / Path(SOCIAL_CARD_PATH)).exists())

        home_page = (self.output_dir / "index.md").read_text(encoding="utf-8")
        guide_page = (self.output_dir / "guide" / "index.md").read_text(encoding="utf-8")
        layout_html = (self.output_dir / "_layouts" / "default.html").read_text(encoding="utf-8")
        social_card_svg = (self.output_dir / Path(SOCIAL_CARD_PATH)).read_text(encoding="utf-8")
        theme_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        config_text = (self.output_dir / "_config.yml").read_text(encoding="utf-8")
        header_html = (self.output_dir / "_includes" / "site_header.html").read_text(
            encoding="utf-8"
        )

        self.assertIn("layout: default", home_page)
        self.assertIn('title: "Home"', home_page)
        self.assertIn("[Guide](guide/)", home_page)
        self.assertIn('<div class="card-grid card-grid-2">', home_page)
        self.assertIn('<article class="content-card">', home_page)
        self.assertIn('<a href="/projects/envstack/">envstack</a>', home_page)
        self.assertIn('<span class="card-tag">python</span>', home_page)
        self.assertIn("![Logo](../images/logo.png)", guide_page)
        self.assertIn('title: "Test Docs"', config_text)
        self.assertIn('description: "Test site description"', config_text)
        self.assertIn('className = "header-anchor"', layout_html)
        self.assertIn('className = "copy-button"', layout_html)
        self.assertIn('class="copy-icon"', layout_html)
        self.assertIn(
            'import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"',
            layout_html,
        )
        self.assertIn(
            '<link rel="icon" href="{{ \'/images/favicon.png\' | relative_url }}">', layout_html
        )
        self.assertIn('property="og:title" content="Test Docs"', layout_html)
        self.assertIn('name="twitter:card" content="summary_large_image"', layout_html)
        self.assertIn("assets/_mkpages/social-card.svg", layout_html)
        self.assertIn('data-mkpages-card-template="dark"', social_card_svg)
        self.assertIn(">Test Docs</text>", social_card_svg)
        self.assertIn(">Test site description</tspan>", social_card_svg)
        self.assertNotIn("Generated by mkpages", social_card_svg)
        self.assertNotIn("mkpages.dev", social_card_svg)
        self.assertIn('<canvas id="theme-canvas" aria-hidden="true"></canvas>', layout_html)
        self.assertIn("function startMatrixRain(canvas)", layout_html)
        self.assertIn(
            'getComputedStyle(document.body).getPropertyValue("--matrix-rain").trim() === "on"',
            layout_html,
        )
        self.assertIn('theme: "base"', layout_html)
        self.assertIn('readThemeVar("--mermaid-node-bg"', layout_html)
        self.assertIn("darkMode: isDarkHex(mermaidBackground)", layout_html)
        self.assertIn("await mermaid.run({ nodes: mermaidBlocks });", layout_html)
        self.assertIn("/\\blanguage-mermaid\\b/.test(languageContainer.className)", layout_html)
        self.assertIn('code.classList.contains("language-mermaid")', layout_html)
        self.assertIn('wrapper.classList.add("terminal")', layout_html)
        self.assertNotIn("copy-status", layout_html)
        self.assertIn('class="site-nav"', header_html)
        self.assertIn("{{ '/' | relative_url }}", header_html)
        self.assertIn("https://github.com/example/project", header_html)
        self.assertIn("--bg: #0d1117;", theme_css)
        self.assertIn(".header-anchor", theme_css)
        self.assertIn(".copy-button", theme_css)
        self.assertNotIn(".code-block.terminal::before", theme_css)
        self.assertIn(".highlight .", theme_css)

    def test_generate_site_refuses_to_overwrite_unmarked_directory(self) -> None:
        self.output_dir.mkdir()
        (self.output_dir / "keep.txt").write_text("nope\n", encoding="utf-8")
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        with self.assertRaises(MkpagesError):
            generate_site(self.content_root, self.output_dir)

    def test_generate_site_can_recover_markerless_mkpages_output(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.output_dir / "_layouts").mkdir(parents=True)
        (self.output_dir / "_includes").mkdir()

        result = generate_site(
            self.content_root,
            self.output_dir,
            allow_unmarked_reuse=True,
        )

        self.assertEqual(result.pages_written, 1)
        self.assertTrue((self.output_dir / OUTPUT_MARKER).exists())

    def test_theme_css_at_root_overrides_explicit_theme(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "theme.css").write_text("body { color: red; }\n", encoding="utf-8")
        alt_theme = self.tempdir / "alt.css"
        alt_theme.write_text("body { color: blue; }\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, explicit_theme=alt_theme)

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("color: red", site_css)

    def test_config_theme_is_used_when_present(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text("theme: retro\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("--bg: #19130d;", site_css)

    def test_favicon_is_optional(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        layout_html = (self.output_dir / "_layouts" / "default.html").read_text(encoding="utf-8")
        self.assertNotIn('rel="icon"', layout_html)

    def test_generate_site_can_embed_preview_reload_token(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, dev_reload_token="preview-123")

        layout_html = (self.output_dir / "_layouts" / "default.html").read_text(encoding="utf-8")
        token_text = (self.output_dir / Path(DEV_RELOAD_TOKEN_PATH)).read_text(encoding="utf-8")

        self.assertIn("window.__MKPAGES_PREVIEW_TOKEN__", layout_html)
        self.assertIn("window.__MKPAGES_PREVIEW_TOKEN_URL__", layout_html)
        self.assertIn("mkpages-preview-token.txt", layout_html)
        self.assertEqual(token_text, "preview-123\n")

    def test_card_can_be_disabled(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text(
            "card:\n  enabled: false\n", encoding="utf-8"
        )

        generate_site(self.content_root, self.output_dir)

        layout_html = (self.output_dir / "_layouts" / "default.html").read_text(encoding="utf-8")
        self.assertNotIn('property="og:title"', layout_html)
        self.assertFalse((self.output_dir / Path(SOCIAL_CARD_PATH)).exists())

    def test_card_template_must_be_supported(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text(
            "card:\n  template: glossy\n",
            encoding="utf-8",
        )

        with self.assertRaises(MkpagesError) as ctx:
            generate_site(self.content_root, self.output_dir)

        self.assertIn("unsupported card template: glossy", str(ctx.exception))
        self.assertIn(
            "Built-in card templates: dark, default",
            str(ctx.exception),
        )

    def test_explicit_card_template_overrides_theme_default(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text(
            "theme: dark\n" "card:\n" "  template: default\n",
            encoding="utf-8",
        )

        generate_site(self.content_root, self.output_dir)

        social_card_svg = (self.output_dir / Path(SOCIAL_CARD_PATH)).read_text(encoding="utf-8")
        self.assertIn('data-mkpages-card-template="default"', social_card_svg)

    def test_custom_theme_css_uses_default_card_template(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "theme.css").write_text("body { color: red; }\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        social_card_svg = (self.output_dir / Path(SOCIAL_CARD_PATH)).read_text(encoding="utf-8")
        self.assertIn('data-mkpages-card-template="default"', social_card_svg)

    def test_card_prefers_configured_favicon_for_generated_art(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text(
            "theme: dark\n" "favicon: images/favicon.png\n",
            encoding="utf-8",
        )
        images_dir = self.content_root / "images"
        images_dir.mkdir()
        (images_dir / "favicon.png").write_bytes(b"fav")
        (self.content_root / "logo.png").write_bytes(b"logo")

        generate_site(self.content_root, self.output_dir)

        social_card_svg = (self.output_dir / Path(SOCIAL_CARD_PATH)).read_text(encoding="utf-8")
        self.assertIn("data:image/png;base64,ZmF2", social_card_svg)
        self.assertNotIn("data:image/png;base64,bG9nbw==", social_card_svg)

    def test_favicon_must_exist_inside_content_root(self) -> None:
        config_path = self.content_root / "mkpages.yml"
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        config_path.write_text("favicon: ../favicon.png\n", encoding="utf-8")

        with self.assertRaises(MkpagesError) as exc:
            generate_site(self.content_root, self.output_dir)

        self.assertIn("favicon", str(exc.exception))
        self.assertIn("must not use empty, '.' or '..' path segments", str(exc.exception))

    def test_favicon_rejects_unsafe_path_characters(self) -> None:
        config_path = self.content_root / "mkpages.yml"
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        config_path.write_text('favicon: "images/evil\'icon.png"\n', encoding="utf-8")

        with self.assertRaises(MkpagesError) as exc:
            generate_site(self.content_root, self.output_dir)

        self.assertIn(
            "must not contain quotes, angle brackets, backslashes, or control characters",
            str(exc.exception),
        )

    def test_default_theme_matches_pathbase_style(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("--bg: #f5f8fc;", site_css)
        self.assertIn(
            ".site-shell {\n  max-width: 1100px;\n  margin: 0 auto;\n  padding: 24px 24px 72px;",
            site_css,
        )
        self.assertIn(".site-footer {\n  display: none;", site_css)
        self.assertIn(
            "background: linear-gradient(180deg, #111b31 0%, var(--code-bg) 100%);", site_css
        )
        self.assertIn("border-radius: 4px;", site_css)
        self.assertNotIn("scrollbar-width:", site_css)
        self.assertNotIn("::-webkit-scrollbar", site_css)

    def test_explicit_theme_overrides_config_theme(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text("theme: retro\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, explicit_theme="dark")

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("--bg: #0d1117;", site_css)

    def test_bundled_named_theme_can_be_selected(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, explicit_theme="dark")

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("--bg: #0d1117;", site_css)

    def test_invalid_theme_name_mentions_bundled_choices(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        with self.assertRaises(MkpagesError) as ctx:
            generate_site(self.content_root, self.output_dir, explicit_theme="nope")

        self.assertIn(
            "Built-in themes: dark, default, developer, matrix, minimal, pulsar, retro",
            str(ctx.exception),
        )

    def test_generate_site_ignores_files_outside_content_root(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        repo_root_file = self.tempdir / "README.md"
        repo_root_file.write_text("# Root Readme\n", encoding="utf-8")
        repo_root_asset = self.tempdir / "pyproject.toml"
        repo_root_asset.write_text("[project]\nname='outside'\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        self.assertFalse((self.output_dir / "README.md").exists())
        self.assertFalse((self.output_dir / "pyproject.toml").exists())

    def test_generate_site_ignores_hidden_files_and_directories(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / ".draft.md").write_text("# Hidden Draft\n", encoding="utf-8")
        (self.content_root / ".gitignore").write_text(".mkpages\n", encoding="utf-8")
        hidden_dir = self.content_root / ".obsidian"
        hidden_dir.mkdir()
        (hidden_dir / "graph.json").write_text("{}\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        self.assertFalse((self.output_dir / ".draft" / "index.md").exists())
        self.assertFalse((self.output_dir / ".gitignore").exists())
        self.assertFalse((self.output_dir / ".obsidian" / "graph.json").exists())

    def test_generate_site_can_preserve_runtime_output_directories(self) -> None:
        self.output_dir.mkdir()
        (self.output_dir / OUTPUT_MARKER).write_text("generated by mkpages\n", encoding="utf-8")
        runtime_dir = self.output_dir / "_site"
        runtime_dir.mkdir()
        (runtime_dir / "keep.txt").write_text("keep\n", encoding="utf-8")
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(
            self.content_root,
            self.output_dir,
            preserve_output_names=("_site",),
        )

        self.assertTrue((runtime_dir / "keep.txt").exists())

    def test_invalid_navigation_item_requires_label_and_href(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "mkpages.yml").write_text(
            "navigation:\n" "  - label: Home\n",
            encoding="utf-8",
        )

        with self.assertRaises(MkpagesError) as ctx:
            generate_site(self.content_root, self.output_dir)

        self.assertIn("require label and href", str(ctx.exception))


class CliTests(unittest.TestCase):
    """CLI dispatch behavior."""

    def test_main_dispatches_serve_subcommand(self) -> None:
        with mock.patch("mkpages.cli.run_serve", return_value=0) as run_serve:
            status = cli.main(["serve", "--port", "5000"])

        self.assertEqual(status, 0)
        run_serve.assert_called_once()

    def test_main_dispatches_build_subcommand(self) -> None:
        with mock.patch("mkpages.cli.run_build", return_value=0) as run_build:
            status = cli.main(["build", "docs", "--output", ".mkpages"])

        self.assertEqual(status, 0)
        run_build.assert_called_once()

    def test_main_dispatches_preview_subcommand(self) -> None:
        with mock.patch("mkpages.cli.run_preview", return_value=0) as run_preview:
            status = cli.main(["preview", "docs", "--theme", "dark"])

        self.assertEqual(status, 0)
        run_preview.assert_called_once()

    def test_main_treats_bare_path_as_preview(self) -> None:
        with mock.patch("mkpages.cli.run_preview", return_value=0) as run_preview:
            status = cli.main(["docs", "--theme", "dark"])

        self.assertEqual(status, 0)
        run_preview.assert_called_once()

    def test_main_requires_subcommand(self) -> None:
        status = cli.main([])
        self.assertEqual(status, 2)

    def test_root_parser_uses_package_version(self) -> None:
        parser = cli.build_root_parser()

        with self.assertRaises(SystemExit) as ctx:
            parser.parse_args(["--version"])

        self.assertEqual(ctx.exception.code, 0)
        version_action = next(action for action in parser._actions if action.dest == "version")
        self.assertEqual(version_action.version, f"mkpages {__version__}")

    def test_run_serve_requires_jekyll(self) -> None:
        parser = cli.build_serve_parser()
        args = parser.parse_args([])

        with mock.patch("mkpages.cli.shutil.which", return_value=None):
            with self.assertRaises(SystemExit) as ctx:
                cli.run_serve(args, parser)

        self.assertEqual(ctx.exception.code, 2)

    def test_run_serve_requires_existing_build_output(self) -> None:
        parser = cli.build_serve_parser()
        with tempfile.TemporaryDirectory(prefix="mkpages-cli-") as tempdir:
            args = parser.parse_args(["--output", str(Path(tempdir) / ".mkpages")])

            with self.assertRaises(SystemExit) as ctx:
                cli.run_serve(args, parser)

        self.assertEqual(ctx.exception.code, 2)

    def test_run_serve_invokes_jekyll_with_generated_output(self) -> None:
        parser = cli.build_serve_parser()

        with tempfile.TemporaryDirectory(prefix="mkpages-cli-") as tempdir:
            args = parser.parse_args(
                ["--output", str(Path(tempdir) / ".mkpages"), "--host", "0.0.0.0", "--port", "5000"]
            )
            output_dir = Path(tempdir) / ".mkpages"
            output_dir.mkdir()
            (output_dir / OUTPUT_MARKER).write_text("generated by mkpages\n", encoding="utf-8")

            with mock.patch("mkpages.cli.shutil.which", return_value="/usr/bin/jekyll"):
                with mock.patch("mkpages.cli.threading.Timer") as timer:
                    process = mock.Mock()
                    process.wait.return_value = 0
                    with mock.patch("mkpages.cli.subprocess.Popen", return_value=process) as popen:
                        status = cli.run_serve(args, parser)

        self.assertEqual(status, 0)
        timer.assert_called_once_with(1.0, cli.open_browser, args=("0.0.0.0", 5000))
        timer.return_value.start.assert_called_once_with()
        process.wait.assert_called_once_with()
        popen.assert_called_once_with(
            [
                "/usr/bin/jekyll",
                "serve",
                "--source",
                str(output_dir),
                "--destination",
                str(output_dir / "_site"),
                "--host",
                "0.0.0.0",
                "--port",
                "5000",
                "--livereload",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=os.name != "nt",
        )

    def test_start_jekyll_serve_uses_windows_safe_launch(self) -> None:
        parser = cli.build_serve_parser()

        with tempfile.TemporaryDirectory(prefix="mkpages-cli-") as tempdir:
            output_dir = Path(tempdir) / ".mkpages"
            output_dir.mkdir()
            (output_dir / OUTPUT_MARKER).write_text("generated by mkpages\n", encoding="utf-8")

            with mock.patch("mkpages.cli.os.name", "nt"):
                with mock.patch("mkpages.cli.shutil.which", return_value="C:\\jekyll.bat"):
                    with mock.patch("mkpages.cli.threading.Timer"):
                        process = mock.Mock()
                        with mock.patch(
                            "mkpages.cli.subprocess.Popen", return_value=process
                        ) as popen:
                            result = cli.start_jekyll_serve(
                                output_dir,
                                "127.0.0.1",
                                4000,
                                parser,
                            )

        self.assertIs(result, process)
        self.assertEqual(popen.call_args.kwargs["start_new_session"], False)

    def test_stop_jekyll_process_uses_windows_fallback(self) -> None:
        process = mock.Mock()
        process.poll.return_value = None

        with mock.patch("mkpages.cli.os.name", "nt"):
            cli.stop_jekyll_process(process)

        process.terminate.assert_called_once_with()
        process.wait.assert_called_once_with(timeout=5)

    def test_run_preview_rebuilds_and_restarts_on_config_change(self) -> None:
        parser = cli.build_preview_parser()
        args = parser.parse_args(["docs", "--output", ".mkpages", "--port", "5000"])
        initial_result = mock.Mock(pages_written=1, assets_copied=0, output_dir=Path(".mkpages"))
        rebuild_result = mock.Mock(pages_written=1, assets_copied=1, output_dir=Path(".mkpages"))
        first_process = mock.Mock()
        first_process.poll.return_value = None
        second_process = mock.Mock()
        second_process.poll.return_value = None
        snapshots = [
            {PurePosixPath("index.md"): (1, 10)},
            {
                PurePosixPath("index.md"): (1, 10),
                PurePosixPath("mkpages.yml"): (2, 20),
            },
        ]

        with mock.patch("mkpages.cli.build_site", return_value=initial_result) as build_site:
            with mock.patch(
                "mkpages.cli.start_jekyll_serve",
                side_effect=[first_process, second_process],
            ) as start_jekyll_serve:
                with mock.patch(
                    "mkpages.cli.rebuild_site_from_staging", return_value=rebuild_result
                ) as rebuild_site_from_staging:
                    with mock.patch("mkpages.cli.build_source_snapshot", side_effect=snapshots):
                        with mock.patch(
                            "mkpages.cli.time.sleep", side_effect=[None, KeyboardInterrupt]
                        ):
                            with mock.patch(
                                "mkpages.cli.stop_jekyll_process"
                            ) as stop_jekyll_process:
                                with mock.patch("builtins.print"):
                                    status = cli.run_preview(args, parser)

        self.assertEqual(status, 0)
        build_site.assert_called_once()
        self.assertEqual(
            build_site.call_args.args[:4], (Path("docs"), Path(".mkpages"), None, parser)
        )
        self.assertIn("dev_reload_token", build_site.call_args.kwargs)
        rebuild_site_from_staging.assert_called_once_with(
            Path("docs"), Path(".mkpages"), None, parser, dev_reload_token=mock.ANY
        )
        self.assertEqual(start_jekyll_serve.call_count, 2)
        start_jekyll_serve.assert_any_call(
            Path(".mkpages"), "127.0.0.1", 5000, parser, verbose=False, open_browser_tab=True
        )
        start_jekyll_serve.assert_any_call(
            Path(".mkpages"), "127.0.0.1", 5000, parser, verbose=False, open_browser_tab=False
        )
        stop_jekyll_process.assert_has_calls([mock.call(first_process), mock.call(second_process)])

    def test_run_preview_reports_rebuild_error_without_aborting(self) -> None:
        parser = cli.build_preview_parser()
        args = parser.parse_args(["docs", "--output", ".mkpages"])
        initial_result = mock.Mock(pages_written=1, assets_copied=0, output_dir=Path(".mkpages"))
        process = mock.Mock()
        process.poll.return_value = None
        snapshots = [
            {PurePosixPath("index.md"): (1, 10)},
            {PurePosixPath("mkpages.yml"): (2, 20)},
        ]

        with mock.patch("mkpages.cli.build_site", return_value=initial_result):
            with mock.patch("mkpages.cli.start_jekyll_serve", return_value=process):
                with mock.patch("mkpages.cli.build_source_snapshot", side_effect=snapshots):
                    with mock.patch(
                        "mkpages.cli.time.sleep", side_effect=[None, KeyboardInterrupt]
                    ):
                        with mock.patch(
                            "mkpages.cli.rebuild_site_from_staging",
                            side_effect=MkpagesError("theme file does not exist: dretrok"),
                        ):
                            with mock.patch(
                                "mkpages.cli.stop_jekyll_process"
                            ) as stop_jekyll_process:
                                with mock.patch("mkpages.cli.print_status") as print_status:
                                    status = cli.run_preview(args, parser)

        self.assertEqual(status, 0)
        print_status.assert_any_call(
            "Rebuild failed: theme file does not exist: dretrok",
            kind="error",
            stream=sys.stderr,
        )
        stop_jekyll_process.assert_called_once_with(process)

    def test_run_serve_stops_jekyll_on_keyboard_interrupt(self) -> None:
        parser = cli.build_serve_parser()
        args = parser.parse_args(["--output", ".mkpages"])
        process = mock.Mock()
        process.wait.side_effect = KeyboardInterrupt

        with mock.patch("mkpages.cli.start_jekyll_serve", return_value=process):
            with mock.patch("mkpages.cli.stop_jekyll_process") as stop_jekyll_process:
                status = cli.run_serve(args, parser)

        self.assertEqual(status, 0)
        stop_jekyll_process.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
