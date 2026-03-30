# -*- coding: utf-8 -*-

name = 'pxo_rigging_kit'

version = '3.0.0'

description = \
    """
    Globally rigging package. It will contain utility code for daily usage. Main reason is to establish a global rigging standard for all pxo facilities. And make cooperation easier for all facilites.
    """

authors = [
    'Johannes Manani',
    'rigging_council'
]

tools = [
    ' numpy and etc',
    ' OpenMaya',
    ' Paya',
    'Pymel'
]

requires = [
    'click-7',
    'maya-2022..2026',
    'maya_math_nodes-1+',
    'maya_mgear-5.1.3+',
    'maya_ng_skin_tools-2+',
    'maya_proxy_node-0+',
    'maya_pyblish_plugins-2.42.0+',
    'maya_pymel-1+',
    'maya_scene_io-0+',
    'maya_shapes-5.7.8-pxo.1+',
    'maya_studiolibrary-1+',
    'maya_utils-3.14.0+',
    'pixo_config-1+',
    'pixo_log-1+',
    'pixo_naming-2+',
    'pixo_paths-1+',
    'pixo_pyblish-0.80.0+',
    'pixo_shotgun-1+',
    'python-3.6+',
    'pydantic-2+',
    'scipy-1+',
    'setuptools-41+',
    'six-1+'
]

build_requires = []

def commands():
    """Set up package."""
    env.PATH.prepend("{this.root}/bin")  # noqa: F821
    env.PYTHONPATH.prepend("{this.root}/site-packages")  # noqa: F821
    env.PXO_MENU_CONFIG_PATH.prepend(
        "{this.root}/config/menu.yaml"
    )  # noqa: F821, E501  # pylint: disable=line-too-long
    env.XBMLANGPATH.append("{this.root}/icons")  # noqa: F821
    env.MAYA_SCRIPT_PATH.append("{this.root}/scripts")  # noqa: F821
    env._PXO_PYBLISHPLUGINPATH.append(
        "{this.root}/site-packages/pxo_rigging_kit/pyblish_plugins"
    )  # noqa: F821
    env.MAYA_PLUG_IN_PATH.append(
        "{this.root}/site-packages/pxo_rigging_kit/plug_ins"
    )  # noqa: F821
    env._PXO_TK_LOADER_HOOK_PATH.append(  # noqa: F821
        literal("{$REZ_PXO_RIGGING_KIT_ROOT}/hooks/sgtk/loader/maya_actions.py")
    )

uuid = 'bd25edbc-7309-4f8c-b707-6d1c826e84e0'

timestamp = 1771240265

_MAYA_TEST_COMMAND = 'pytest --cov=pxo_rigging_kit --pyargs pxo_rigging_kit'

format_version = 2

tests = \
    {'maya-2022': {'command': 'pytest --cov=pxo_rigging_kit --pyargs pxo_rigging_kit',
                   'requires': ['maya-2022',
                                'maya_mtoa',
                                'numpy-1.17.3',
                                'maya_pymel-1.4',
                                'pytest',
                                'pytest_cov',
                                'pytest_mock']},
     'maya-2025': {'command': 'pytest --cov=pxo_rigging_kit --pyargs pxo_rigging_kit',
                   'requires': ['maya-2025',
                                'maya_mtoa',
                                'maya_pymel',
                                'pytest',
                                'pytest_cov',
                                'pytest_mock']},
     'simple_import_test': {'command': 'python -c "import pxo_rigging_kit"'}}

homepage = 'https://gitlab.pixomondo.com/internal/pxo_rigging_kit'

dev_requires = [
    'click-7',
    'maya-2022..2026',
    'maya_math_nodes-1+',
    'maya_mgear-5.1.3+',
    'maya_ng_skin_tools-2+',
    'maya_proxy_node-0+',
    'maya_pyblish_plugins-2.42.0+',
    'maya_pymel-1+',
    'maya_scene_io-0+',
    'maya_shapes-5.7.8-pxo.1+',
    'maya_studiolibrary-1+',
    'maya_utils-3.14.0+',
    'pixo_config-1+',
    'pixo_log-1+',
    'pixo_naming-2+',
    'pixo_paths-1+',
    'pixo_pyblish-0.80.0+',
    'pixo_shotgun-1+',
    'python-3.6+',
    'pydantic-2+',
    'scipy-1+',
    'setuptools-41+',
    'six-1+',
    'pytest-3.6+',
    'pytest_cov-2.5+',
    'pytest_mock-1.10+'
]

_MAYA_REQUIRES = ('pytest', 'pytest_cov', 'pytest_mock')
