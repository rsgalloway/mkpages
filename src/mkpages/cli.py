"""Command-line interface for mkpages."""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mkpages import __version__
from mkpages.generator import (
    CONFIG_FILE_NAME,
    OUTPUT_MARKER,
    MkpagesError,
    generate_site,
    is_excluded,
)

DEFAULT_OUTPUT_DIR = Path(".mkpages")
WATCH_POLL_INTERVAL = 0.5
JEKYLL_RUNTIME_NAMES = ("_site", ".jekyll-cache", ".jekyll-metadata", ".sass-cache")
NOISY_JEKYLL_PATTERNS = (
    "Configuration file:",
    "Source:",
    "Destination:",
    "Incremental build:",
    "Generating...",
    "Auto-regeneration:",
    "LiveReload address:",
    "Server address:",
    "Server running...",
    "LiveReload: Browser connected",
    "done in ",
    "...done in ",
)
_TRANSIENT_STATUS_ACTIVE = False


@dataclass
class ConsoleStyle:
    """Optional ANSI styling for concise CLI status lines."""

    muted: str = ""
    accent: str = ""
    success: str = ""
    warning: str = ""
    error: str = ""
    reset: str = ""


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


def add_verbose_option(parser: argparse.ArgumentParser) -> None:
    """Add the shared verbose flag."""
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show full Jekyll and rebuild output.",
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
    add_verbose_option(parser)
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
    add_verbose_option(parser)
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
    add_verbose_option(parser)
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
    result = build_site(content_root, output_dir, theme_path, parser)

    print_status(
        f"Built {result.pages_written} page(s) and copied {result.assets_copied} asset(s) into {result.output_dir}",
        kind="success",
    )
    return 0


def run_serve(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Serve the existing generated site through Jekyll."""
    output_dir = Path(getattr(args, "output", DEFAULT_OUTPUT_DIR)).expanduser()
    process: subprocess.Popen | None = None
    try:
        process = start_jekyll_serve(output_dir, args.host, args.port, parser, verbose=args.verbose)
        return process.wait()
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        parser.exit(status=2, message=f"mkpages: error: unable to launch jekyll: {exc}\n")
        return 2
    finally:
        if process is not None:
            stop_jekyll_process(process)


def run_preview(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Build, watch, and serve a Markdown tree using the default mkpages output flow."""
    content_root, output_dir, theme_path = resolve_common_paths(args, parser)
    result = build_site(content_root, output_dir, theme_path, parser)
    print_status(
        f"Built {result.pages_written} page(s) and copied {result.assets_copied} asset(s) into {output_dir}",
        kind="success",
    )

    process: subprocess.Popen | None = None

    snapshot = build_source_snapshot(content_root)
    try:
        process = start_jekyll_serve(output_dir, args.host, args.port, parser, verbose=args.verbose)
        print_status(
            f"Watching {content_root} and serving http://{args.host}:{args.port}/",
            kind="accent",
        )
        while True:
            if process.poll() is not None:
                return process.returncode or 0

            time.sleep(WATCH_POLL_INTERVAL)
            next_snapshot = build_source_snapshot(content_root)
            changed_paths = detect_changed_paths(snapshot, next_snapshot)
            if not changed_paths:
                continue

            snapshot = next_snapshot
            if args.verbose:
                changed_list = ", ".join(path.as_posix() for path in changed_paths)
                print_status(f"Source change detected: {changed_list}", kind="muted")
            else:
                print_status(
                    f"Change detected in {summarize_changed_paths(changed_paths)}; rebuilding...",
                    kind="muted",
                    transient=True,
                )

            needs_restart = PurePosixPath(CONFIG_FILE_NAME) in changed_paths
            try:
                result = rebuild_site_from_staging(
                    content_root,
                    output_dir,
                    theme_path,
                    parser,
                )
            except MkpagesError as exc:
                clear_transient_status()
                print_status(f"Rebuild failed: {exc}", kind="error", stream=sys.stderr)
                continue
            except Exception as exc:  # pragma: no cover
                clear_transient_status()
                print_status(f"Rebuild failed: {exc}", kind="error", stream=sys.stderr)
                continue

            print_status(
                f"Rebuilt {result.pages_written} page(s), copied {result.assets_copied} asset(s)",
                kind="success",
                transient=not args.verbose,
            )

            if needs_restart:
                print_status(
                    "Restarting Jekyll to reload updated site configuration", kind="warning"
                )
                stop_jekyll_process(process)
                process = start_jekyll_serve(
                    output_dir, args.host, args.port, parser, verbose=args.verbose
                )
    except KeyboardInterrupt:
        clear_transient_status()
        return 0
    except OSError as exc:
        parser.exit(status=2, message=f"mkpages: error: unable to launch jekyll: {exc}\n")
        return 2
    finally:
        clear_transient_status()
        if process is not None:
            stop_jekyll_process(process)


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


def print_status(
    message: str,
    kind: str = "muted",
    stream=sys.stdout,
    transient: bool = False,
) -> None:
    """Print one concise mkpages status line."""
    global _TRANSIENT_STATUS_ACTIVE
    style = console_style()
    prefixes = {
        "muted": f"{style.muted}mkpages{style.reset}",
        "accent": f"{style.accent}mkpages{style.reset}",
        "success": f"{style.success}mkpages{style.reset}",
        "warning": f"{style.warning}mkpages{style.reset}",
        "error": f"{style.error}mkpages{style.reset}",
    }
    rendered = f"{prefixes.get(kind, 'mkpages')}: {message}"
    if transient and stream is sys.stdout and sys.stdout.isatty():
        print(f"\r\033[2K{rendered}", file=stream, end="", flush=True)
        _TRANSIENT_STATUS_ACTIVE = True
        return

    if _TRANSIENT_STATUS_ACTIVE and stream is sys.stdout:
        print(file=stream, flush=True)
        _TRANSIENT_STATUS_ACTIVE = False
    print(rendered, file=stream, flush=True)


def clear_transient_status() -> None:
    """Finish any in-place status line so the shell prompt stays clean."""
    global _TRANSIENT_STATUS_ACTIVE
    if not _TRANSIENT_STATUS_ACTIVE or not sys.stdout.isatty():
        return
    print(file=sys.stdout, flush=True)
    _TRANSIENT_STATUS_ACTIVE = False


def console_style() -> ConsoleStyle:
    """Return ANSI colors when stdout is an interactive terminal."""
    if not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        return ConsoleStyle()
    return ConsoleStyle(
        muted="\033[2m",
        accent="\033[36m",
        success="\033[32m",
        warning="\033[33m",
        error="\033[31m",
        reset="\033[0m",
    )


def summarize_changed_paths(changed_paths: tuple[PurePosixPath, ...]) -> str:
    """Summarize changed paths for compact preview output."""
    names = [path.as_posix() for path in changed_paths[:3]]
    if len(changed_paths) == 1:
        return names[0]
    if len(changed_paths) <= 3:
        return ", ".join(names)
    return f"{', '.join(names)} and {len(changed_paths) - 3} more"


def build_site(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    parser: argparse.ArgumentParser,
    preserve_output_names: tuple[str, ...] = (),
):
    """Generate the site or exit with a friendly parser error."""
    try:
        return generate_site_checked(
            content_root=content_root,
            output_dir=output_dir,
            theme_path=theme_path,
            preserve_output_names=preserve_output_names,
        )
    except MkpagesError as exc:
        parser.exit(status=2, message=f"mkpages: error: {exc}\n")
    except Exception as exc:  # pragma: no cover
        parser.exit(status=2, message=f"mkpages: error: unexpected build failure: {exc}\n")


def generate_site_checked(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    preserve_output_names: tuple[str, ...] = (),
):
    """Generate a site and raise regular Python exceptions for callers that want to recover."""
    return generate_site(
        content_root=content_root,
        output_dir=output_dir,
        explicit_theme=theme_path,
        preserve_output_names=preserve_output_names,
        allow_unmarked_reuse=output_dir.name == DEFAULT_OUTPUT_DIR.name,
    )


def rebuild_site_from_staging(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    parser: argparse.ArgumentParser,
):
    """Rebuild preview output via a staging tree to avoid tearing away live Jekyll inputs."""
    staging_root = Path(
        tempfile.mkdtemp(prefix=f"{output_dir.name}-staging-", dir=str(output_dir.parent))
    )
    try:
        result = generate_site_checked(content_root, staging_root, theme_path)
        sync_staged_output(staging_root, output_dir, preserve_names=JEKYLL_RUNTIME_NAMES)
        return result
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


def start_jekyll_serve(
    output_dir: Path,
    host: str,
    port: int,
    parser: argparse.ArgumentParser,
    verbose: bool = False,
) -> subprocess.Popen:
    """Launch Jekyll serve with livereload enabled."""
    jekyll_bin = shutil.which("jekyll")
    if jekyll_bin is None:
        parser.exit(
            status=2,
            message=(
                "mkpages: error: jekyll executable not found on PATH. "
                "Install Jekyll to use `mkpages serve`.\n"
            ),
        )

    validate_output_dir(output_dir, parser)
    threading.Timer(1.0, open_browser, args=(host, port)).start()
    process = subprocess.Popen(
        [
            jekyll_bin,
            "serve",
            "--source",
            str(output_dir),
            "--destination",
            str(output_dir / "_site"),
            "--host",
            host,
            "--port",
            str(port),
            "--livereload",
        ],
        stdout=None if verbose else subprocess.PIPE,
        stderr=None if verbose else subprocess.STDOUT,
        text=True if not verbose else None,
        bufsize=1 if not verbose else -1,
        start_new_session=True,
    )
    if not verbose:
        start_jekyll_output_filter(process)
    return process


def start_jekyll_output_filter(process: subprocess.Popen) -> None:
    """Drain Jekyll output and only surface useful lines in quiet mode."""
    if process.stdout is None:
        return

    def forward_output() -> None:
        assert process.stdout is not None
        stdout = process.stdout
        suppress_regenerating_block = False
        try:
            iterator = iter(stdout)
        except TypeError:
            return
        for raw_line in iterator:
            line = raw_line.strip()
            if suppress_regenerating_block:
                if is_regenerating_block_end(line):
                    suppress_regenerating_block = False
                continue
            if not line:
                continue
            if line.startswith("Regenerating:"):
                suppress_regenerating_block = True
                continue
            if should_suppress_jekyll_line(line):
                continue
            stream = sys.stderr if is_jekyll_error_line(line) else sys.stdout
            print(line, file=stream)
        close = getattr(stdout, "close", None)
        if callable(close):
            close()

    threading.Thread(target=forward_output, daemon=True).start()


def should_suppress_jekyll_line(line: str) -> bool:
    """Return True for expected Jekyll chatter that should stay hidden by default."""
    lowered = line.lower()
    if any(pattern in line for pattern in NOISY_JEKYLL_PATTERNS):
        return True
    if line.startswith("/usr/lib/ruby/") and "warning:" in lowered:
        return True
    return False


def is_regenerating_block_end(line: str) -> bool:
    """Return True when Jekyll finishes a regenerating block."""
    return "done in " in line.lower()


def is_jekyll_error_line(line: str) -> bool:
    """Return True for fatal-looking lines that should stay visible in quiet mode."""
    lowered = line.lower()
    if "warning:" in lowered:
        return False
    return "error" in lowered or "exception" in lowered or "traceback" in lowered


def stop_jekyll_process(process: subprocess.Popen) -> None:
    """Terminate the running Jekyll preview process."""
    if process.poll() is not None:
        return

    try:
        process_group = os.getpgid(process.pid)
    except ProcessLookupError:
        return

    os.killpg(process_group, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process_group, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def validate_output_dir(output_dir: Path, parser: argparse.ArgumentParser) -> None:
    """Ensure an output directory exists and looks like mkpages output."""
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


def sync_staged_output(
    staging_dir: Path, output_dir: Path, preserve_names: tuple[str, ...]
) -> None:
    """Copy a freshly generated staging tree into the live output tree."""
    output_dir.mkdir(parents=True, exist_ok=True)
    sync_directory_contents(staging_dir, output_dir)
    remove_stale_output_entries(staging_dir, output_dir, preserve_names)


def sync_directory_contents(source_dir: Path, destination_dir: Path) -> None:
    """Mirror files from a source tree into a destination tree without removing first."""
    for source_path in sorted(source_dir.rglob("*")):
        relative_path = source_path.relative_to(source_dir)
        destination_path = destination_dir / relative_path
        if source_path.is_dir():
            destination_path.mkdir(parents=True, exist_ok=True)
            continue
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        copy_file_atomically(source_path, destination_path)


def copy_file_atomically(source_path: Path, destination_path: Path) -> None:
    """Replace a destination file atomically using a temporary sibling."""
    temp_path = destination_path.with_name(f".{destination_path.name}.mkpages-tmp-{os.getpid()}")
    shutil.copyfile(source_path, temp_path)
    os.replace(temp_path, destination_path)


def remove_stale_output_entries(
    staging_dir: Path, output_dir: Path, preserve_names: tuple[str, ...]
) -> None:
    """Remove files and directories that no longer exist in the staged output."""
    for live_path in sorted(output_dir.rglob("*"), reverse=True):
        relative_path = live_path.relative_to(output_dir)
        if not relative_path.parts:
            continue
        if relative_path.parts[0] in preserve_names:
            continue
        if (staging_dir / relative_path).exists():
            continue
        if live_path.is_dir():
            try:
                live_path.rmdir()
            except OSError:
                continue
        else:
            live_path.unlink()


def build_source_snapshot(content_root: Path) -> dict[PurePosixPath, tuple[int, int]]:
    """Capture mtimes and sizes for source files that should trigger preview rebuilds."""
    snapshot: dict[PurePosixPath, tuple[int, int]] = {}
    for path in sorted(content_root.rglob("*")):
        if path.is_dir():
            continue
        rel_path = path.relative_to(content_root)
        if is_excluded(rel_path):
            continue
        stat = path.stat()
        snapshot[PurePosixPath(rel_path.as_posix())] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def detect_changed_paths(
    previous: dict[PurePosixPath, tuple[int, int]],
    current: dict[PurePosixPath, tuple[int, int]],
) -> tuple[PurePosixPath, ...]:
    """Return the sorted set of source paths that changed between snapshots."""
    changed = {
        path for path in previous.keys() | current.keys() if previous.get(path) != current.get(path)
    }
    return tuple(sorted(changed))


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
