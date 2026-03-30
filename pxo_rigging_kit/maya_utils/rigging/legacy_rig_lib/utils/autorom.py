"""
www.pixomondo.com
Date: 02 / 05 / 2022

auto rom animation module
category : Rigging
subcategory : utils
author : Christof Puehringer / Junior Rigging TD

"""
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

from future import standard_library
standard_library.install_aliases()
from builtins import object
import pymel.core as pmc

''' this is the script i put in for testing
import legacy_rig_lib.utils.autorom as autorom
reload(autorom)
batz= autorom.RomAnimation()
batz.apply_rom(clamp_at=None)
'''

class RomAnimation(object):
    """ class to work with automated rom animation
        classAttributes:
            KEY_SCALING
            KEY_SEPERATION
            TRANSLATE_VALUE
            ROTATE_VALUE
            SCALE_VALUE
            DEFAULT_KEY
            DEFAULT_KEY_SCALE
            KEYABLE_ATTRS

    """

    KEY_SCALING = 1
    KEY_SEPERATION = 1

    TRANSLATE_VALUE = 10 * KEY_SCALING
    ROTATE_VALUE = 15 * KEY_SCALING
    SCALE_VALUE = 1 * KEY_SCALING

    DEFAULT_KEY = 0
    DEFAULT_KEY_SCALE = 1

    KEYABLE_ATTRS = {'tx': (DEFAULT_KEY,  TRANSLATE_VALUE),
                     'ty': (DEFAULT_KEY, TRANSLATE_VALUE),
                     'tz': (DEFAULT_KEY, TRANSLATE_VALUE),
                     'rx': (DEFAULT_KEY, ROTATE_VALUE),
                     'ry': (DEFAULT_KEY, ROTATE_VALUE),
                     'rz': (DEFAULT_KEY, ROTATE_VALUE),
                     'sx': (DEFAULT_KEY_SCALE, SCALE_VALUE),
                     'sy': (DEFAULT_KEY_SCALE, SCALE_VALUE),
                     'sz': (DEFAULT_KEY_SCALE, SCALE_VALUE)}

    CONTROL_SUFFIX = 'ctrl'

    def __init__(self, clamp_at_value=120):
        """ initializes the class
        Args:
            clamp_at_value(int): specifies the range in which the test should be run
                                 stops the keying-process at this frame
        """

        min_time = pmc.playbackOptions(minTime=True, query=True)
        max_time = pmc.playbackOptions( maxTime=True, query=True)
        self.anim_range = [min_time, max_time]

        min_anim = pmc.playbackOptions(animationStartTime=True, query=True)
        max_anim = pmc.playbackOptions(animationEndTime=True, query=True)
        self.slider_range = [min_anim, max_anim]

    @staticmethod
    def list_all_controls():
        """ checks whole scene for objects with the suffix specified in the class
            and returns them

        Returns:
            all_controls(list): list of PyNodes
        """

        all_controls = pmc.ls('*_{}'.format(RomAnimation.CONTROL_SUFFIX))
        return all_controls

    def apply_rom(self, clamp_at=120, stretch_rom=True, key_seperation=None):
        """

        :param clamp_at:
        :return:
        """
        keyed_controls = list()
        end_pos = 1
        if not key_seperation:
            print('ayyy')
            key_seperation = self.KEY_SEPERATION

        for ctrl in RomAnimation.list_all_controls():
            for key, value in list(self.KEYABLE_ATTRS.items()):
                if clamp_at:
                    if end_pos >= clamp_at:
                        break
                print(key_seperation)
                try:
                    pmc.setKeyframe(ctrl, t=end_pos, at=key, v=value[0])
                    pmc.setKeyframe(ctrl, t=end_pos+key_seperation, at=key, v=value[1])
                    pmc.setKeyframe(ctrl, t=end_pos+(key_seperation * 2), at=key, v=value[0])

                except:
                    print('{}: was skipped due not being able to add keyframe data on it'.format(key))

                if stretch_rom:
                    end_pos= end_pos + (key_seperation * 2)

            keyed_controls.append(ctrl)

        pmc.playbackOptions(animationEndTime=end_pos, maxTime=end_pos)
        return keyed_controls

    def remove_rom(self):
        """ resets the timeslider and range to the status it was in before having the rom animation
            then it deletes all the keyframes that are on the sampled positions

        :return:
        """
        pmc.playbackOptions(minTime=self.slider_range[0], maxTime=self.slider_range[1],
                           animationStartTime=self.anim_range[0], animationEndTime=self.anim_range[1])
