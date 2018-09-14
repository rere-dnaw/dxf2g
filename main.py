############################################################################
#
#   Created by Rafal Wilk based on DXF2GCODE
#
#
#   Copyright (C) 2008-2015
#    Christian Kohlöffel
#    Jean-Paul Schouwstra
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
import sys
import logging
import globals.globals as g
import glob
import wx
import time

from globals.config import MyConfig
from dxfimport.importer import ReadDXF
from copy import copy
from core.shape import Shape
from core.point import Point
from core.holegeo import HoleGeo
from core.layercontent import LayerContent, Layers, Shapes
from core.entitycontent import EntityContent
from core.stmove import StMove
from postpro.postprocessor import MyPostProcessor


class Main():
    '''
    This is the main class of the script
    '''
    def __init__(self, dxf_filename):
        '''
        dxf_object initialization
        '''
        self.dxf_filename = dxf_filename
        self.values_dxf = None
        self.shapes = Shapes([])
        self.entity_root = None
        self.layer_contents = Layers([])
        self.newNumber = 1

        self.cont_dx = 0.0
        self.cont_dy = 0.0
        self.cont_rotate = 0.0
        self.cont_scale = 1.0

        self.file_name = ""
        self.my_post_processor = MyPostProcessor(script_dir)

    def load(self):
        """
        Loads the file given by self.file_name. This function is called
        when a dxf file is selected.
        """
        g.config = MyConfig(script_dir)

        self.values_dxf = ReadDXF(self.dxf_filename)

        # Output to the logfile
        logger.info(('Loaded layers: %s') %
                    len(self.values_dxf.layers))
        logger.info(('Loaded blocks: %s') %
                    len(self.values_dxf.blocks.Entities))

        # Output to the logfile
        for i in range(len(self.values_dxf.blocks.Entities)):
            layers = self.values_dxf.blocks.Entities[i].get_used_layers()
            logger.info(("Block %i includes %i Geometries, reduced to %i "
                         "Contours, used layers: %s") %
                        (i, len(self.values_dxf.blocks.Entities[i].geo),
                            len(self.values_dxf.blocks.Entities[i].cont),
                        layers))

        layers = self.values_dxf.entities.get_used_layers()
        insert_nr = self.values_dxf.entities.get_insert_nr()

        # Output to the logfile
        logger.info(("Loaded %i entity geometries; reduced to %i contours; "
                     "used layers: %s; number of inserts %i") %
                    (len(self.values_dxf.entities.geo),
                     len(self.values_dxf.entities.cont), layers, insert_nr))

        # Output to the logfile
        if g.config.metric == 0:
            logger.info("Drawing units: inches")
        else:
            logger.info("Drawing units: millimeters")

        self.makeShapes()
        self.call_stmove(self.shapes)
        self.exportShapes()

    def call_stmove(self, shapes):
        """
        The parameters are generally offset the base geometry. 
        """
        for shape in shapes:
            shape.stmove = self.create_stmove(shape)

    def create_stmove(self, shape):
        """
        This function creates the Additional Start and End Moves in the plot
        window when the shape is selected
        @param shape: The shape for which the Move shall be created.
        """
        stmove = StMoveGUI(shape)
        return stmove

    def makeShapes(self):
        self.entity_root = EntityContent(nr=0,
                                         name='Entities',
                                         parent=None,
                                         p0=Point(self.cont_dx, self.cont_dy),
                                         pb=Point(),
                                         sca=[self.cont_scale, self.cont_scale,
                                              self.cont_scale],
                                         rot=self.cont_rotate)
        self.layer_contents = Layers([])
        self.shapes = Shapes([])

        self.makeEntityShapes(self.entity_root)

        for layerContent in self.layer_contents:
            layerContent.overrideDefaults()

        self.layer_contents.sort(key=lambda x: x.nr)
        self.newNumber = len(self.shapes)

    def change_direction(self):
        """
        this method is changing routing direction
        this needs to be linked to RI parameter which will came from 
        layer name. The method needs to be called in def makeShapes method
        """
        for shape in self.shapes:
            shape.reverse()

    def makeEntityShapes(self, parent, layerNr=-1):
        """
        Instance is called prior to plotting the shapes. It creates
        all shape classes which are plotted into the canvas.

        @param parent: The parent of a shape is always an Entity. It may be the root
        or, if it is a Block, this is the Block.
        """
        if parent.name == "Entities":
            entities = self.values_dxf.entities
        else:
            ent_nr = self.values_dxf.Get_Block_Nr(parent.name)
            entities = self.values_dxf.blocks.Entities[ent_nr]

        # Assigning the geometries in the variables geos & contours in cont
        ent_geos = entities.geo

        # Loop for the number of contours
        for cont in entities.cont:
            # Query if it is in the contour of an insert or of a block
            if ent_geos[cont.order[0][0]].Typ == "Insert":
                ent_geo = ent_geos[cont.order[0][0]]

                # Assign the base point for the block
                new_ent_nr = self.values_dxf.Get_Block_Nr(ent_geo.BlockName)
                new_entities = self.values_dxf.blocks.Entities[new_ent_nr]
                pb = new_entities.basep

                # Scaling, etc. assign the block
                p0 = ent_geos[cont.order[0][0]].Point
                sca = ent_geos[cont.order[0][0]].Scale
                rot = ent_geos[cont.order[0][0]].rot

                # Creating the new Entitie Contents for the insert
                newEntityContent = EntityContent(nr=0,
                                                 name=ent_geo.BlockName,
                                                 parent=parent,
                                                 p0=p0,
                                                 pb=pb,
                                                 sca=sca,
                                                 rot=rot)

                parent.append(newEntityContent)

                self.makeEntityShapes(newEntityContent, ent_geo.Layer_Nr)

            else:
                # Loop for the number of geometries
                tmp_shape = Shape(len(self.shapes),
                                  (True if cont.closed else False),
                                  parent)

                for ent_geo_nr in range(len(cont.order)):
                    ent_geo = ent_geos[cont.order[ent_geo_nr][0]]
                    if cont.order[ent_geo_nr][1]:
                        ent_geo.geo.reverse()
                        for geo in ent_geo.geo:
                            geo = copy(geo)
                            geo.reverse()
                            self.append_geo_to_shape(tmp_shape, geo)
                        ent_geo.geo.reverse()
                    else:
                        for geo in ent_geo.geo:
                            self.append_geo_to_shape(tmp_shape, copy(geo))

                if len(tmp_shape.geos) > 0:
                    # All shapes have to be CW direction.
                    tmp_shape.AnalyseAndOptimize()

                    self.shapes.append(tmp_shape)
                    if g.config.vars.Import_Parameters['insert_at_block_layer'] and layerNr != -1:
                        self.addtoLayerContents(tmp_shape, layerNr)
                    else:
                        self.addtoLayerContents(tmp_shape, ent_geo.Layer_Nr)
                    parent.append(tmp_shape)

    def append_geo_to_shape(self, shape, geo):
        if -1e-5 <= geo.length < 1e-5:  # TODO adjust import for this
            return

        shape.append(geo)

        if isinstance(geo, HoleGeo):
            shape.type = 'Hole'
            shape.closed = True  # TODO adjust import for holes?
            if g.config.machine_type == 'drag_knife':
                shape.disabled = True
                shape.allowedToChange = False
    
    def addtoLayerContents(self, shape, lay_nr):
        # Check if the layer already exists and add shape if it is.
        for LayCon in self.layer_contents:
            if LayCon.nr == lay_nr:
                LayCon.shapes.append(shape)
                shape.parentLayer = LayCon
                return

        # If the Layer does not exist create a new one.
        LayerName = self.values_dxf.layers[lay_nr].name
        self.layer_contents.append(LayerContent(lay_nr, LayerName, [shape]))
        shape.parentLayer = self.layer_contents[-1]

    def exportShapes(self, status=False, saveas=None):
        """
        This function is called by the menu "Export/Export Shapes". It may open
        a Save Dialog if used without LinuxCNC integration. Otherwise it's
        possible to select multiple postprocessor files, which are located
        in the folder.
        """

        logger.debug('Export the enabled shapes') # save debug line into the logger file

        logger.debug("Sorted layers:") # save debug line into the logger file
        for i, layer in enumerate(self.layer_contents.non_break_layer_iter()):
            logger.debug("LayerContents[%i] = %s" % (i, layer)) #save layers from class layer_contents into the logger file

        ##fix for bug B01486 
        for LayerContent in self.layer_contents.non_break_layer_iter():
            for number in range(0, len(LayerContent.shapes)):
                LayerContent.exp_order_complete.append(number)
        ##fix fir bug B01486

        if not g.config.vars.General['write_to_stdout']:
            save_filename = os.path.splitext(self.dxf_filename)
            save_filename = save_filename[0] + ".nc"
            print(save_filename)
            self.my_post_processor.getPostProVars(0)

        """
        Export will be performed according to LayerContents and their order
        is given in this variable too.
        """

        self.my_post_processor.exportShapes(self.file_name,
                                            save_filename,
                                            self.layer_contents)

        if g.config.vars.General['write_to_stdout']:
            self.close()

    @staticmethod
    def log_file_path():
        '''
        Return a path for a main.py file location
        '''
        if getattr(sys, 'frozen', False):
            script_dir = os.path.dirname(sys.executable)  # from exe
        elif __file__:
            script_dir = os.path.dirname(__file__)  # running live
        return script_dir

    @staticmethod
    def log_config(script_dir):
        '''
        Setting up logger configuration
        '''
        LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(filename=script_dir + "\\LogFile.log",
                            level=logging.DEBUG, format=LOG_FORMAT,
                            filemode='w')  # filemode=w clean the log file
        logger = logging.getLogger()
        return logger


class StMoveGUI(StMove):

    def __init__(self, shape):
        StMove.__init__(self, shape)
        self.allwaysshow = False


def create_dxf_list(dxf_directory):
    """
    This function load dxf files into the
    dxf_files_list form input directory.
    """
    os.chdir(dxf_directory)
    dxf_files_list = []

    for file in glob.glob("*.dxf"):
        dxf_files_list.append(dxf_directory + "\\" + file)

    return dxf_files_list


class MyFrame(wx.Frame):
    
    def __init__(self):
        wx.Frame.__init__ ( self, None, id = wx.ID_ANY, title = wx.EmptyString, pos = wx.DefaultPosition, size = wx.Size( 500,182 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
        
        self.SetSizeHints( wx.DefaultSize, wx.DefaultSize )
        
        bSizer1 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_panel1 = wx.Panel( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL )
        bSizer2 = wx.BoxSizer( wx.VERTICAL )
        
        sbSizer1 = wx.StaticBoxSizer( wx.StaticBox( self.m_panel1, wx.ID_ANY, u"Select directory:" ), wx.VERTICAL )
        
        self.m_dir_pick = wx.DirPickerCtrl( sbSizer1.GetStaticBox(), wx.ID_ANY, wx.EmptyString, u"Select a folder", wx.DefaultPosition, wx.DefaultSize, wx.DIRP_DEFAULT_STYLE )
        sbSizer1.Add( self.m_dir_pick, 0, wx.ALL|wx.EXPAND, 5 )
        
        
        bSizer2.Add( sbSizer1, 1, wx.ALL|wx.EXPAND, 5 )
        
        bSizer8 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_gauge2 = wx.Gauge( self.m_panel1, wx.ID_ANY, 100, wx.DefaultPosition, wx.DefaultSize, wx.GA_HORIZONTAL )
        self.m_gauge2.SetValue(0)
        bSizer8.Add( self.m_gauge2, 0, wx.ALIGN_CENTER|wx.ALL, 5 )
        
        
        bSizer2.Add( bSizer8, 1, wx.EXPAND, 5 )
        
        bSizer3 = wx.BoxSizer( wx.HORIZONTAL )
        
        bSizer5 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_OK_button = wx.ToggleButton( self.m_panel1, wx.ID_ANY, u"OK", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer5.Add( self.m_OK_button, 0, wx.ALIGN_CENTER|wx.ALL, 5 )
        
        
        bSizer3.Add( bSizer5, 1, wx.ALIGN_CENTER, 5 )
        
        bSizer6 = wx.BoxSizer( wx.VERTICAL )
        
        self.m_cancel_button = wx.ToggleButton( self.m_panel1, wx.ID_ANY, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
        bSizer6.Add( self.m_cancel_button, 0, wx.ALIGN_CENTER|wx.ALL, 5 )
        
        
        bSizer3.Add( bSizer6, 1, wx.ALIGN_CENTER, 5 )
        
        
        bSizer2.Add( bSizer3, 1, wx.ALIGN_CENTER|wx.EXPAND, 5 )
        
        
        self.m_panel1.SetSizer( bSizer2 )
        self.m_panel1.Layout()
        bSizer2.Fit( self.m_panel1 )
        bSizer1.Add( self.m_panel1, 1, wx.EXPAND |wx.ALL, 5 )
        
        
        self.SetSizer( bSizer1 )
        self.Layout()
        
        self.Centre( wx.BOTH )
        
        # Connect Events
        self.m_dir_pick.Bind( wx.EVT_DIRPICKER_CHANGED, self.m_dir_pickOnDirChanged )
        self.m_OK_button.Bind( wx.EVT_TOGGLEBUTTON, self.m_OK_buttonOnToggleButton )
        self.m_cancel_button.Bind( wx.EVT_TOGGLEBUTTON, self.m_cancel_buttonOnToggleButton )
    
    def __del__( self ):
        pass
    
    
    # Virtual event handlers, overide them in your derived class
    def m_dir_pickOnDirChanged( self, event ):
        event.Skip()
    
    def m_OK_buttonOnToggleButton( self, event ):
        dxf_directory = self.m_dir_pick.GetPath()
        dxf_files_list = create_dxf_list(dxf_directory)
        dxf_list_len = len(dxf_files_list)
        value = 0
        for el in dxf_files_list:
            dxf_object = Main(el)
            Main.load(dxf_object)
            value = value + 100/dxf_list_len
            self.m_gauge2.SetValue(value)
        print(value)
        self.m_gauge2.SetValue(99.5)
        time.sleep(2)
        self.m_gauge2.SetValue(0)
    
    def m_cancel_buttonOnToggleButton( self, event ):
        self.Close()


script_dir = Main.log_file_path()  # path for script location
logger = Main.log_config(script_dir)  # setting up logger configuration

if __name__ == "__main__":
    app = wx.App(False)
    frame = MyFrame()
    frame.Show()
    app.MainLoop()
