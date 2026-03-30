from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
#    asset decomposition
from future import standard_library
standard_library.install_aliases()
import os

import pymel.core as pm
from pxo_rigging_kit.maya_utils.rigging.legacy_rig_lib.utils import data

#   decompose the naming
full_location = os.environ.get('PXO_ASSET_ROOT', "")
asset_name = os.path.basename(full_location)
assets_path = os.path.dirname(full_location)
main_path = os.path.join(full_location, 'rig_prop')
skin_path = os.path.join(main_path, 'data', 'skincluster')

data.get_latest_element_interval()


print(full_location)
print(asset_name)
print(assets_path)
print(main_path)
print(skin_path)


def go_to_builder():
    pm.openFile(data.get_latest_element_interval(),
                force=True)
