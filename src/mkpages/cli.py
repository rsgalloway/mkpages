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
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from mkpages import __version__
from mkpages.generator import (
    CONFIG_FILE_NAME,
    OUTPUT_MARKER,
    MkpagesError,
    discover_export_documents,
    generate_site,
    is_excluded,
)

DEFAULT_OUTPUT_DIR = Path(".mkpages")
WATCH_POLL_INTERVAL = 0.5
JEKYLL_RUNTIME_NAMES = ("_site", ".jekyll-cache", ".jekyll-metadata", ".sass-cache")
EXPORT_FORMATS = ("docx", "pdf", "zip")
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
    parser.add_argument(
        "--url",
        dest="site_url",
        help="Canonical site origin to write to the generated Jekyll configuration.",
    )
    parser.add_argument(
        "--baseurl",
        dest="site_baseurl",
        help="Site subpath to write to the generated Jekyll configuration.",
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


def build_export_parser() -> argparse.ArgumentParser:
    """Create the export subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages export",
        description="Export a Markdown folder tree as PDF, DOCX, or a rendered site ZIP.",
    )
    add_source_argument(parser)
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        help="Output file path. The format is inferred from the extension unless --format is set.",
    )
    parser.add_argument(
        "--format",
        choices=EXPORT_FORMATS,
        help="Explicit export format override.",
    )
    return parser


def build_root_parser() -> argparse.ArgumentParser:
    """Create the top-level subcommand parser."""
    parser = argparse.ArgumentParser(
        prog="mkpages",
        description="Generate and preview Jekyll source trees from Markdown folder trees.",
        epilog=(
            "commands:\n"
            "  build     Generate a Jekyll source tree.\n"
            "  serve     Serve an existing generated site.\n"
            "  preview   Build and serve a Markdown tree (the default for a bare path).\n"
            "  export    Export a Markdown tree as PDF, DOCX, or a rendered site ZIP."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
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
    result = build_site(
        content_root,
        output_dir,
        theme_path,
        parser,
        site_url=args.site_url,
        site_baseurl=args.site_baseurl,
    )

    print_status(
        f"Built {result.pages_written} page(s) and copied {result.assets_copied} asset(s) into {result.output_dir}",
        kind="success",
    )
    print_generation_warnings(result)
    return 0


def run_serve(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Serve the existing generated site through Jekyll."""
    output_dir = Path(getattr(args, "output", DEFAULT_OUTPUT_DIR)).expanduser()
    process: subprocess.Popen | None = None
    try:
        process = start_jekyll_serve(
            output_dir,
            args.host,
            args.port,
            parser,
            verbose=args.verbose,
            open_browser_tab=True,
        )
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
    result = build_site(
        content_root,
        output_dir,
        theme_path,
        parser,
        dev_reload_token=next_dev_reload_token(),
        site_url=args.site_url,
        site_baseurl=args.site_baseurl,
    )
    print_status(
        f"Built {result.pages_written} page(s) and copied {result.assets_copied} asset(s) into {output_dir}",
        kind="success",
    )
    print_generation_warnings(result)

    process: subprocess.Popen | None = None

    snapshot = build_source_snapshot(content_root)
    try:
        process = start_jekyll_serve(
            output_dir,
            args.host,
            args.port,
            parser,
            verbose=args.verbose,
            open_browser_tab=True,
        )
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
                    dev_reload_token=next_dev_reload_token(),
                    site_url=args.site_url,
                    site_baseurl=args.site_baseurl,
                )
            except MkpagesError as exc:
                clear_transient_status()
                print_status(f"Rebuild failed: {exc}", kind="error", stream=sys.stderr)
                continue
            except Exception as exc:  # pragma: no cover
                clear_transient_status()
                print_status(f"Rebuild failed: {exc}", kind="error", stream=sys.stderr)
                continue

            if needs_restart:
                if args.verbose:
                    print_status(
                        "Restarting Jekyll to reload updated site configuration", kind="warning"
                    )
                stop_jekyll_process(process)
                process = start_jekyll_serve(
                    output_dir,
                    args.host,
                    args.port,
                    parser,
                    verbose=args.verbose,
                    open_browser_tab=False,
                )
                print_status(
                    f"Rebuilt {result.pages_written} page(s), copied {result.assets_copied} asset(s), and reloaded config",
                    kind="success",
                    transient=not args.verbose,
                )
                print_generation_warnings(result)
                continue

            print_status(
                f"Rebuilt {result.pages_written} page(s), copied {result.assets_copied} asset(s)",
                kind="success",
                transient=not args.verbose,
            )
            print_generation_warnings(result)
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


def run_export(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Export the Markdown tree as PDF, DOCX, or rendered-site ZIP."""
    content_root = Path(args.path).expanduser()
    if not content_root.exists():
        parser.error(f"content root does not exist: {content_root}")
    if not content_root.is_dir():
        parser.error(f"content root is not a directory: {content_root}")

    output_path = Path(args.output).expanduser()
    if output_path.exists() and output_path.is_dir():
        parser.error(f"output path is a directory: {output_path}")

    export_format = resolve_export_format(output_path, args.format, parser)
    if export_format in {"pdf", "docx"}:
        export_combined_document(content_root, output_path, export_format, parser)
    else:
        export_rendered_site_zip(content_root, output_path, parser)

    print_status(f"Exported {content_root} to {output_path}", kind="success")
    return 0


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


def resolve_export_format(
    output_path: Path, explicit_format: str | None, parser: argparse.ArgumentParser
) -> str:
    """Resolve the export format from an explicit override or output extension."""
    if explicit_format:
        return explicit_format

    suffix = output_path.suffix.lower().lstrip(".")
    if suffix in EXPORT_FORMATS:
        return suffix

    choices = ", ".join(EXPORT_FORMATS)
    parser.error(
        f"could not infer export format from output path: {output_path}. "
        f"Use a .pdf, .docx, or .zip extension, or pass --format ({choices})."
    )
    return ""


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


def print_generation_warnings(result) -> None:
    """Report non-fatal generation fallbacks through the normal CLI status UI."""
    warnings = getattr(result, "warnings", ())
    if not isinstance(warnings, tuple):
        return
    for warning in warnings:
        print_status(warning, kind="warning", stream=sys.stderr)


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


def next_dev_reload_token() -> str:
    """Return a changing token that preview pages can poll for restart-safe reloads."""
    return str(time.time_ns())


def build_site(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    parser: argparse.ArgumentParser,
    preserve_output_names: tuple[str, ...] = (),
    dev_reload_token: str | None = None,
    site_url: str | None = None,
    site_baseurl: str | None = None,
):
    """Generate the site or exit with a friendly parser error."""
    try:
        return generate_site_checked(
            content_root=content_root,
            output_dir=output_dir,
            theme_path=theme_path,
            preserve_output_names=preserve_output_names,
            dev_reload_token=dev_reload_token,
            site_url=site_url,
            site_baseurl=site_baseurl,
        )
    except MkpagesError as exc:
        parser.exit(status=2, message=f"mkpages: error: {exc}\n")
    except Exception as exc:  # pragma: no cover
        parser.exit(status=2, message=f"mkpages: error: unexpected build failure: {exc}\n")


def export_combined_document(
    content_root: Path,
    output_path: Path,
    export_format: str,
    parser: argparse.ArgumentParser,
) -> None:
    """Export the Markdown tree as one combined PDF or DOCX via Pandoc."""
    pandoc_bin = shutil.which("pandoc")
    if pandoc_bin is None:
        parser.exit(
            status=2,
            message="mkpages: error: PDF and DOCX exports require Pandoc. Install Pandoc and retry.\n",
        )

    input_paths = discover_export_documents(content_root)
    if not input_paths:
        parser.exit(
            status=2,
            message=f"mkpages: error: no Markdown files found under {content_root}\n",
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    completed = run_pandoc_export(pandoc_bin, input_paths, output_path)
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        if details:
            parser.exit(
                status=2,
                message=f"mkpages: error: pandoc {export_format} export failed:\n{details}\n",
            )
        parser.exit(status=2, message=f"mkpages: error: pandoc {export_format} export failed\n")


def run_pandoc_export(
    pandoc_bin: str, input_paths: list[Path], output_path: Path
) -> subprocess.CompletedProcess[str]:
    """Invoke Pandoc for one combined document export."""
    return subprocess.run(
        [pandoc_bin, *(str(path) for path in input_paths), "-o", str(output_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )


def export_rendered_site_zip(
    content_root: Path,
    output_path: Path,
    parser: argparse.ArgumentParser,
) -> None:
    """Export the rendered static site as a ZIP archive."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mkpages-export-") as tempdir:
        temp_root = Path(tempdir)
        source_output_dir = temp_root / ".mkpages"
        rendered_output_dir = temp_root / "_site"

        result = generate_site_checked(
            content_root=content_root,
            output_dir=source_output_dir,
            theme_path=None,
            preserve_output_names=("_site",),
        )
        print_generation_warnings(result)
        build_rendered_site(source_output_dir, rendered_output_dir, parser)
        write_zip_archive(rendered_output_dir, output_path)


def build_rendered_site(
    source_output_dir: Path, rendered_output_dir: Path, parser: argparse.ArgumentParser
) -> None:
    """Run Jekyll build for a generated mkpages source tree."""
    jekyll_bin = shutil.which("jekyll")
    if jekyll_bin is None:
        parser.exit(
            status=2,
            message=(
                "mkpages: error: ZIP exports require the jekyll executable on PATH. "
                "Install Jekyll and retry.\n"
            ),
        )

    completed = subprocess.run(
        [
            jekyll_bin,
            "build",
            "--source",
            str(source_output_dir),
            "--destination",
            str(rendered_output_dir),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout).strip()
        if details:
            parser.exit(status=2, message=f"mkpages: error: jekyll build failed:\n{details}\n")
        parser.exit(status=2, message="mkpages: error: jekyll build failed\n")


def write_zip_archive(source_dir: Path, output_path: Path) -> None:
    """Write a deterministic ZIP archive from a rendered site tree."""
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(source_dir.rglob("*")):
            if path.is_dir():
                continue
            archive_info = zipfile.ZipInfo(path.relative_to(source_dir).as_posix())
            archive_info.compress_type = zipfile.ZIP_DEFLATED
            archive_info.date_time = (1980, 1, 1, 0, 0, 0)
            archive_info.external_attr = 0o644 << 16
            archive.writestr(archive_info, path.read_bytes())


def generate_site_checked(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    preserve_output_names: tuple[str, ...] = (),
    dev_reload_token: str | None = None,
    site_url: str | None = None,
    site_baseurl: str | None = None,
):
    """Generate a site and raise regular Python exceptions for callers that want to recover."""
    return generate_site(
        content_root=content_root,
        output_dir=output_dir,
        explicit_theme=theme_path,
        preserve_output_names=preserve_output_names,
        allow_unmarked_reuse=output_dir.name == DEFAULT_OUTPUT_DIR.name,
        dev_reload_token=dev_reload_token,
        site_url=site_url,
        site_baseurl=site_baseurl,
    )


def rebuild_site_from_staging(
    content_root: Path,
    output_dir: Path,
    theme_path: Path | None,
    parser: argparse.ArgumentParser,
    dev_reload_token: str | None = None,
    site_url: str | None = None,
    site_baseurl: str | None = None,
):
    """Rebuild preview output via a staging tree to avoid tearing away live Jekyll inputs."""
    staging_root = Path(tempfile.mkdtemp(prefix=f"{output_dir.name}-staging-"))
    try:
        result = generate_site_checked(
            content_root,
            staging_root,
            theme_path,
            dev_reload_token=dev_reload_token,
            site_url=site_url,
            site_baseurl=site_baseurl,
        )
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
    open_browser_tab: bool = True,
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
    if open_browser_tab:
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
        start_new_session=os.name != "nt",
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

    if os.name == "nt":
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
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
    if root_args.command == "export":
        parser = build_export_parser()
        args = parser.parse_args(args_list[1:])
        return run_export(args, parser)
    if root_args.command:
        parser = build_preview_parser()
        args = parser.parse_args(args_list)
        return run_preview(args, parser)

    root_parser.print_usage(sys.stderr)
    print(
        "mkpages: error: a subcommand is required (build, serve, preview, or export)",
        file=sys.stderr,
    )
    return 2
