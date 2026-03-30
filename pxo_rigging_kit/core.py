"""
Globally rigging package. It will contain utility code for daily usage.
Main reason is to establish a global rigging standart for all pxo facilities.
And make cooperation easier for all facilites.
"""

# Import future modules
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

# Import built-in modules
from builtins import map
from builtins import str
from collections import defaultdict
import hashlib
import uuid
from xml.etree import cElementTree as ET

# Import third-party modules
from future import standard_library
from pixo_config.config import Configuration

# Import local modules
from pxo_rigging_kit import constants

standard_library.install_aliases()

##########################################################
# FUNCTIONS
##########################################################


def get_config(key=None):
    """
    Read config file and return value by key.

    Args:
        key(str): The key to get the value from the config file.
    Return:
        str or dict: Value from key.
    """
    config = Configuration()
    return config.query(constants.CONFIG_FILE_NAME, key)


def load_config():
    """
    Read config file and return everything as a dictionary

    Return:
        str or dict: Value from key.
    """
    config = Configuration()
    return config.query(constants.CONFIG_FILE_NAME)


def generate_uuid_from_string(the_string):
    """
    Return string representation
    of the UUID of a hex md5 hash of the given string.

    Args:
        the_string(str): The string you want as uuid.

    """

    # Instansiate new md5_hash
    md5_hash = hashlib.md5()

    # Pass the_string to the md5_hash as bytes
    md5_hash.update(the_string.encode("utf-8"))

    # Generate the hex md5 hash of all the read bytes
    the_md5_hex_str = md5_hash.hexdigest()

    # Return a String repersenation of the uuid of the md5 hash
    return str(uuid.UUID(the_md5_hex_str))


def xml_to_dict(xml_data):
    """
    Convert xml data to dictionary.

    Args:
        xml_data(ET.XML): The xml data.

    Return:
        Dictionary: The converted xml data.

    """
    data_dict = {xml_data.tag: {} if xml_data.attrib else None}
    children = list(xml_data)
    if children:
        default_data_dict = defaultdict(list)
        for dc in map(xml_to_dict, children):
            for k, v in list(dc.items()):
                default_data_dict[k].append(v)
        data_dict = {
            xml_data.tag: {
                k: v[0] if len(v) == 1 else v
                for k, v in list(default_data_dict.items())
            }
        }
    if xml_data.attrib:
        data_dict[xml_data.tag].update(
            ("@" + k, v) for k, v in list(xml_data.attrib.items())
        )
    if xml_data.text:
        text = xml_data.text.strip()
        if children or xml_data.attrib:
            if text:
                data_dict[xml_data.tag]["#text"] = text
        else:
            data_dict[xml_data.tag] = text
    return data_dict


def check_similar_list_objects(list_1, list_2):
    """
    Check if members of two arrays are the same.

    Args:
        list_1(list): Source list.
        list_2(list): Target list.

    Return:
        True or False

    """
    return any(check in list_1 for check in list_2)


def get_duplicates_in_list(input_list):
    """
    Get duplicates in given list.

    Return:
        None if no duplicates.
        List: Filled with the duplicates.

    """
    duplicates = [obj for obj in input_list if input_list.count(obj) > 1]
    duplicates = list(set(duplicates))
    return duplicates


def pairwise(iterable):
    """
    Generator function to zip a list into pairs.

    Args:
        iterable(list): list(A,B,C,D,E,F,G)

    Returns:
        List: list((AB), (BC), (CD), (DE), (EF), (FG))
    """
    # Import built-in modules
    from itertools import tee

    a, b = tee(iterable)
    next(b, None)
    return list(zip(a, b))


def get_index_as_int(elem):
    """
    Get index string as integer

    Args:
        elem(str):

    Returns:

    """
    return int(elem.split('_')[-2])


def list_split(list_a, chunk_size):
    """
    Splits a lits if defined chuncks.

    Args:
        list_a:
        chunk_size:

    Returns:

    """
    for i in range(0, len(list_a), chunk_size):
        yield list_a[i:i + chunk_size]

def func(*args, **kwargs):
    pass
