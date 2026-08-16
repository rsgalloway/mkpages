"""Command-line interface for mkpages."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages",
        description="Generate a Jekyll source tree from a Markdown folder tree.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Content root to process. Defaults to the current directory.",
    )
    parser.add_argument(
        "--output",
        default=".mkpages",
        help="Directory where the generated Jekyll source tree will be written.",
    )
    parser.add_argument(
        "--theme",
        help="Optional path to a CSS file to apply as the generated site theme.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="mkpages 0.1.0",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and validate the content root for now."""
    parser = build_parser()
    args = parser.parse_args(argv)

    content_root = Path(args.path).expanduser()
    if not content_root.exists():
        parser.error(f"content root does not exist: {content_root}")
    if not content_root.is_dir():
        parser.error(f"content root is not a directory: {content_root}")

    print(f"mkpages: content root={content_root.resolve()} output={Path(args.output)}")
    if args.theme:
        print(f"mkpages: theme={Path(args.theme)}")
    print("mkpages: generator implementation is not wired up yet.")
    return 0
