"""Command-line interface for mkpages."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from mkpages import __version__
from mkpages.generator import OUTPUT_MARKER, MkpagesError, generate_site

DEFAULT_OUTPUT_DIR = Path(".mkpages")


def add_source_argument(parser: argparse.ArgumentParser, default: str = ".") -> None:
    """Add the shared content-root argument."""
    parser.add_argument(
        "path",
        nargs="?",
        default=default,
        help="Content root to process. Defaults to the current directory.",
    )


def add_build_options(parser: argparse.ArgumentParser) -> None:
    """Add options used when generating the source tree."""
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where the generated Jekyll source tree will be written.",
    )
    parser.add_argument(
        "--theme",
        help="Optional path to a CSS file to apply as the generated site theme.",
    )


def add_version_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared version flag."""
    parser.add_argument(
        "--version",
        action="version",
        version=f"mkpages {__version__}",
    )


def build_build_parser() -> argparse.ArgumentParser:
    """Create the build subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages build",
        description="Generate a Jekyll source tree from a Markdown folder tree.",
    )
    add_source_argument(parser)
    add_build_options(parser)
    return parser


def build_serve_parser() -> argparse.ArgumentParser:
    """Create the serve subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages serve",
        description="Serve an existing mkpages output directory through Jekyll.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Existing mkpages output directory to serve. The default is .mkpages.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind the Jekyll preview server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4000,
        help="Port for the Jekyll preview server.",
    )
    return parser


def build_preview_parser() -> argparse.ArgumentParser:
    """Create the preview subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages preview",
        description="Build a Markdown folder tree into .mkpages and serve it through Jekyll.",
    )
    add_source_argument(parser)
    add_build_options(parser)
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host interface to bind the Jekyll preview server to.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=4000,
        help="Port for the Jekyll preview server.",
    )
    return parser


def build_root_parser() -> argparse.ArgumentParser:
    """Create the top-level subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages",
        description="Generate and preview Jekyll source trees from Markdown folder trees.",
    )
    add_version_argument(parser)
    parser.add_argument(
        "command",
        nargs="?",
        help="Subcommand to run, or a Markdown content path to preview directly.",
    )
    return parser


def run_build(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Generate the Jekyll source tree."""
    content_root, output_dir, theme_path = resolve_common_paths(args, parser)

    try:
        result = generate_site(
            content_root=content_root, output_dir=output_dir, explicit_theme=theme_path
        )
    except MkpagesError as exc:
        parser.exit(status=2, message=f"mkpages: error: {exc}\n")

    print(
        f"mkpages: generated {result.pages_written} page(s) and copied "
        f"{result.assets_copied} asset(s) into {result.output_dir}"
    )
    return 0


def run_serve(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Serve the existing generated site through Jekyll."""
    output_dir = Path(getattr(args, "output", DEFAULT_OUTPUT_DIR)).expanduser()
    jekyll_bin = shutil.which("jekyll")
    if jekyll_bin is None:
        parser.exit(
            status=2,
            message=(
                "mkpages: error: jekyll executable not found on PATH. "
                "Install Jekyll to use `mkpages serve`.\n"
            ),
        )

    if not output_dir.exists():
        parser.exit(
            status=2,
            message=f"mkpages: error: output directory does not exist: {output_dir}. Run `mkpages build` first.\n",
        )
    if not output_dir.is_dir():
        parser.exit(
            status=2, message=f"mkpages: error: output path is not a directory: {output_dir}\n"
        )
    if not (output_dir / OUTPUT_MARKER).exists():
        parser.exit(
            status=2,
            message=(
                f"mkpages: error: {output_dir} is not a mkpages output directory. "
                "Run `mkpages build` first.\n"
            ),
        )

    print(f"mkpages: serving at http://{args.host}:{args.port}/ via Jekyll")
    threading.Timer(1.0, open_browser, args=(args.host, args.port)).start()

    command = [
        jekyll_bin,
        "serve",
        "--source",
        str(output_dir),
        "--destination",
        str(output_dir / "_site"),
        "--host",
        args.host,
        "--port",
        str(args.port),
    ]
    try:
        completed = subprocess.run(command, check=False)
    except OSError as exc:
        parser.exit(status=2, message=f"mkpages: error: unable to launch jekyll: {exc}\n")
        return 2

    if completed.returncode != 0:
        return completed.returncode
    return 0


def run_preview(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Build and then serve a Markdown tree using the default mkpages output flow."""
    status = run_build(args, parser)
    if status != 0:
        return status
    return run_serve(args, parser)


def open_browser(host: str, port: int) -> None:
    """Open the preview URL in the user's default browser."""
    browser_host = "localhost" if host in {"0.0.0.0", "::"} else host
    try:
        webbrowser.open_new_tab(f"http://{browser_host}:{port}/")
    except Exception:
        pass


def resolve_common_paths(
    args: argparse.Namespace, parser: argparse.ArgumentParser
) -> tuple[Path, Path, Path | None]:
    """Validate shared path arguments for build and serve commands."""
    content_root = Path(args.path).expanduser()
    if not content_root.exists():
        parser.error(f"content root does not exist: {content_root}")
    if not content_root.is_dir():
        parser.error(f"content root is not a directory: {content_root}")

    output_dir = Path(args.output).expanduser()
    theme_path = Path(args.theme).expanduser() if args.theme else None
    return content_root, output_dir, theme_path


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the requested subcommand."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    root_parser = build_root_parser()
    root_args = root_parser.parse_args(args_list[:1])

    if root_args.command == "build":
        parser = build_build_parser()
        args = parser.parse_args(args_list[1:])
        return run_build(args, parser)
    if root_args.command == "serve":
        parser = build_serve_parser()
        args = parser.parse_args(args_list[1:])
        return run_serve(args, parser)
    if root_args.command == "preview":
        parser = build_preview_parser()
        args = parser.parse_args(args_list[1:])
        return run_preview(args, parser)
    if root_args.command:
        parser = build_preview_parser()
        args = parser.parse_args(args_list)
        return run_preview(args, parser)

    root_parser.print_usage(sys.stderr)
    print(
        "mkpages: error: a subcommand is required (build, serve, or preview)",
        file=sys.stderr,
    )
    return 2
