from argparse import ArgumentParser, Namespace
from logging import getLogger

from sosci.cli import SUBCOMMANDS


def get_parser() -> ArgumentParser:
    """Create and return the argument parser for the SO campaign."""
    parser = ArgumentParser(description="Run the SO campaign.")
    # Make sure all args here are redirected to vars starting with
    # '_'.  We are going to clean those off before passing to the
    # subcommand.
    sps = parser.add_subparsers(dest='_pipemod', required=True)

    for name, module in SUBCOMMANDS.items():
        sp = sps.add_parser(name)
        module.get_parser(sp)

    return parser


def main() -> None:
    logger = getLogger(name="sosci")
    parser = get_parser()
    args = parser.parse_args()

    # Extract top-level args ...
    top_args = {k: v for k, v in vars(args).items()
                if k[0] == '_'}
    for k in top_args:
        delattr(args, k)
    top_args = Namespace(**top_args)

    module = SUBCOMMANDS[top_args._pipemod]
    _main = getattr(module, '_main', None)
    if _main is not None:
        _main(args, logger=logger)
