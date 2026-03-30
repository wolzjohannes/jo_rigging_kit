"""Run cli."""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
from future import standard_library

# Import local modules
from pxo_rigging_kit.cli import cli as pxo_cli

standard_library.install_aliases()


def cli():
    """Run cli."""
    pxo_cli()


if __name__ == "__main__":
    cli()
