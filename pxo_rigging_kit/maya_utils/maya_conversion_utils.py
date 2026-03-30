"""
PyConvert - Convert mGear PyMaya objects to PyMel
Only converts pymaya objects, everything else passes through unchanged
"""

import pymel.core as pmc
from typing import Any, Union, List, Tuple, Set
import warnings

# Check if mgear is available
try:
    import mgear.pymaya as mgear_pm
    HAS_MGEAR = True
except ImportError:
    HAS_MGEAR = False


def pymaya_to_pymel(*args, v: bool = False) -> Any:
    """Convert mgear.pymaya objects to pymel.core

    Args:
        *args: Any number of objects to convert
        v: Verbose mode for debugging

    Returns:
        Converted object(s) preserving original structure

    Raises:
        RuntimeError: If pymaya conversion fails
    """
    if not args:
        warnings.warn("pyconvert: No arguments provided")
        return None

    # Multiple arguments
    if len(args) > 1:
        if v:
            print(f"Converting {len(args)} arguments")
        return tuple(_convert_item(arg, v) for arg in args)

    # Single argument
    return _convert_item(args[0], v)


def _convert_item(item: Any, v: bool = False) -> Any:
    """Convert a single item, handling nested structures

    Args:
        item: Item to convert
        v: Verbose mode

    Returns:
        Converted item or original if not pymaya
    """
    # Handle None
    if item is None:
        warnings.warn("pyconvert: Received None input")
        return None

    # Handle empty containers - check type first to avoid pymaya __eq__ issues
    if isinstance(item, list) and len(item) == 0:
        warnings.warn("pyconvert: Received empty list")
        return []

    if isinstance(item, tuple) and len(item) == 0:
        warnings.warn("pyconvert: Received empty tuple")
        return ()

    if isinstance(item, set) and len(item) == 0:
        warnings.warn("pyconvert: Received empty set")
        return set()

    # Handle nested structures recursively
    if isinstance(item, list):
        return [_convert_item(x, v) for x in item]

    if isinstance(item, tuple):
        return tuple(_convert_item(x, v) for x in item)

    if isinstance(item, set):
        return {_convert_item(x, v) for x in item}

    # Check if it's a pymaya node
    if _is_pymaya_node(item):
        return _convert_pymaya_to_pymel(item, v)

    # Everything else passes through unchanged
    return item


def _is_pymaya_node(obj: Any) -> bool:
    """Check if object is an mgear.pymaya node

    Args:
        obj: Object to check

    Returns:
        True if pymaya node, False otherwise
    """
    if not HAS_MGEAR:
        return False

    # Method 1: Check module
    if hasattr(obj, '__module__'):
        module = str(obj.__module__)
        if 'mgear.pymaya' in module:
            return True

    # Method 2: Check class
    if hasattr(obj, '__class__'):
        class_str = str(obj.__class__)
        if 'mgear.pymaya' in class_str:
            return True

    # Method 3: Check type for components
    type_str = str(type(obj))
    pymaya_types = ['MeshVertex', 'MeshEdge', 'MeshFace', 'PyNode']
    for ptype in pymaya_types:
        if ptype in type_str and 'pymaya' in type_str:
            return True

    return False


def _convert_pymaya_to_pymel(obj: Any, v: bool = False) -> pmc.PyNode:
    """Convert pymaya node to pymel node

    Args:
        obj: PyMaya object to convert
        v: Verbose mode

    Returns:
        PyMel node

    Raises:
        RuntimeError: If conversion fails
    """
    try:
        # Get node name
        if hasattr(obj, 'name'):
            node_name = obj.name()
        else:
            node_name = str(obj)

        # Convert to PyMel
        pymel_node = pmc.PyNode(node_name)

        if v:
            obj_type = type(obj).__name__
            print(f"  Converted pymaya.{obj_type}: {node_name} → {pymel_node}")

        return pymel_node

    except Exception as e:
        raise RuntimeError(f"pyconvert: Failed to convert pymaya '{obj}': {e}")


def info(obj: Any) -> None:
    """Print info about object's pymaya/pymel status

    Args:
        obj: Object to analyze
    """
    print("-" * 40)
    print(f"Type: {type(obj)}")

    if _is_pymaya_node(obj):
        print("Status: mGear PyMaya node")
        if hasattr(obj, 'name'):
            print(f"Name: {obj.name()}")
    elif hasattr(obj, '__module__') and 'pymel' in str(obj.__module__):
        print("Status: PyMel node")
        if hasattr(obj, 'name'):
            print(f"Name: {obj.name()}")
    elif isinstance(obj, (list, tuple, set)):
        print(f"Container with {len(obj)} items")
        pymaya_count = sum(1 for x in obj if _is_pymaya_node(x))
        if pymaya_count:
            print(f"  PyMaya nodes: {pymaya_count}")
    else:
        print("Status: Not a pymaya/pymel node")

    print("-" * 40)


# Convenience function for testing
def test_conversion():
    """Test the conversion with sample data"""
    print("\nPyConvert Test Suite")
    print("=" * 50)

    # Test None
    print("\n1. Testing None:")
    result = pymaya_to_pymel(None)
    print(f"   Result: {result}")

    # Test empty list
    print("\n2. Testing empty list:")
    result = pymaya_to_pymel([])
    print(f"   Result: {result}")

    # Test string (should pass through)
    print("\n3. Testing string:")
    result = pymaya_to_pymel("pCube1")
    print(f"   Input: 'pCube1' → Output: {result}")
    print(f"   Type unchanged: {isinstance(result, str)}")

    # Test mixed list
    print("\n4. Testing mixed list:")
    test_list = ["string", 42, None]
    result = pymaya_to_pymel(test_list)
    print(f"   Input: {test_list}")
    print(f"   Output: {result}")

    print("\n" + "=" * 50)
    print("Note: Full test requires mgear.pymaya nodes in scene")


if __name__ == "__main__":
    test_conversion()