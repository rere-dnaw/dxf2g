# -*- coding: utf-8 -*-

############################################################################
#
#   Copyright (C) 2008-2016
#    Christian Kohlöffel
#    Vinzenz Schulz
#    Jean-Paul Schouwstra
#    Xavier Izard
#
#   This file is part of DXF2GCODE.
#
#   DXF2GCODE is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   DXF2GCODE is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with DXF2GCODE.  If not, see <http://www.gnu.org/licenses/>.
#
############################################################################

import os

from globals.configobj.configobj import ConfigObj, flatten_errors
from globals.configobj.validate import Validator

import globals.globals as g
from globals.d2gexceptions import *

from globals.six import text_type
import globals.constants as c

import logging
logger = logging.getLogger("PostPro.PostProcessorConfig")

POSTPRO_VERSION = "6"
"""
version tag - increment this each time you edit CONFIG_SPEC

compared to version number in config file so
old versions are recognized and skipped
"""

POSTPRO_SPEC = str('''
#  Section and variable names must be valid Python identifiers
#      do not use whitespace in names

# do not edit the following section name:
    [Version]
    # do not edit the following value:
    config_version = string(default="'''  +
    str(POSTPRO_VERSION) + '")\n' +
    '''
    [General]
    # This extension is used in the save file export dialog.
    output_format = string(default=".ngc")
    # This title is shown in the export dialog and is used by the user to differentiate between the possible different postprocessor configurations.
    output_text = string(default="G-CODE for LinuxCNC")
    # This type defines the output format used in the export dialog.
    output_type = option('g-code', 'dxf', 'text', default = 'g-code')

    # Used to switch between absolute (G90) and relative/incremental coordinates (G91).
    abs_export = boolean(default=True)
    # If cutter compensation is used, e.g. G41 or G42, this option cancels the compensation when there is a momevement on the 3rd-axis, and enables the compensation again afterwards.
    cancel_cc_for_depth = boolean(default=False)
    # If cutter compensation is used (G41-G42) this will apply the cutter compensation outside the piece (i.e. it is applied before it is at milling depth).
    cc_outside_the_piece = boolean(default=True)
    # Used for dxfs which only support arcs that are in counterclockwise direction. Turning this on for normal G-Code will result in unintended output.
    export_ccw_arcs_only = boolean(default=False)
    # If an arc's radius exceeds this value, then it will be exported as a line.
    max_arc_radius = float(min = 0, default=10000)

    code_begin_units_mm = string(default="G21 (Units in millimeters)")
    code_begin_units_in = string(default="G20 (Units in inches)")
    code_begin_prog_abs = string(default="G90 (Absolute programming)")
    code_begin_prog_inc = string(default="G91 (Incremental programming)")
    # This is code which will be written at the beginning of the exported file.
    code_begin = string(default="G64 (Default cutting) G17 (XY plane) G40 (Cancel radius comp.) G49 (Cancel length comp.)")
    # This is code which will be written at the end of the exported file.
    code_end = string(default="M2 (Program end)")

    [Number_Format]
    # Gives the indentation for the values.
    pre_decimals = integer(min = 0, default=4)
    # Gives the accuracy of the output after which it will be rounded.
    post_decimals = integer(min = 0, default=3)
    # Give the separator which is used in the exported values (e.g. '.' or ',').
    decimal_separator = string(default=".")
    # If true all values will be padded with zeros up to pre_decimals (e.g. 0001.000).
    pre_decimal_zero_padding = boolean(default=False)
    # If false e.g. 1.000 will be given as 1 only.
    post_decimal_zero_padding = boolean(default=True)
    # If True 1.000 will be written as +1.000
    signed_values = boolean(default=False)

    [Line_Numbers]
    # Enables line numbers into the exported G-Code file.
    use_line_nrs = boolean(default=False)
    line_nrs_begin = integer(default=10)
    line_nrs_step = integer(default=10)

    [Program]
    # This will be done after each layer, if different tools are used.
    tool_change = string(default=T%tool_nr M6%nlS%speed%nl)
    # This will be done after each change between cutting in plane or cutting in depth.
    feed_change = string(default=F%feed%nl)
    # This will be done between each shape to cut.
    rap_pos_plane = string(default=G0 X%XE Y%YE%nl)
    # This will be done between each shape to cut.
    rap_pos_depth = string(default=G0 Z%ZE %nl)
    # This will be used for shape cutting.
    lin_mov_plane = string(default= G1 X%XE Y%YE%nl)
    # This will be used for shape cutting.
    lin_mov_depth = string(default= G1 Z%ZE%nl)
    # This will be used for shape cutting.
    arc_int_cw = string(default=G2 X%XE Y%YE I%I J%J%nl)
    # This will be used for shape cutting.
    arc_int_ccw = string(default=G3 X%XE Y%YE I%I J%J%nl)
    # Generally set to G40%nl
    cutter_comp_off = string(default=G40%nl)
    # Generally set to G41%nl
    cutter_comp_left = string(default=G41%nl)
    # Generally set to G42%nl
    cutter_comp_right = string(default=G42%nl)
    # This will be done before starting to cut a shape or a contour.
    pre_shape_cut = string(default=M3 M8%nl)
    # This will be done after cutting a shape or a contour.
    post_shape_cut = string(default=M9 M5%nl)
    # Defines comments' format. Comments are written at some places during the export in order to make the g-code better readable.
    comment = string(default=%nl(%comment)%nl)

''').splitlines()
""" format, type and default value specification of the global config file"""


class MyPostProConfig(object):
    """
    This class hosts all functions related to the PostProConfig File.
    """
    def __init__(self, file_name='postpro_config' + c.CONFIG_EXTENSION):
        """
        initialize the varspace of an existing plugin instance
        init_varspace() is a superclass method of plugin
        @param file_name: The file_name for the creation of a new config
        file and the file_name of the file to read config from.
        """
        self.folder = os.path.join('C:\\PythonScripts\\1.Programming\\dxf2g\\config')
        self.file_name = os.path.join(self.folder, file_name)

        self.version_mismatch = '' # no problem for now
        self.default_config = False  # whether a new name was generated
        self.var_dict = dict()
        self.spec = ConfigObj(POSTPRO_SPEC, interpolation=False, list_values=False, _inspec=True)

    def load_config(self):
        """
        This method tries to load the defined postprocessor file given in
        self.file_name. If this fails it will create a new one
        """

        try:
            # file exists, read & validate it
            self.var_dict = ConfigObj(self.file_name, configspec=POSTPRO_SPEC)
            _vdt = Validator()
            result = self.var_dict.validate(_vdt, preserve_errors=True)
            validate_errors = flatten_errors(self.var_dict, result)
        except self.var_dict == None: #rw
            logger.error("reading values from postprocessorconfig file error") #rw

        self.var_dict.main.interpolation = False  # avoid ConfigObj getting too clever
        self.update_config()

    def update_config(self):
        """
        Call this function each time the self.var_dict is updated (eg when the postprocessor configuration window changes some settings)
        """
        # convenience - flatten nested config dict to access it via self.config.sectionname.varname
        self.vars = DictDotLookup(self.var_dict)
        # add here any update needed for the internal variables of this class

    def make_settings_folder(self):
        """
        This method creates the postprocessor settings folder if necessary
        """
        try:
            os.mkdir(self.folder)
        except OSError:
            pass


class DictDotLookup(object):
    """
    Creates objects that behave much like a dictionaries, but allow nested
    key access using object '.' (dot) lookups.
    """
    def __init__(self, d):
        for k in d:
            if isinstance(d[k], dict):
                self.__dict__[k] = DictDotLookup(d[k])
            elif isinstance(d[k], (list, tuple)):
                l = []
                for v in d[k]:
                    if isinstance(v, dict):
                        l.append(DictDotLookup(v))
                    else:
                        l.append(v)
                self.__dict__[k] = l
            else:
                self.__dict__[k] = d[k]

    def __getitem__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]

    def __iter__(self):
        return iter(self.__dict__.keys())
