from pxo_rigging_kit.io_version_control import version_io
import importlib
import numpy as np
import pymel.core as pmc

importlib.reload(version_io)

io_manager = version_io.ImportExport()
#io_manager._debug_mode()

"""
import pxo_rigging_kit
from pxo_rigging_kit.io_version_control import io_vc_debug_tester
import importlib
importlib.reload(io_vc_debug_tester)

io_vc_debug_tester.test_short()

io_vc_debug_tester.test_long()
"""

def test_quick():
    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="abc"
    )

    io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="abc"
    )


def test_short():

    mesh = "Eag_01:chr_eagle_cornea_rt_geo"
    vertices = pmc.ls(f"{mesh}.vtx[*]", fl=True)
    vertex_array = np.array(
        [vertex.getPosition(space="world") for vertex in vertices]
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="ng"
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo",
        data_to_write=["this is a very complex file"],
        data_type="json",
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo",
        data_to_write=vertex_array,
        data_type="npy",
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="obj"
    )

    io_manager.write(object_name="skinCluster780", data_type="deformer_weights")

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="ma"
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="abc"
    )

    io_manager.write(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="mb"
    )

    io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="ng"
    )

    data = io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="json"
    )
    print(data)

    data = io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="npy"
    )

    mesh = io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="obj"
    )

    pmc.select(mesh)

    mesh = io_manager.load(
        object_name="skinCluster780", data_type="deformer_weights"
    )

    pmc.select(mesh)

    io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="abc"
    )


    io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="ma"
    )


    io_manager.load(
        object_name="Eag_01:chr_eagle_body_main_geo", data_type="mb"
    )

    print("SHORT TEST COMPLETED")


def test_long():
    mesh = "Eag_01:chr_eagle_cornea_rt_geo"
    vertices = pmc.ls(f"{mesh}.vtx[*]", fl=True)
    vertex_array = np.array(
        [vertex.getPosition(space="world") for vertex in vertices]
    )

    io_manager.write(
        object_name="body_long_test",
        data_type="ngskin",
        data_to_write=None,  # no needed data are generated
        node_to_export="Eag_01:chr_eagle_body_main_geo",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.write(
        object_name="body_long_test",
        data_type="json",
        data_to_write=["json datas"],  # no needed data are generated
        node_to_export=None,
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.write(
        object_name="body_long_test",
        data_to_write=vertex_array,
        data_type="npy",
        node_to_export=None,
        data_category="PXO_TEST_LONG",
        data_file_name="npy_someting",
        version=-1,
        as_path=False,
    )

    io_manager.write(
        object_name="body_long_test",
        data_type="obj",
        node_to_export="Eag_01:chr_eagle_body_main_geo",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.write(
        object_name="body_long_test",
        data_type="deformer_weights",
        node_to_export="skinCluster780",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.load(
        object_name="body_long_test",
        data_type="ngskin",
        receiver_node="Eag_01:chr_eagle_body_main_geo",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.load(
        object_name="body_long_test",
        data_type="json",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.load(
        object_name="body_long_test",
        data_type="npy",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.load(
        object_name="body_long_test",
        data_type="obj",
        data_category="PXO_TEST_LONG",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    io_manager.load(
        object_name="body_long_test",
        data_type="deformer_weights",
        data_category="PXO_TEST_LONG",
        receiver_node="skinCluster780",
        data_file_name=None,
        version=-1,
        as_path=False,
    )

    print("LONG TEST COMPLETED")
