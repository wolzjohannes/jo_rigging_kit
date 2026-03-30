# Author:     Johannes Wolz / Lead Rigging TD

"""
Util code for custom python exceptions.
"""
# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

# Import built-in modules
from builtins import super

# Import third-party modules
from future import standard_library

standard_library.install_aliases()

##########################################################
# CLASSES
##########################################################


class MeshError(Exception):
    """
    Raised when there is something wrong with a maya mesh.
    """

    def __init__(self, message="There is something wrong with the mesh."):
        super(MeshError, self).__init__(message)


class DefaultSettingsArgumentError(Exception):
    """
    Raised when there is something wrong with a maya mesh.
    """

    def __init__(self, message="no key found in the settings dictionary that corresponds with argument."):
        super(DefaultSettingsArgumentError, self).__init__(message)


class DefaultSettingsImportError(Exception):
    """
    Raised when there is something wrong with a maya mesh.
    """

    def __init__(self, message="no key found in the settings dictionary that corresponds with argument."):
        super(DefaultSettingsImportError, self).__init__(message)


class DefaultSettingsSettingsError(Exception):
    """
    Raised when there is something wrong with a maya mesh.
    """

    def __init__(self, message="no key found in the settings dictionary that corresponds with argument."):
        super(DefaultSettingsSettingsError, self).__init__(message)


class BlendshapeError(Exception):
    def __init__(
        self, message="There is something wrong with the blendshape node."
    ):
        super(BlendshapeError, self).__init__(message)


class BlendShapeWeightDriverError(Exception):
    def __init__(self, message="Weight driver node is problematic."):
        super(BlendShapeWeightDriverError, self).__init__(message)


class MayaNodePortError(Exception):
    def __init__(self, message="Something is wrong with the port of the node."):
        super(MayaNodePortError, self).__init__(message)


class PixoNamingError(Exception):
    def __init__(self, message="Can not find the pattern in pixo_naming"):
        super(PixoNamingError, self).__init__(message)


class ShotgridError(Exception):
    def __init__(self, message="Something wrong with shotgrid."):
        super(ShotgridError, self).__init__(message)


class PxoModelAssetError(Exception):
    def __init__(self, message="Something wrong with the model asset."):
        super(PxoModelAssetError, self).__init__(message)


class PxoPymelNodeClassError(Exception):
    def __init__(
        self, message="Something is wrong with this custom pymel class."
    ):
        super(PxoPymelNodeClassError, self).__init__(message)


class MayaNodeNotFound(Exception):
    def __init__(self, message="Searched not not found."):
        super(MayaNodeNotFound, self).__init__(message)


class SkinclusterError(Exception):
    def __init__(
        self, message="There is something wrong with the skin cluster node."
    ):
        super(SkinclusterError, self).__init__(message)


class SkinPrecisionError(Exception):
    def __init__(
        self, message="There is something wrong with the skin precision mode."
    ):
        super(SkinPrecisionError, self).__init__(message)


class DeformerGeneralizedError(Exception):
    def __init__(
        self, message="There is something wrong with the deformer."
    ):
        super(DeformerGeneralizedError, self).__init__(message)

class DeformerHandlerError(Exception):
    def __init__(
        self, message="There is something wrong with the deformer."
    ):
        super(DeformerHandlerError, self).__init__(message)


class DeformerNotFoundError(Exception):
    def __init__(
        self, message="The deformer on this geo was not found."
    ):
        super(DeformerNotFoundError, self).__init__(message)


class TransformNotFoundError(Exception):
    def __init__(
        self, message="The transformwas not found."
    ):
        super(TransformNotFoundError, self).__init__(message)


class SzeneSetupError(Exception):
    def __init__(
        self, message="There is missing information in the PXO Scene setup."
    ):
        super(SzeneSetupError, self).__init__(message)


class AnimControllerInterfaceError(Exception):
    def __init__(
        self, message="Something is wrong with the animation controllers."
    ):
        super(AnimControllerInterfaceError, self).__init__(message)


class HikCharacterDefinitionError(Exception):
    def __init__(
        self, message="Something is wrong in your HIK Character Definition."
    ):
        super(HikCharacterDefinitionError, self).__init__(message)


class HikDataError(Exception):
    def __init__(self, message="Something is wrong with your hik data."):
        super(HikDataError, self).__init__(message)


class ModelAssetRootNodeError(Exception):
    def __init__(
        self, message="There is something wrong with the model asset root."
    ):
        super(ModelAssetRootNodeError, self).__init__(message)


class MayaSelectionError(Exception):
    def __init__(
        self,
        message="There is something wrong with your selection in the scene.",
    ):
        super(MayaSelectionError, self).__init__(message)


class MayaNodeNameUniqueness(Exception):
    def __init__(self, message="Your specified node has a not unique name."):
        super(MayaNodeNameUniqueness, self).__init__(message)


class MayaObjectSetError(Exception):
    def __init__(self, message="Maya object set failed."):
        super(MayaObjectSetError, self).__init__(message)


class ChopperError(Exception):
    def __init__(self, message="An error occured while chopping the mesh."):
        super(ChopperError, self).__init__(message)

class MayaNodeAttributeError(Exception):
    def __init__(self, message="An error occured while triggering a nodes attribute."):
        super(MayaNodeAttributeError, self).__init__(message)

class RigAssetAssemblyError(Exception):
    def __init__(self, message="An error occured processing the rig asset assembly node."):
        super(RigAssetAssemblyError, self).__init__(message)