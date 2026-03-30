# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import str
import pprint

# Import third-party modules
from future import standard_library
import pymel.core as pmc

standard_library.install_aliases()


HEIGHT = 510
WIDTH = 720
SEPARATOR_HEIGHT = 10
TEXTFIELD_HEIGHT = 20
SCROLL_FIELD_HEIGHT = 200


def show(gui_data_list):
    titel = "Rig meta data log."
    with pmc.window(titel) as win:
        if win.exists(titel):
            pmc.deleteUI(titel)
        with pmc.tabLayout(innerMarginWidth=5, innerMarginHeight=5) as tab:
            for data_dict in gui_data_list:
                asset_name = data_dict["asset_name"]
                meta_data_dict = data_dict["meta_data"]
                asset_assembly_data = data_dict.get("asset_assembly_data")
                assembly_text = "None"
                if asset_assembly_data:
                    assembly_text = pprint.pformat(asset_assembly_data)
                with pmc.paneLayout(configuration="horizontal2", st=20) as pan:
                    with pmc.scrollLayout(
                        horizontalScrollBarThickness=16,
                        verticalScrollBarThickness=16,
                    ):
                        with pmc.columnLayout(adj=True, width=700):
                            for index, key in enumerate(
                                sorted(list(meta_data_dict.keys()))
                            ):
                                pmc.separator(height=SEPARATOR_HEIGHT)
                                with pmc.frameLayout(
                                    borderVisible=False, labelVisible=True, label=key
                                ):
                                    textfield_color = (0.2, 0.2, 0.2)
                                    text = str(meta_data_dict.get(key))
                                    pmc.textField(
                                        height=TEXTFIELD_HEIGHT,
                                        text=text,
                                        editable=False,
                                        fn="boldLabelFont",
                                        bgc=textfield_color,
                                        ebg=True,
                                    )
                    pmc.scrollField(
                        height=SCROLL_FIELD_HEIGHT,
                        text=assembly_text,
                        editable=False,
                        wordWrap=False,
                    )
                tab.setTabLabel((pan, asset_name))
        win.setWidth(WIDTH)
        win.setHeight(HEIGHT)
        win.setSizeable(False)
        win.show()
