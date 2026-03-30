"""Run command line interface."""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import third-party modules
import click
from future import standard_library

# Import local modules
from pxo_rigging_kit.core import func

standard_library.install_aliases()


@click.group(
    name="pxo_rigging_kit",
    context_settings={"help_option_names": ["-h", "--help"]},
)
def cli():
    """Perform some cli tasks."""
    func()
