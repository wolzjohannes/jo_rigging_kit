

import datetime
import inspect
import time
import logging
from pprint import pprint
import pathlib
from typing import Optional, Iterable

import numpy  # noqa: import error
import shutil

from future import standard_library
from pxo_rigging_kit import constants
from pxo_rigging_kit import paths
from pxo_rigging_kit.maya_utils import decorators, exceptions
from pxo_rigging_kit.maya_utils import dag_utils
from pxo_rigging_kit.maya_utils import model_utils
from pxo_rigging_kit.maya_utils import paths_utils
from pxo_rigging_kit.maya_utils import scene_utils

from maya import cmds  # noqa: import error
import pymel.core as pmc

try:
    # Import third-party modules
    import ngSkinTools2
    from ngSkinTools2 import api as ngst_api
    from ngSkinTools2.api import VertexTransferMode
    from ngSkinTools2.api import InfluenceMappingConfig
    from ngSkinTools2.api import import_export
    from ngSkinTools2.api import layers
    from ngSkinTools2.operations import removeLayerData
    from ngSkinTools2.ui import mainwindow as ng_main_window

except ModuleNotFoundError:
    pmc.warning("Unable to import ngSkinTools2")

##########################################################
# GLOBALS
##########################################################

standard_library.install_aliases()
_LOGGER = logging.getLogger(f"{__name__}.py")
_LOGGER.setLevel(logging.DEBUG)
DECORATORS = decorators.Decorators()
DECORATORS.debug = False
DECORATORS.logger = _LOGGER


##########################################################
# FUNCTIONS
##########################################################


class ImportExport(object):
    """
    ImportExport is a central class responsible for managing data operations within the system,
    capable of both importing and exporting various file types such as ngskin, json, npy, obj, and deformer_weights.
    The class automates key functionalities like data writing, retrieval, version control, directory management, and lookup table updates.
    It supports complex operations such as handling multiple versions of files and simplifying data access by managing data categories and file naming through system configurations (_FILE_TRANSLATOR).

    Functional Overview:
    - Automatic Data Writing/Retrieval:
            Directly writes to or retrieves data from specified data categories to ensure organized data management.
    - Version Control:
            Automatically manages file versions, creating new ones as necessary during export or fetching the latest for imports.
    - Default Data Category:
            Utilizes a default category determined by _FILE_TRANSLATOR if not specified, which simplifies the process of data operations.
    - Directory Management:
            Either creates or accesses directories named after the object involved, capable of handling multiple files if required.
    - Lookup Table Management:
            Updates and references a lookup table to efficiently access the latest file versions, enhancing operational speed and reliability.

    The variable name are consisted true all the class this is a list of the one used across varius definition but wit the same name and data type

    Parameters:
            string      object_name     : The name of the folder that will be created, if the node_to_export is None, will also be the name of the node to export. Multiple files can be saved within this folder if used multiple times.
            string      data_type       : The type of data to save. Choosing this parameter will also trigger the export process automatically. you can have use not only the specifi name but also other name, like ng or ngskin and you will have the same output, have a look at constant.DATA_NAMES_DICT
            any         data_to_write   : This parameter is used only when the type of file to be saved involves a data type storable in a variable. it can be the type of data you need to export
            string      node_to_export  : If you want to export a specific node rather than a variable. If not provided, it defaults to the value of object_name.
            string      data_category   : The data category is typically determined automatically by the script (_FILE_TRANSLATOR). However, you can specify a different category if needed.
            string      data_file_name  : The desired name for the file. If not specified, the file name will default to the object name with the appropriate extension. Custom names are permissible.
            int         version         : Specifies the version to export. Typically, this will be -1 to denote the latest or a newly created version.
            str/bool    as_path         : If set to true, returns only the path components (version_path, data_file_name, data_type). If set to "full", returns the full path.
            Path        object_path     : The path to the relative object
            Path        version_path    : The path to the relative version
            Path        full_path       : The full path included file name and extension

    Practical functionality:
        The main point of this manager is to make the import and export as simple as possible,
        this is why the import and export have very little argument needed to work in default mode
        If no other flag is given the script assume that:
                    you want to export or import the latest version,
                    the object_name is also the node_to_export and the data_file_name

        This allows us to have very simple code to import or export

        JSON
        io_manager.write(
                object_name="Eag_01:chr_eagle_body_main_geo",
                data_to_write=["this is a very complex file"],
                data_type="json",
        )
                data = io_manager.load(
                object_name="Eag_01:chr_eagle_body_main_geo", data_type="json"
        )

        NG_SKIN
        io_manager.write(
            object_name="Eag_01:chr_eagle_body_main_geo", data_type="ng"
        )
        io_manager.load(
            object_name="Eag_01:chr_eagle_body_main_geo", data_type="ng"
        )

        But you can have control on any flag and any detail needed,
        controlling not only the path but also the name file and the data_category and mutch more


        io_manager.write(
            object_name="body_long_test",
            data_type="ngskin",
            data_to_write=None,  # no needed data are generated
            node_to_export="Eag_01:chr_eagle_body_main_geo",
            data_category="PXO_TEST_LONG",
            data_file_name=None,
            version=-1,
            as_path=False
        )

        io_manager.load(
            object_name="body_long_test",
            data_type="json",
            data_category="PXO_TEST_LONG",
            data_file_name=None,
            version=-1,
            as_path=False
        )

        for more example have a look at the test file in the pxo_rigging_kit/test

    """

    _FILE_TRANSLATOR = {
        "skincluster_op": constants.PXO_FILEPATH_SKIN,
        "skincluster_utils_gui": constants.PXO_FILEPATH_SKIN,
        "blendshape_utils": constants.PXO_FILEPATH_BSHP,
        "io_vc_debug_tester": constants.PXO_FILEPATH_TEST,
        "skincluster_layering": constants.PXO_FILEPATH_SLYR,
        "skincluster_precision_mode": constants.PXO_FILEPATH_SPRC,
    }

    def __init__(self, *args, abstraction_layers=1):
        # the operations dict collects everything into a
        self.debug_mode = False
        self.print_execution_time = True
        self.start_time = time.time()

        self.data_path = pathlib.Path(paths_utils.get_project_paths(pmc.sceneName()))

        self.current_script_root = pathlib.Path(
            inspect.stack()[abstraction_layers][1]
        ).absolute()

        self.current_script_name = self.current_script_root.with_suffix("").name

        # collect_maya_datas
        self.user = paths_utils.get_user_name()
        self.scene_name = pmc.sceneName()

        self.rig_version = paths_utils.get_version_number_from_basename(
            self.scene_name
        )
        self.default_data_category = self._FILE_TRANSLATOR.get(
            self.current_script_name, constants.DEFAULT_DATA_FOLDER_NAME
        )
        # needed files
        self.created_paths = []
        self.versions_dict = {}

    def _debug_mode(self):
        self.debug_mode = True
        self.print_execution_time = True

        _LOGGER.setLevel(logging.DEBUG)
        _LOGGER.debug("Debug mode activate")
        _LOGGER.debug(self.current_script_name)

    def _compose_structural_data(self, *args):
        """
        Takes all the data, and constructs an operations dict from it.
        Non in use at the moment
        Returns: the collected data

        """

        json_dict = {
            "user": self.user,
            "scene name": self.scene_name,
            "rig_version": self.rig_version,
            "date": datetime.date.today().strftime("%Y-%m-%d"),
            "time": datetime.datetime.now().time().strftime("%H:%M:%S"),
        }

        return json_dict

    def _set_data_type_short_name(self, search_value):
        """
        given a data type it will change the data type to a standard value look in
        constants.DATA_NAMES_DICT
        :param search_value:  string of data type - 'deformer_weights'
        :return: the data type in a short format - xml
        """

        for key, values in constants.DATA_NAMES_DICT.items():
            if search_value in values:
                return str(key)  # Return the key if the value is found
        return None

    @DECORATORS.x_timer
    def write(
        self,
        object_name,
        data_type,
        data_to_write=None,
        node_to_export=None,
        data_category=None,
        data_file_name=None,
        version=-1,
        as_path=False,
    ):
        """
        This function is central to managing and exporting data within the system. You can export different kind of files and format
        ngskin - json - npy - obj - deformer_weights

        the version control will take care of everything related paths

        Other Key Functionalities Include:
        - Automatic Data Writing: The function writes data directly into a specified data category. This ensures that data are organized according to predefined categories without manual intervention.
        - Version Control: If the object does not already have a version created, the function will generate a new version automatically. This feature helps in maintaining the integrity and traceability of data over time.
        - Default Data Category: In cases where a data category is not explicitly specified, the function uses a default category determined by the _FILE_TRANSLATOR configuration. This default setting simplifies the export process when specific categorization criteria are not necessary.
        - Directory Creation: Automatically creates a folder named after the `object_name` parameter within the designated data category. This folder can house multiple files if the function is invoked several times with the same object name, untlill the same class declaration
        - Automatic Version Management: The system handles versioning of the data files automatically, ensuring that the latest version is always readily identifiable and accessible.
        - Post-Write Verification: After data is written, the file undergoes a verification process to check for any potential errors.
        - Lookup Table Update: Adds the latest file to a lookup table, enhancing the accessibility and reference speed for future queries or operations.

        Parameters:
            string      object_name     : The name of the object to export. This name also serves as the folder name. Multiple files can be saved within this folder if used multiple times.
            string      data_type       : The type of data to save. Choosing this parameter will also trigger the export process automatically. Refer to the main documentation for more details.
            any         data_to_write   : This parameter is used only when the type of file to be saved involves a data type storable in a variable.
            string      node_to_export  : If you want to export a specific node rather than a variable. If not provided, it defaults to the value of object_name.
            string      data_category   : The data category is typically determined automatically by the script (_FILE_TRANSLATOR). However, you can specify a different category if needed.
            string      data_file_name  : The desired name for the file. If not specified, the file name will default to the object name with the appropriate extension. Custom names are permissible.
            int         version         : Specifies the version to export. Typically, this will be -1 to denote the latest or a newly created version.
            str/bool    as_path         : If set to true, returns only the path components (version_path, data_file_name, data_type). If set to "full", returns the full path.
            string      receiver_node   : If you want to import data related to a specific node rather than a variable. If not provided, it defaults to the value of object_name.

        Returns:
            :return: True if the operation completes successfully, indicating all processes, including checks and updates, were executed without errors.

        """

        write_start_timer = time.time()
        data_type = self._set_data_type_short_name(data_type)

        ##### CHECKS AND PREPARATION #####
        self._compose_structural_data()

        if data_type != "npy":
            if not data_to_write:
                data_to_write = object_name

        if not node_to_export:
            node_to_export = object_name

        if not data_category:
            data_category = self.default_data_category

        object_name = object_name.replace(":", constants.SEPARATOR)

        if not data_file_name:
            data_file_name = object_name

        #### GATHERING DATA FOR PATH AND VERSIONS ####
        version_path = self._create_path(object_name, data_category, version)
        full_path = version_path / pathlib.Path(f"{data_file_name}.{data_type}")

        if as_path:
            if as_path == "full":
                return full_path
            else:
                return version_path, data_file_name, data_type

        if full_path.exists():
            _LOGGER.error(f"{data_file_name}.{data_type} already exist")
            return

        #### EXPORTING ####
        if "npy" == data_type:
            self._write_numpy(
                array=data_to_write,
                data_file_name=data_file_name,
                version_path=version_path,
            )

        if "json" == data_type:
            self._write_json(data_to_write,
                             version_path,
                             data_file_name
                             )

        if "obj" == data_type:
            self._write_obj(node_to_export=node_to_export,
                            full_path=full_path
                            )

        if "ng" == data_type:
            self._write_ng(
                node_to_export=node_to_export,
                version_path=version_path,
                data_file_name=data_file_name,
            )

        if "xml" == data_type:
            self._write_xml(
                data_file_name=data_file_name,
                node_to_export=node_to_export,
                version_path=version_path,
            )

        if data_type in {"mb", "ma"}:
            self._export_maya(
                node_to_export=node_to_export,
                full_path=full_path,
                data_type=data_type,
            )

        if "abc" == data_type:
            self._export_alembic(
                node_to_export=node_to_export, full_path=full_path
            )

        # fbx
        # usd ? pipelin
        if self.check_and_cleanup(full_path):
            execution_time = str((time.time() - write_start_timer))
            _LOGGER.info(
                f"EXPORTED:   {data_category:10} | {data_type:5} | {data_file_name} | {execution_time:4}"
            )

            self.add_to_look_up_table(
                file_name_ext=f"{data_file_name}.{data_type}",
                version_path=version_path,
            )

        return True

    @DECORATORS.x_timer
    def load(
        self,
        object_name,
        data_type,
        data_category=None,
        data_file_name=None,
        receiver_node=None,
        version=-1,
        as_path=False,
    ):
        """
        This function is central to managing and importing data within the system. You can import various file types and formats:
        ngskin - json - npy - obj - deformer_weights

        Version control will handle everything related to paths.

        Other Key Functionalities Include:
        - Automatic Data Retrieval: The function retrieves data directly from a specified data category and folder.
        - Default Data Category: If a data category is not explicitly specified, the function uses a default category determined by the _FILE_TRANSLATOR configuration. This default setting simplifies the import process when specific categorization criteria are not necessary.
        - Directory Access: Automatically accesses a folder named after the `object_name` parameter within the designated data category.
        - Lookup Table Reference: References the latest file from a lookup table, enhancing the accessibility and reference speed for future queries or operations.

        Parameters:
            :param object_name: The name of the object to import. This name also serves as the folder name. Multiple files can be retrieved from this folder if used multiple times.
            :param data_type: The type of data to retrieve. Selecting this parameter will also trigger the import process automatically. Refer to the main documentation for more details.
            :string receiver_node: If you want to import data related to a specific node rather than a variable. If not provided, it defaults to the value of object_name.
            :param data_category: The data category is typically determined automatically by the script (_FILE_TRANSLATOR). However, you can specify a different category if needed.
            :param data_file_name: The desired name for the file. If not specified, the file name will default to the object name with the appropriate extension. Custom names are permissible.
            :param version: Specifies the version to import. Typically, this will be -1 to denote the latest or most recent version.
            :param as_path: If 'full', returns the full path of the data file. If True, returns only the path components (version_path, data_file_name, data_type).

         Returns:
            :return: True if the import operation completes successfully, indicating all processes, including checks and updates, were executed without errors.
        """
        load_start_time = time.time()
        data_type = self._set_data_type_short_name(data_type)
        return_val = None

        ##### CHECKS AND PREPARATION #####
        if not receiver_node:
            receiver_node = object_name

        if not data_category:
            data_category = self.default_data_category

        object_name = object_name.replace(":", constants.SEPARATOR)

        if not data_file_name:
            data_file_name = object_name

        if not data_file_name:
            data_file_name = object_name.replace(":", constants.SEPARATOR)

        #### GATHERING DATA FOR PATH AND VERSIONS ####
        version_path = self.get_version_path(
            object_name, data_category, version, data_file_name, data_type
        )

        full_path = version_path / pathlib.Path(f"{data_file_name}.{data_type}")

        # TODO: here is where we will hook into <3
        if as_path:

            if as_path == "full":
                return full_path

            else:
                return version_path, data_file_name, data_type

        if "npy" == data_type:
            return_val = self._read_numpy(full_path)

        if "json" == data_type:
            _LOGGER.debug(str(version_path) + " version_path")
            data = self._read_json(version_path, data_file_name)
            _LOGGER.debug(data)
            return_val = data

        if "obj" == data_type:
            return_val = self._read_obj(version_path, data_file_name)

        if "ng" == data_type:
            self._read_ng(reciver_node=receiver_node, full_path=full_path)

        if "xml" == data_type:
            self._read_xml(
                data_file_name=data_file_name,
                deformer=receiver_node,
                version_path=version_path,
            )
        if data_type in {"mb", "ma"}:
            return_val = self._import_maya(
                version_path=version_path,
                data_file_name=data_file_name,
                data_type=data_type,
            )

        if "abc" == data_type:
            self._import_alembic(full_path=full_path)

        execution_time = str((time.time() - load_start_time))

        _LOGGER.info(
            f"IMPORTED:   {data_category:10} | {data_type:4} | {data_file_name:10} | {execution_time:4}"
        )

        if return_val is not None:
            return return_val

    def _write_numpy(self, array, data_file_name, version_path):
        path = version_path / pathlib.Path(data_file_name)
        numpy.save(path, array, allow_pickle=False, )

    def _read_numpy(self, full_path):
        _LOGGER.debug(full_path)
        return numpy.load(
            full_path,
            mmap_mode=None,
            allow_pickle=False,
            encoding="ASCII",
        )

    def _write_json(self, data, file_path, file_name):
        paths.write_json_file(data, file_path, f"{file_name}.{constants.JSON}")

    def _read_json(self, file_path, file_name):
        path = file_path / file_name
        path = (
            pathlib.Path(path).with_suffix(f".{constants.JSON}")
            if pathlib.Path(path).suffix != f".{constants.JSON}"
            else path
        )
        return paths.read_json_file(str(path))

    def _write_obj(self, node_to_export, full_path):
        _LOGGER.debug(str(node_to_export) + "  " + str(full_path))
        model_utils.save_mesh_obj(str(full_path), node_to_export)

    def _read_obj(self, version_path, data_file_name):
        path = version_path / pathlib.Path(f"{data_file_name}.obj")
        node = model_utils.load_mesh_obj(path)
        return node

    def _write_ng(self, node_to_export, version_path, data_file_name):
        # load plugin for ng2

        # load plugin for ng2
        if not cmds.pluginInfo(constants.NG_PLUGIN_EXECUTABLE, query=True, loaded=True):

            try:
                cmds.loadPlugin(constants.NG_PLUGIN_EXECUTABLE)

            except ImportError:
                _LOGGER.error("Plugin not found")

        ng_main_window.workspace_control_permanent_script()

        name_to_export = f"{node_to_export.longName()}"

        if not layers.get_layers_enabled(name_to_export):

            ng_layer = layers.init_layers(name_to_export)
            ng_layer.add("exportLayer")

        import_export.export_json(
            name_to_export,
            file=str(version_path / pathlib.Path(f"{data_file_name}.{constants.JSON}")),
        )
        pmc.delete(
            removeLayerData.remove_custom_nodes(interactive=False,
                                                meshes=[name_to_export],
                                                )
        )

    def _read_ng(
        self, reciver_node, full_path, vertex_match=False, naming_glob=None
    ):
        """
        Imports the skin cluster from json file and applies it to the object.

        """
        # load plugin for ng2
        if not cmds.pluginInfo(constants.NG_PLUGIN_EXECUTABLE, query=True, loaded=True):

            try:
                cmds.loadPlugin(constants.NG_PLUGIN_EXECUTABLE)
            except ImportError:
                print("Plugin not found")

        ng_main_window.workspace_control_permanent_script()

        # asdfasdf
        config = InfluenceMappingConfig()
        config.use_label_matching = False
        config.use_dg_link_matching = False
        config.use_distance_matching = True
        config.use_name_matching = False

        if naming_glob:
            config.globs = naming_glob
            config.use_name_matching = True
            config.use_distance_matching = False

        if not vertex_match:
            transfer_modus = VertexTransferMode.closestPoint
        else:
            transfer_modus = VertexTransferMode.vertexId

        import_export.import_json(
            reciver_node,
            file=str(full_path),
            vertex_transfer_mode=transfer_modus,
            influences_mapping_config=config.transfer_defaults(),
        )

    def _write_xml(self, data_file_name, node_to_export, version_path):
        pmc.deformerWeights(
            f"{data_file_name}.xml",
            path=version_path,
            export=True,
            deformer=node_to_export,
        )

    def _read_xml(self, data_file_name, deformer, version_path):
        _LOGGER.debug(f"version Path {version_path}")

        pmc.deformerWeights(
            f"{data_file_name}.xml",
            path=str(version_path),
            im=True,
            deformer=deformer,
        )

    def _export_maya(self, node_to_export, full_path, data_type):
        _extension_dict = {"mb": "mayaBinary",
                           "ma": "mayaAscii",
                           }

        file_extension = _extension_dict.get(data_type, "mayaAscii")

        sel = pmc.ls(sl=True)

        export_name_adaption = f"{node_to_export}_EXPORT"

        namespace_subversion_adaption = export_name_adaption.replace(
            constants.NAMESPACE, constants.SEPARATOR
        )

        dupl_to_export = pmc.duplicate(
            node_to_export, n=namespace_subversion_adaption
        )[0]

        pmc.parent(dupl_to_export, world=True)

        dag_utils.delete_hidden_shapes(dupl_to_export)

        group_ids = dupl_to_export.getShape().listConnections(type="groupId") or []
        group_parts = dupl_to_export.getShape().listConnections(type="groupParts") or []

        pmc.delete(group_ids + group_parts)
        pmc.delete(dupl_to_export, ch=True)

        scene_utils.delete_unkown_plugins()
        scene_utils.delete_unkown_nodes()

        pmc.select(cl=True)
        pmc.select(dupl_to_export)

        pmc.system.exportSelected(
            full_path,
            force=True,
            options="v=0;",
            type=file_extension,
            shader=False,
            constructionHistory=False,
        )

        pmc.delete(dupl_to_export)
        pmc.select(sel)

    def _import_maya(self, version_path, data_file_name, data_type):
        _extension_dict = {"mb": "mayaBinary",
                           "ma": "mayaAscii",
                           }

        file_path = version_path / pathlib.Path(f"{data_file_name}.{data_type}")

        file_extension = _extension_dict.get(data_type, "mayaAscii")

        imported_objects = pmc.system.importFile(
            str(file_path),
            type=file_extension,
            i=True,
            returnNewNodes=True,
            defaultNamespace=True,
        )

        for x in imported_objects:
            x.rename(x.shortName().replace(constants.SEPARATOR,
                                           constants.NAMESPACE,
                                           )
                     )
            x.rename(x.shortName().replace("EXPORT", "IMPORT"))

        return imported_objects

    def _export_alembic(self, node_to_export, full_path):
        sel = pmc.ls(sl=True)

        dupl_to_export = pmc.duplicate(
            node_to_export, name=f"{node_to_export}_EXPORT"
        )[0]
        pmc.parent(dupl_to_export, world=True)
        dag_utils.delete_hidden_shapes(dupl_to_export)
        pmc.select(clear=True)
        pmc.select(dupl_to_export)

        alembic_options = (f"-frameRange 1 1 -uvWrite -worldSpace "
                           f"-writeVisibility -dataFormat ogawa -root {dupl_to_export}"
                           )

        pmc.AbcExport(j=f"{alembic_options} -file {full_path}")

        pmc.delete(dupl_to_export)
        pmc.select(sel)

    def _import_alembic(self, full_path):
        pmc.AbcImport(str(full_path), mode="import")

    # Path handling
    def _create_path(self, object_name, data_category, version=-1):
        """
        It will create the path to the relative version, if the path exist will just return the path.
        If -1 will create a new one, but only the first time this is called.

        the path will be the following:
             self.data_path / data_category / object_name / version


        :param string object_name:
        :param WindowsPath data_category:
        :param WindowsPath version:
        :return: the version path of the indicated version
        """
        object_path = self.get_object_path(object_name, data_category)

        pathlib.Path(object_path).mkdir(parents=True, exist_ok=True)

        vers_list = self.get_versions(
            data_category=data_category, object_name=object_name
        )

        version_path = object_path / pathlib.Path(vers_list[version])
        pathlib.Path(version_path).mkdir(parents=True, exist_ok=True)
        return version_path

    def get_object_path(self, object_name, data_category):
        """
        it will create the object path but it will not be created, if in the object name is present a ":" will be replaced with constants.SEPARATOR

        :return: Path object_path the path to the relative object
        """
        if ":" in object_name:
            object_name = object_name.replace(":", constants.SEPARATOR)

        object_path = self.data_path / pathlib.Path(data_category) / pathlib.Path(object_name)
        return object_path

    def get_versions(
        self,
        data_category,
        object_name,
    ):
        """
        get all version into the object_path if is not present in th the self.versions_dict will add it and create a new
        version this is done to avoid creating multiple version when saving multiple files,

        :param object_name:
        :param data_category:
        :return: the list of versions present in the folder plus one,
        """
        object_path = self.get_object_path(
            data_category=data_category, object_name=object_name
        )

        if object_name in self.versions_dict:
            _LOGGER.debug(
                f"{object_name} latest version already created returning current versions"
            )
            return self.versions_dict[object_name]

        elif object_path.exists():
            dir_names = list_directories(object_path)

            if not dir_names:
                _LOGGER.debug(f"{object_name} first version created.")
                self.versions_dict[object_name] = ["001"]
                return self.versions_dict[object_name]

            dir_sorted = sorted(dir_names)

            latest_version = str(int(dir_sorted[-1]) + 1).zfill(3)

            _LOGGER.debug(
                f"{object_name} creating new version {latest_version}"
            )
            dir_sorted.append(latest_version)

            self.versions_dict[object_name] = dir_sorted

            return self.versions_dict[object_name]

        _LOGGER.debug(f"{object_name} first version created.")
        self.versions_dict[object_name] = ["001"]

        return self.versions_dict[object_name]

    def get_version_path(
        self, object_name, data_category, version, data_file_name, data_type
    ):
        """
        It will get the version path of the specified version if -1 will create a new if is the first iteration


        :return: version_path as Path
        """

        _LOGGER.debug("###### get_version_path #####")
        object_path = self.data_path / pathlib.Path(data_category) / pathlib.Path(object_name)

        _LOGGER.debug(f"object_path = {object_path}")

        get_version_time = time.time()
        if version == -1:
            vers_dict = self._read_json(object_path, constants.LOOK_UP_IO)

            _LOGGER.debug(f"vers_dict = {vers_dict} {data_type}")

            if f"{data_file_name}.{data_type}" in vers_dict:

                version = vers_dict[f"{data_file_name}.{data_type}"]
                _LOGGER.debug(f"version: {version}")

                version_path = pathlib.Path(object_path) / pathlib.Path(version)
                if version_path.exists():
                    _LOGGER.debug(version_path)
                    _LOGGER.debug(
                        f"EXECUTION = {time.time() - get_version_time}"
                    )

                    return version_path
                else:
                    _LOGGER.debug("file not found")
                    raise FileNotFoundError(version_path)
        else:
            _LOGGER.debug("Version is not last searching manually")
            _LOGGER.debug(data_file_name + " + " + object_path)

            files = find_files(object_path, data_file_name)
            _LOGGER.debug(files)

            for file in files:
                f = pathlib.Path(file).parents[0].name
                if int(f) == version:
                    _LOGGER.debug("Found matching version")
                    version_path = pathlib.Path(object_path) / f
                    return version_path
                else:
                    raise FileNotFoundError("Version not found")

            _LOGGER.debug(
                "EXECUTION = " + str((time.time() - get_version_time))
            )

    def add_to_look_up_table(self, file_name_ext, version_path):
        """
        the look-up table is used to quicky acces the latest version, this definition will add the latest created file to the look_up_table
        the look_up_table is store into the object_path

        :param file_name_ext:
        :param version_path:
        :return:
        """
        look_up_path = version_path.parent
        version = version_path.name

        look_up_file_path = look_up_path / pathlib.Path(constants.LOOK_UP_IO + ".json")

        if look_up_file_path.exists():
            look_up_data = self._read_json(look_up_path, constants.LOOK_UP_IO)
            look_up_data[file_name_ext] = version

        else:
            _LOGGER.info(
                f"no look_up_file_path for {file_name_ext} creating a new one"
            )

            look_up_data = {file_name_ext: version}

        self._write_json(
            data=look_up_data,
            file_path=look_up_path,
            file_name=constants.LOOK_UP_IO,
        )

    def check_and_cleanup(self, file_path):
        """
        Checks if a file exists at the specified path. If the file does not exist,
        and the containing directory is empty, it deletes the directory.

        Args:
        file_path (str): The full path to the file.
        """
        path = pathlib.Path(file_path)

        if not path.exists():
            directory = path.parent
            if not any(directory.iterdir()):  # Check if directory is empty
                shutil.rmtree(
                    str(directory)
                )  # Convert Path object to string for shutil.rmtree
                pmc.warning(
                    f"Exported file not found, directory was empty and has been deleted."
                )
            else:
                pmc.warning(
                    f"Exported file not found, Directory  is not empty, not deleting."
                )
            return False

        else:
            return True

    def get_version_controlled_directories(self, data_category):
        object_path = self.data_path / data_category

        found_dirs = list_directories(object_path)

        if not found_dirs:
            raise FileNotFoundError(f"No valid directories found in : {object_path}")

        _LOGGER.info(f"Found: {found_dirs}")

        return found_dirs


def ng_plugin_check():
    if not pmc.pluginInfo(constants.NG_PLUGIN_EXECUTABLE, query=True, loaded=True):
        try:
            pmc.loadPlugin(constants.NG_PLUGIN_EXECUTABLE)

        except ImportError:
            _LOGGER.error("ngSkinTools2 plugin not found")
            return False
    return True


def list_directories(path):
    directories_ = set()
    path_obj = pathlib.Path(path)

    for entry in path_obj.iterdir():
        if entry.is_dir():
            directories_.add(entry.name)

    return directories_


def list_scene_directory_overlap(scene_items: set,
                                 directory: pathlib.Path,
                                 ) -> Iterable:
    """
    Searches the version controlled files in the data path, sorts them returns them, also writes the location data.
    Can be found in [self.exported_directories_list] and is in correspondence with [self.exported_geo_nodes_list].

    Returns:
        List: [self.exported_geo_nodes_list]
    """
    overlap_sorted = []

    if not directory:
        _LOGGER.error("No directory was given. Returning an empty list.")
        return overlap_sorted

    directories = list_directories(directory)

    directories_namespace_corr_ = set(dir_name.replace(constants.SEPARATOR,
                                                       constants.NAMESPACE,
                                                       )
                                      for dir_name
                                      in directories
                                      )

    overlap = directories_namespace_corr_ & scene_items

    _LOGGER.debug(f"Scene found geos: {scene_items}\n"
                  f"Dir found geos: {directories_namespace_corr_}\n"
                  f"Overlap: {overlap}"
                  )

    if not overlap:
        return overlap_sorted

    overlap_sorted = sorted([x for x in overlap])

    return overlap_sorted


def find_files(root_folder, filename_without_extension):
    found_files = []
    root_path = pathlib.Path(root_folder)

    pattern = f"{filename_without_extension}.*"  # Search for files with any extension

    found_files = [str(file_path.resolve()) for file_path
                   in root_path.rglob(pattern)
                   if file_path.stem == filename_without_extension
                   ]

    return found_files
