from . import metadata  # noqa: F401
from . import purge  # noqa: F401

SUBCOMMANDS = {"metadata-sync": metadata, "metadata-purge": purge}
