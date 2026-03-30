# Author:     Johannes Wolz / Lead Rigging TD

"""
Gui module for a simple logger text window.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import third-party modules
from future import standard_library

standard_library.install_aliases()
# Import third-party modules
import pymel.core as pmc

##########################################################
# GLOBAL
##########################################################

SCROLL_FIELD_HEIGHT = 500
SCROLL_FIELD_WIDTH = 500
WINDOW = ""

##########################################################
# FUNCTIONS
##########################################################


def show(titel, info_str):
    """
    Will show the window.

    Args:
        titel(str): The window title.
        info_str(str): The info text.

    """
    global WINDOW
    if pmc.window(WINDOW, exists=True):
        pmc.deleteUI(WINDOW)
    with pmc.window() as win:
        WINDOW = win
        with pmc.horizontalLayout():
            pmc.scrollField(
                height=SCROLL_FIELD_HEIGHT,
                width=SCROLL_FIELD_WIDTH,
                text=info_str,
                editable=False,
                wordWrap=False,
            )
    win.setTitle(titel)
    win.show()
