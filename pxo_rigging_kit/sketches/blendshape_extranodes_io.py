# Import standart python modules
# Import built-in modules
import logging
import os
import pprint

# Import third-party modules
from maya import cmds
# Import third party modules
from pixo_paths import normalize
# Import maya modules
from pymel import core as pmc

# Import local modules
from pxo_rigging_kit import paths
from pxo_rigging_kit import versioncontrol_utils
# Import locals
from pxo_rigging_kit.maya_utils import decorators
from pxo_rigging_kit.maya_utils import paths_utils

##########################################################
# GLOBALS
##########################################################

_LOGGER = logging.getLogger(__name__ + ".py")
_LOGGER.setLevel(logging.INFO)
DECORATORS = decorators.Decorators()
DECORATORS.debug = True
DECORATORS.logger = _LOGGER

##########################################################
# DYNAMIC LOCALS
##########################################################
BLENDSHAPE_EXTRANODES_LOOKUP_EXPORT_NAME = "blendshape_extranodes_data"
BLENDSHAPE_EXTRANODES_DATA_LOCATION_FOLDER_NAME = "PXO_BLENDSHAPE_EXTRANODES"

_STOP_AT_NODETYPES = ("poseInterpolator", "transform", "weightDriver")


##########################################################
# DYNAMIC FUNCTIONS
##########################################################


def gather_blendshape_nodes():
    return pmc.ls(type="blendShape")


def graph_blendshape_nodes(blendshape_nodes):
    blendshape_nodes = [blendshape_node for blendshape_node
                        in blendshape_nodes
                        if blendshape_node.hasAttr("weight")
                        ]

    if not blendshape_nodes:
        return

    blendshape_nodes_graph = dict()

    for blendshape_node in blendshape_nodes:
        graphed_node = graph_node_net(blendshape_node)

        if not graphed_node:
            continue

        blendshape_nodes_graph[blendshape_node.shortName()] = graphed_node

    return blendshape_nodes_graph


def graph_node_net(blend_shape_node):
    connection_graph = list()
    for i in blend_shape_node.weight:
        input_attr = i
        connected_nodes = (i.listConnections())
        connected_attrs = (i.listConnections(plugs=True))

        if not connected_nodes and not connected_attrs:
            continue

        node_to_operate_on = connected_nodes[0]
        connection_subgraph = list()

        iteration_counter = 0

        while iteration_counter < 500:

            if node_to_operate_on.nodeType() in _STOP_AT_NODETYPES:
                break

            node_type_ = node_to_operate_on.nodeType()
            node_name_ = node_to_operate_on.shortName()

            to_attr = None
            from_attr = None
            input_connections = node_to_operate_on.listConnections(source=True,
                                                                   destination=False,
                                                                   plugs=True,
                                                                   connections=True
                                                                   )

            if input_connections:

                to_attr, from_attr = input_connections[0]

            node_attributes = compose_node_attributes(node_to_operate_on)

            connection_information = compose_node_info_dict(connected_attrs[0],
                                                            from_attr,
                                                            input_attr,
                                                            node_attributes,
                                                            node_name_,
                                                            node_type_,
                                                            to_attr,
                                                            )

            connection_subgraph.append(connection_information)

            new_connections = node_to_operate_on.listConnections(source=True, destination=False)

            if not new_connections:
                break

            node_to_operate_on = new_connections[0]
            iteration_counter += 1

        if connection_subgraph:
            connection_graph.append(connection_subgraph)

    return connection_graph


def compose_node_attributes(node_to_get_attrs):
    node_attributes = dict()
    for attr_ in node_to_get_attrs.listAttr(settable=True, connectable=True, output=True):

        if not pmc.objExists(attr_):
            continue

        try:

            node_attributes[str(attr_.longName())] = attr_.get()

        except RuntimeError:
            pass
    return node_attributes


def compose_node_info_dict(connected_attr,
                           from_attr,
                           input_attr,
                           node_attributes,
                           node_name_,
                           node_type_,
                           to_attr
                           ):

    connection_information = dict()

    connection_information["active_node"] = (node_type_, node_name_)
    connection_information["settings"] = node_attributes
    connection_information["input_attributes"] = ((from_attr.node().shortName(),
                                                   from_attr.shortName()
                                                   ),
                                                  (to_attr.node().shortName(),
                                                   to_attr.shortName()
                                                   )
                                                  )
    connection_information["output_attributes"] = ((connected_attr.node().shortName(),
                                                    connected_attr.shortName()
                                                    ),
                                                   (input_attr.node().shortName(),
                                                    input_attr.shortName()
                                                    )
                                                   )

    return connection_information


def kill_inbetween_data():

    blendshape_nodes = gather_blendshape_nodes()
    graphed_blendshape_nodes = graph_blendshape_nodes(blendshape_nodes)
    all_nodes_for_deletion = list()
    for graphed_blendshape_keys, graphed_blendshape_values in graphed_blendshape_nodes.items():
        nodes_per_blendshape_for_deletion = list()
        for weights_graphed in graphed_blendshape_values:
            out_attr = weights_graphed[0]["output_attributes"][1]
            in_attr = weights_graphed[-1]["input_attributes"][0]

            pmc.PyNode(in_attr[0]).attr(in_attr[1]).connect(pmc.PyNode(out_attr[0]).attr(out_attr[1]), f=True)

            nodes_per_blendshape_for_deletion.extend([item_["active_node"][1]
                                                      for item_
                                                      in weights_graphed
                                                      ]
                                                     )
        all_nodes_for_deletion.extend(nodes_per_blendshape_for_deletion)
    pprint.pprint(all_nodes_for_deletion)
    cmds.delete(all_nodes_for_deletion)
    # get first blendshape weight input attr
    # get last driver node output attr attr

    # force connect them
    # kill rest that is inbetween
    # -> scene is prepared for export


def save_blendshape_extranodes_data(export_path=None, prettyprint=True):
    """
    Save the skinlayer data as json file for a rebuild.

    Args:
        export_path(str): The export path
                          If None it auto generate a directory with version control
                          in the data directory of the asset we are working on.
                          But this requieres an PXO anv whihc you will have when you are working with PXO save/load.
                          Default is None.

        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    """
    blendshape_nodes = gather_blendshape_nodes()
    graphed_blendshape_nodes = graph_blendshape_nodes(blendshape_nodes)

    blendshape_extranodes_data = graphed_blendshape_nodes

    if not blendshape_extranodes_data:
        raise LookupError("No data dict exist for pre bind matrix transforms")

    if export_path:
        vers_lod_path = normalize(export_path)

    else:
        export_path = paths_utils.get_project_paths(pmc.sceneName())

        # general save operations
        export_path = os.path.join(
                export_path, BLENDSHAPE_EXTRANODES_DATA_LOCATION_FOLDER_NAME
        )
        paths.check_and_create_path(export_path)
        vers_lod_path = versioncontrol_utils.check_and_create_date(export_path)

    paths.write_json_file(
            blendshape_extranodes_data,
            vers_lod_path,
            "{}.json".format(BLENDSHAPE_EXTRANODES_LOOKUP_EXPORT_NAME),
    )
    if prettyprint:
        pprint.pprint(blendshape_extranodes_data)


def _read_blendshape_extranodes_data(import_path=None, prettyprint=True):
    """
    Reads the json data and returns the data as list filled with data dicts.

    Args:
        import_path(str): The json file path.
                          If None will take latest file found in the version control
                          directory of the assets data directory.
                          Default is None.
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    Returns:
        List: Filled with data dicts for each skinlayer.

    """
    if not import_path:
        import_path = paths_utils.get_project_paths(pmc.sceneName())

        import_path = normalize(
                os.path.join(import_path, BLENDSHAPE_EXTRANODES_DATA_LOCATION_FOLDER_NAME)
        )
        paths.check_and_create_path(import_path)

        vers_lod_path = versioncontrol_utils.get_latest_path(import_path)
    else:
        vers_lod_path = import_path

    data_lookup_file = paths.read_files_of_directory(vers_lod_path)

    if not data_lookup_file:
        raise LookupError("No file in {}".format(vers_lod_path))

    list_length = len(data_lookup_file)

    if list_length > 1:
        raise ValueError("Too many items in {}".format(vers_lod_path))

    json_file_location = normalize(
            os.path.join(
                    vers_lod_path,
                    "{}.json".format(BLENDSHAPE_EXTRANODES_LOOKUP_EXPORT_NAME),
            )
    )
    data_lookup_info = paths.read_json_file(json_file_location)
    if prettyprint:
        pprint.pprint(data_lookup_info)
    return data_lookup_info


def connect_blendshape_extranodes_data(import_path=None, prettyprint=True):
    """
    Load the skinlayer data from json file and rebuild the layer geos.

    Args:
        import_path(str): The json file path.
                          If None will take latest file found in the version control
                          directory of the assets data directory.
                          Default is None.
        prettyprint(bool): Will pretty print the data dict into the script editor.
                           Default is False.

    Returns:
        List: Created layer meshes as pmc.PyNodes.

    """
    blendshape_extranodes_data = _read_blendshape_extranodes_data(import_path, prettyprint)

    result = []
    for blendshape_node_name, blendshape_node_data_array in blendshape_extranodes_data.items():
        for blendshape_node_data in blendshape_node_data_array:
            for blendshape_node_info in blendshape_node_data:
                if pmc.objExists(blendshape_node_info["active_node"][1]):
                    active_node = pmc.PyNode(blendshape_node_info["active_node"][1])
                else:
                    active_node = pmc.createNode(blendshape_node_info["active_node"][0],
                                                 n=blendshape_node_info["active_node"][1]
                                                 )

                for attr_, val_ in blendshape_node_info["settings"].items():
                    try:
                        active_node.attr(attr_).set(val_)
                    except RuntimeError:
                        pass

            connect_from_dict(blendshape_node_data, "output_attributes")
            connect_from_dict(blendshape_node_data, "input_attributes")

    return result


def connect_from_dict(blendshape_node_data, dict_key_name):
    [pmc.PyNode(blendshape_node_info[dict_key_name][0][0]).attr(
            blendshape_node_info[dict_key_name][0][1]).connect(
            pmc.PyNode(blendshape_node_info[dict_key_name][1][0]).attr(
                    blendshape_node_info[dict_key_name][1][1]), f=True)
        for blendshape_node_info
        in blendshape_node_data
        if pmc.PyNode(blendshape_node_info[dict_key_name][1][0]).attr(
                    blendshape_node_info[dict_key_name][1][1]).get(settable=True)
    ]

# save_blendshape_extranodes_data(export_path=None, prettyprint=False)
# kill_inbetween_data()
# connect_blendshape_extranodes_data(import_path=None, prettyprint=False)
