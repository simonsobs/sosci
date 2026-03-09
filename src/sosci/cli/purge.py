from argparse import ArgumentParser, Namespace
from logging import Logger
from pathlib import Path
from urllib.request import urlopen


def get_parser(parser: ArgumentParser) -> ArgumentParser:
    """Create and return a sub-argument parser for metadata purging."""
    parser.add_argument(
        "--file",
        "-f",
        type=str,
        required=True,
        help="Path to a local txt file or a URL to a txt file with the files we need to purge.",
    )
    parser.add_argument(
        "--base-path",
        type=str,
        help="Base path to prepend to the files listed in the file.",
        required=True
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run for testing.",
    )
    return parser


def _main(args: Namespace, logger: Logger) -> None:

    if args.file.startswith(("https://github.com/simonsobs/sosci/")):
        with urlopen(args.file) as response:
            files_to_purge = response.read().decode().splitlines()
    else:
        with open(args.file) as f:
            files_to_purge = f.read().splitlines()

    for filename in files_to_purge:
        filename = filename.strip()
        if not filename:
            continue
        file = Path(args.base_path) / filename
        if file.exists():
            if not args.dry_run:
                file.unlink()
            logger.info(f"Removed {filename}")