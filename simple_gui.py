#!/usr/bin/env python3
import gi
gi.require_version('Gtk','3.0')

from gi.repository import Gtk
from gi.repository import Gdk
import os.path
import os

import converter
import xml.etree.ElementTree as ET
#import sys
import io

#NO_FILE = "<!--no file-->"
NO_FILE = '<span style="italic">No selected file.</span>'
class GUIHandler(object):
    def __init__( self, widgets, buffers ):
        self.widgets = widgets
        self.buffers = buffers
        self.set_filename( None )
    
    def set_filename( self, new_name ):
        if new_name == None:
            self.filename = None
            self.widgets["filename_label"].set_markup(NO_FILE)
        else:
            self.filename = new_name
            self.widgets["filename_label"].set_text( os.path.basename(new_name) )
        
    def get_filename( self ):
        return self.filename
    
    def set_buffer_text( self, text ):
        self.buffers["output_buffer"].set_text(text)
        
    def on_main_window_destroy( self, window ):
        Gtk.main_quit()
        return True
    
    def on_select_file_clicked( self, button ):
        svg_dialog = Gtk.FileChooserDialog(
                "Open SVG file",
                None,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK),
                )
        filter_svg = Gtk.FileFilter()
        filter_svg.set_name("SVG file")
        filter_svg.add_mime_type("image/svg+xml")
        svg_dialog.add_filter(filter_svg)

        response = svg_dialog.run()
        if response == Gtk.ResponseType.OK:
            self.set_filename( svg_dialog.get_filename() )
        #elif response == Gtk.ResponseType.CANCEL:
        #    pass
        svg_dialog.destroy()
        return True
    
    def on_execute_clicked( self, button ):
        converter.counter = 1
        filename = self.get_filename()
        if filename == None:
            self.set_buffer_text( "<!--No file selected-->\n" )
            return

        try:
            tree = ET.parse( filename )
        except ET.ParseError as e:
            self.set_buffer_text(
                    "<!--could not parse file %s : error %d at line %d, column %d-->\n"\
                    %( (repr(filename),e.code)+e.position) )
            return
        root = tree.getroot()
        
        subtree_id = self.buffers["subtree_id_buffer"].get_text()
        if subtree_id == "":
            imagemap_element = root
        else:
            imagemap_element = converter.findElementById( root, subtree_id )
            
        if imagemap_element == None:
            self.set_buffer_text( 
                    "<!--could not find element %s in %s-->\n"\
                    %(repr(subtree_id),repr(filename)) )
            return
            
        transform_stack = converter.TransformStack()
        output_stream = io.StringIO()
        converter.writeMapFromSubTree( imagemap_element, transform_stack, output_stream )
        self.set_buffer_text( output_stream.getvalue() )

def runGUI():
    glade_path = os.path.join( os.path.dirname( __file__ ), "simple_gui.glade" )
    builder = Gtk.Builder.new_from_file( glade_path )
    
    widget_names = ["main_window","filename_label"]
    widgets = dict(map(   lambda wid: (wid,builder.get_object(wid)),   widget_names   ))
    buffer_names = ["output_buffer","subtree_id_buffer"]
    buffers = dict(map(   lambda wid: (wid,builder.get_object(wid)),   buffer_names   ))
    
    builder.connect_signals( GUIHandler(widgets,buffers) )
    widgets["main_window"].show_all()
    
    Gtk.main()

if __name__ == '__main__':
    runGUI()
