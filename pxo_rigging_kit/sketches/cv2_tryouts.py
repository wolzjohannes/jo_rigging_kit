import os

os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "1"  # needs to be set before cv2 import

import cv2
import numpy as np
import logging
from pprint import pprint

if sys.version_info.major == 3:

    from importlib import reload

elif sys.version_info.major == 2:

    pass

##########################################################
# GLOBALS
##########################################################
_LOGGER = logging.getLogger(__name__ + ".py")

_LOGGER.setLevel(logging.INFO)

_TEST_CASE_FILE_PATH = r'X:\redgun3_rg3-18453\_library\assets\creature\crt_vhagar\txt\_publish\clr_oneUdim\v001\fullres\rg2_crt_vhagar_txt_clr_oneUdim_v001_tof.tx'

# the standard of only returning one
_SIMPLE_NUMBER_OF_CLUSTERS_ = 4

# the fancy version of returning multiples, and how many of those
NUMBER_OF_CLUSTERS_ = 4


##########################################################
# Functions
##########################################################

def encode_to_srgb_np(input_array):
    """
    Uses numpy vectorization to convert EXRs value to SRGB.

    Args:
        input_array(numpy.array): The array that is shifted.

    Returns:
        numpy.array(srgb): the newly created srgb array.
    """

    input_array = np.asarray(input_array)

    srgb = np.where(input_array <= 0.0031308,
                    input_array * 12.92,
                    1.055 * np.power(input_array, 1.0 / 2.4) - 0.055
                    )

    return srgb * 255.0


def _create_bar(height, width, color):

    # Ensure color is in the correct format
    color = tuple((int(col) for col in color))

    # Create the bar using np.full for direct initialization
    bar = np.full((height, width, 3), color, dtype=np.uint8)

    # Extract RGB values
    red, green, blue = color[2], color[1], color[0]

    return bar, (red, green, blue)


def read_image(file_path,is_exr=True):

    img_raw_ = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)

    if img_raw_ is None:
        raise ValueError(f"wrong path was given with:\n{file_path}")

    _LOGGER.debug("image has been read")

    # getting rid of disgusteng alphas
    img_ = cv2.cvtColor(img_raw_, cv2.COLOR_RGBA2RGB)

    if is_exr:
        #img_ = encode_to_srgb_np(img_)

        _LOGGER.info("image has been normalized to rgb")

    return img_raw_, img_


def find_most_dominant_means(data_):

    # convert data to float because kmeans only takes float32
    data_ = np.float32(data_)

    # setting the options
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    flags = cv2.KMEANS_RANDOM_CENTERS

    return cv2.kmeans(data_, NUMBER_OF_CLUSTERS_, None, criteria, 10, flags)


def main():
    img_raw, img = read_image(_TEST_CASE_FILE_PATH)

    height, width, _ = np.shape(img)

    data = np.reshape(img, (height * width, 3))

    compactness, labels, centers = find_most_dominant_means(data)

    bars = []

    rgb_values = []

    for index, row in enumerate(centers):

        bar, rgb = _create_bar(200, 200, row)

        bars.append(bar)

        rgb_values.append(rgb)

    # Compute the min, max and median of product

    pmin, pmax , pmed = np.amin((3,2,1)), np.amax((3,1,1)), np.median((3,21,1))

    img_bar = np.hstack(bars)

    cv2.namedWindow('dom_clr',
                    cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_EXPANDED)

    cv2.namedWindow('exr_neg',
                    cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO | cv2.WINDOW_GUI_EXPANDED)

    cv2.imshow('exr_neg', img_raw)
    cv2.imshow('dom_clr', img_bar)

    cv2.imwrite(r'C:\Users\christof.puehringer\Desktop\lel.jpeg', img_bar)

    cv2.waitKey(0)
    cv2.destroyAllWindows()

    print(rgb_values)


if __name__ == "__main__":
    main()