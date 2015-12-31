#!/usr/bin/env python3

#####################
## data outputters ##
#####################

import re
command_re = re.compile("[a-zA-Z]")
useless_re = re.compile("[,;:|\s]*")
counter = 1
link_template = "Link %d"
def writeMapFromPath( string, transform, outputstream ):
    global counter
    
    coordinates = []
    words = re.split( "[a-zA-Z,;:|\s]", string )
    word_stack = [ w for w in words if not useless_re.fullmatch(w) ]
    x = 0.0
    y = 0.0
    z_x, z_y = x, y
    command = "m"
    
    if len(word_stack) == 0:
        return
    
    outputstream.write("poly")
    
    while len(word_stack)>0:
        word = word_stack.pop(0)
        
        #new command to use for next points
        if word == "z" or word == "Z":
            x = z_x
            y = z_y
            outputstream.write( " %d %d" % (round(x),round(y)) )
            command = "m"
            continue
        elif command_re.fullmatch( word ):
            command = word
            continue
        #else, the following
        
        #add point accordingly to last command
        if command == "m":
            x += float(word)
            y += float(word_stack.pop(0))
            z_x, z_y = x, y
            command = "l"
        elif command  == "M":
            x = float(word)
            y = float(word_stack.pop(0))
            z_x, z_y = x, y
            command = "L"
        elif command == "l":
            x += float(word)
            y += float(word_stack.pop(0))
        elif command == "L":
            x = float(word)
            y = float(word_stack.pop(0))
        elif command == "h":
            x += float(word)
        elif command == "H":
            x = float(word)
        elif command == "v":
            y += float(word)
        elif command == "V":
            y = float(word)
        else:
            outputstream.write( "<!--unimplemented behavior on %s, or mistyped command.-->" % repr(command) )
            
        outputstream.write( " %d %d" % (round(x),round(y)) )
        
    outputstream.write(" [[%s]]\n" % (link_template%counter) )
    counter += 1


def writeMapFromRect( x, y, w, h, transform, outputstream ):
    global counter
    link_label = link_template % counter
    
    if transform.is_rectilinear:
        left = round(x)
        top = round(y)
        right = x + round(w)
        bottom = y + round(h)
        outputstream.write( "rect %d %d %d %d [[%s]]\n" % (left,top,right,bottom,link_label) )
    else:
        a = x,y
        b = x,y+h
        c = x+w,y+h
        d = x+w,y
        outputstream.write( "poly %d %d %d %d %d %d %d %d [[%s]]\n" % (a+b+c+d+(link_label,)) )

    counter += 1

##############
## Matrices ##
##############

import re
import affine

transform_re = re.compile("([a-zA-Z0-9]+)\(([^()]*)\)")
def transformFromStr( string ):
    match = transform.match( string )
    transform_type = match.group(1)
    transform_args = list(float, match.group(2).split(","))
    n = len(transform_args)
    
    if transform_type == "matrix":
        if n == 6:
            return affine.Affine( *transform_args )
    elif transform_type == "translate":
        if n == 1:
            return affine.Affine.translation( transform_args[0], 0 )
        elif n == 2:
            return affine.Affine.translation( *transform_args )
    elif transform_type == "scale":
        if n == 1:
            factor = transform_args[0]
            return affine.Affine.scale( factor, factor )
        elif n == 2:
            return affine.Affine.scale( *transform_args )
    elif transform_type == "rotate":
        if n == 1:
            return affine.Affine.rotation( transform_args[0] )
        elif n == 3:
            pivot = tuple(transform_args[2:3])
            return affine.Affine.rotation( transform_args[0], pivot = pivot )
    elif transform_type == "skewX":
        if n == 1:
            return affine.Affine.shear( x_angle = transform_args[0] )
    elif transform_type == "skewY":
        if n == 1:
            return affine.Affine.shear( y_angle = transform_args[0] )
    else:
        raise Exception( "Unknown transform %s" % transformation_type )
    raise Exception( "Bad number of parameters for transfrom %s : %d" % (transformation_type,n) )
    


class TransformStack(object):
    def __init__( self ):
        self.stack_ = [affine.Affine.identity()]
        self.precomputed_stack_ = [affine.Affine.identity()]
    
    def push( self, transform ):
        self.stack_.append( transform )
        composition = transform * self.precomputed_stack_[-1]
        self.precomputed_stack_.append( composition )
        
    def pop( self, transform ):
        self.stack_.pop()
        self.precomputed_stack_.pop()
    
    def compute( self ):
        return self.precomputed_stack_[-1]

########################
## Tree & xml parsing ##
########################

import xml.etree.ElementTree as ET

def writeMapFromSubTree( element, transform_stack, outputstream ):
    n = 0
    #transform_stack.push()
    if element.tag[-4:] == 'path':
        writeMapFromPath( element.attrib['d'], transform_stack.compute(), outputstream )
    elif element.tag[-4:] == 'rect':
        #x, y = element.attrib['x'], element.attrib['y']
        #w, h = element.attrib['width'], element.attrib['height']
        x, y, w, h = map( lambda name: float(element.attrib[name]), ['x','y','width','height'] )
        writeMapFromRect( x, y, w, h, transform_stack.compute(), outputstream )
        
    for subelement in element:
        writeMapFromSubTree( subelement, transform_stack, outputstream )
    #transform_stack.pop()
    
    
def findElementById( element, idname ):
    if 'id' in element.attrib and element.attrib['id'] == idname:
        return element
    for child in element:
        result = findElementById( child, idname )
        if result != None:
            return result
    return None


import xml.etree.ElementTree as ET
if __name__ == '__main__':
    import sys
    import argparse
    parser = argparse.ArgumentParser(
            description="Convert shapes to clickable mediawiki <imagemap> links."
            )
    parser.add_argument( 'svgfile', nargs='+', action='store' )
    parser.add_argument( '-g', '--groupname', action='store', default='imagemap' )
    parser.add_argument( '-a', '--all', dest='groupname', action='store_const', const=None )
    args = parser.parse_args()
    
    imagemap_groupname = args.groupname
    
    for svg_filename in args.svgfile:
        tree = ET.parse( svg_filename )
        root = tree.getroot()
        imagemap_element = findElementById( root, imagemap_groupname ) if imagemap_groupname else root
        if imagemap_element == None:
            print( "<!--could not find element %s in %s-->" %(repr(imagemap_groupname),repr(svg_filename)) )
        else:
            writeMapFromSubTree( imagemap_element, TransformStack(), sys.stdout )