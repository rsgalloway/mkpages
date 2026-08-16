"""Tests for mkpages site generation."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest import mock

from mkpages import __version__, cli
from mkpages.generator import (
    MkpagesError,
    OUTPUT_MARKER,
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
            "# Home\n\nSee [Guide](guide.md).\n", encoding="utf-8"
        )
        (self.content_root / "guide.md").write_text(
            "# Guide\n\n![Logo](images/logo.png)\n",
            encoding="utf-8",
        )
        images_dir = self.content_root / "images"
        images_dir.mkdir()
        (images_dir / "logo.png").write_bytes(b"png")

        result = generate_site(self.content_root, self.output_dir)

        self.assertEqual(result.pages_written, 2)
        self.assertEqual(result.assets_copied, 1)
        self.assertTrue((self.output_dir / ".mkpages-output").exists())
        self.assertTrue((self.output_dir / "_config.yml").exists())
        self.assertTrue((self.output_dir / "_layouts" / "default.html").exists())
        self.assertTrue((self.output_dir / "_includes" / "site_header.html").exists())
        self.assertTrue((self.output_dir / "assets" / "site.css").exists())
        self.assertTrue((self.output_dir / "guide" / "index.md").exists())
        self.assertTrue((self.output_dir / "images" / "logo.png").exists())

        home_page = (self.output_dir / "index.md").read_text(encoding="utf-8")
        guide_page = (self.output_dir / "guide" / "index.md").read_text(encoding="utf-8")

        self.assertIn("layout: default", home_page)
        self.assertIn('title: "Home"', home_page)
        self.assertIn("[Guide](guide/)", home_page)
        self.assertIn("![Logo](../images/logo.png)", guide_page)

    def test_generate_site_refuses_to_overwrite_unmarked_directory(self) -> None:
        self.output_dir.mkdir()
        (self.output_dir / "keep.txt").write_text("nope\n", encoding="utf-8")
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        with self.assertRaises(MkpagesError):
            generate_site(self.content_root, self.output_dir)

    def test_theme_css_at_root_overrides_explicit_theme(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        (self.content_root / "theme.css").write_text("body { color: red; }\n", encoding="utf-8")
        alt_theme = self.tempdir / "alt.css"
        alt_theme.write_text("body { color: blue; }\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, explicit_theme=alt_theme)

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("color: red", site_css)

    def test_bundled_named_theme_can_be_selected(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir, explicit_theme="dark")

        site_css = (self.output_dir / "assets" / "site.css").read_text(encoding="utf-8")
        self.assertIn("--bg: #0d1117;", site_css)

    def test_invalid_theme_name_mentions_bundled_choices(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")

        with self.assertRaises(MkpagesError) as ctx:
            generate_site(self.content_root, self.output_dir, explicit_theme="nope")

        self.assertIn("Built-in themes: dark, default, minimal", str(ctx.exception))

    def test_generate_site_ignores_files_outside_content_root(self) -> None:
        (self.content_root / "index.md").write_text("# Home\n", encoding="utf-8")
        repo_root_file = self.tempdir / "README.md"
        repo_root_file.write_text("# Root Readme\n", encoding="utf-8")
        repo_root_asset = self.tempdir / "pyproject.toml"
        repo_root_asset.write_text("[project]\nname='outside'\n", encoding="utf-8")

        generate_site(self.content_root, self.output_dir)

        self.assertFalse((self.output_dir / "README.md").exists())
        self.assertFalse((self.output_dir / "pyproject.toml").exists())


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
        args = parser.parse_args([])

        original_output = cli.DEFAULT_OUTPUT_DIR
        with tempfile.TemporaryDirectory(prefix="mkpages-cli-") as tempdir:
            try:
                cli.DEFAULT_OUTPUT_DIR = Path(tempdir) / ".mkpages"
                with self.assertRaises(SystemExit) as ctx:
                    cli.run_serve(args, parser)
            finally:
                cli.DEFAULT_OUTPUT_DIR = original_output

        self.assertEqual(ctx.exception.code, 2)

    def test_run_serve_invokes_jekyll_with_generated_output(self) -> None:
        parser = cli.build_serve_parser()

        with tempfile.TemporaryDirectory(prefix="mkpages-cli-") as tempdir:
            args = parser.parse_args(["--host", "0.0.0.0", "--port", "5000"])
            output_dir = Path(tempdir) / ".mkpages"
            output_dir.mkdir()
            (output_dir / OUTPUT_MARKER).write_text("generated by mkpages\n", encoding="utf-8")

            original_output = cli.DEFAULT_OUTPUT_DIR
            with mock.patch("mkpages.cli.shutil.which", return_value="/usr/bin/jekyll"):
                try:
                    cli.DEFAULT_OUTPUT_DIR = output_dir
                    with mock.patch("mkpages.cli.threading.Timer") as timer:
                        with mock.patch(
                            "mkpages.cli.subprocess.run", return_value=mock.Mock(returncode=0)
                        ) as run:
                            status = cli.run_serve(args, parser)
                finally:
                    cli.DEFAULT_OUTPUT_DIR = original_output

        self.assertEqual(status, 0)
        timer.assert_called_once_with(1.0, cli.open_browser, args=("0.0.0.0", 5000))
        timer.return_value.start.assert_called_once_with()
        run.assert_called_once_with(
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
            ],
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
