import struct
import xml.etree.ElementTree as ET
import ast
import numpy as np
import os
from reduction import datareducers,data_operators
from collections import Iterable


class VlsvWriter(object):
   ''' Class for reading VLSV files
   '''
   def __init__(self, vlsvReader, file_name ):
      ''' Initializes the vlsv file (opens the file, reads the file footer and reads in some parameters)

          :param vlsvReader:    Some open vlsv file for creating an XML footer as well as the grid
          :param file_name:     Name of the vlsv file where to input data
      '''
      self.__file_name = os.path.abspath(file_name)
      self.__fptr = open(self.__file_name,"wb")

      self.__xml_root = ET.fromstring("<VLSV></VLSV>")
      self.__fileindex_for_cellid={}

      self.__offset = 0
      # Write endianness
      np.array(0, dtype=np.uint64).tofile(self.__fptr)
      # Write xml_offset, for now put this to zero:
      np.array(0, dtype=np.uint64).tofile(self.__fptr)

      self.__initialize( vlsvReader )

   def __initialize( self, vlsvReader ):
      ''' Writes the xml footer as well as the cell ids from the vlsvReader to the file and everything else needed for the grid
      '''
      # Get the xml sheet:
      xml_root = vlsvReader._VlsvReader__xml_root

      # Get list of tags to write:
      tags = {}
      tags['PARAMETER'] = ''
      tags['PARAMETERS'] = ''
      tags['MESH_NODE_CRDS_X'] = ''
      tags['MESH_NODE_CRDS_Y'] = ''
      tags['MESH_NODE_CRDS_Z'] = ''
      tags['MESH'] = ''
      tags['MESH_DOMAIN_SIZES'] = ''
      tags['CellID'] = ''
      tags['MESH_BBOX'] = ''
      tags['COORDS'] = ''

      # Copy the xml root
      for child in xml_root:
         if child.tag in tags:
            if 'name' in child.attrib: name = child.attrib['name']
            else: name = ''
            if 'mesh' in child.attrib: mesh = child.attrib['mesh']
            else: mesh = ''
            tag = child.tag
            extra_attribs = {}
            for i in child.attrib.iteritems():
               if i[0] != 'name' and i[0] != 'mesh':
                  extra_attribs[i[0]] = i[1]
            data = vlsvReader.read( name=name, tag=tag, mesh=mesh )
            # Write the data:
            self.write( data=data, name=name, tag=tag, mesh=mesh, extra_attribs=extra_attribs )

      #



   def write(self, data, name, tag, mesh, extra_attribs={}):
      ''' Writes an array into the vlsv file

      :param name: Name of the data array
      :param tag:  Tag of the data array.
      :param mesh: Mesh for the data array
      :param extra_attribs: Dictionary with whatever xml attributes that should be defined in the array that aren't name, tag, or mesh

      :returns: True if the data was written successfully

      '''
      # Make sure the data is in numpy array format:
      data = np.atleast_1d(data)
      fptr = self.__fptr

      datatype = ''

      # Add the data into the xml data:
      child = ET.SubElement(parent=self.__xml_root, tag=tag)
      child.attrib["name"] = name
      child.attrib["mesh"] = mesh
      child.attrib["arraysize"] = len(np.atleast_1d(data))
      if extra_attribs != '':
         for i in extra_attribs.iteritems():
            child.attrib[i[0]] = i[1]
      if len(np.shape(data)) == 2:
         child.attrib["vectorsize"] = np.shape(data)[1]
         datatype = str(type(data[0][0]))
      elif len(np.shape(data)) > 2:
         print "ERROR, np.shape returned len(np.shape(data)) > 2"
         return False
      else:
         child.attrib["vectorsize"] = 1
         datatype = str(type(data[0]))

      # Parse the data types:
      if 'uint' in datatype:
         child.attrib["datatype"] = "uint"
      elif 'int' in datatype:
         child.attrib["datatype"] = "int"
      elif 'float' in datatype:
         child.attrib["datatype"] = "float"
      else:
         print "BAD DATATYPE"
         return False

      if '64' in datatype:
         child.attrib["datasize"] = 8
      elif '32' in datatype:
         child.attrib["datasize"] = 4
      else:
         print "BAD DATASIZE"
         return False

      current_offset = fptr.tell()
      # Info the xml about the file offset for the data:
      child.text = str(current_offset)

      data.tofile(fptr)

      # write the xml footer:
      self.__write_xml_footer()

   def __write_xml_footer( self ):
      # Write the xml footer:
      max_xml_size = 1000000
      if self.__fptr.closed:
         fptr = open(self.__file_name,"wb")
      else:
         fptr = self.__fptr
      current_offset = fptr.tell()
      #self.__xml_root.write( fptr )
      # Convert everything to string:
      for child in self.__xml_root:
         for i in child.attrib.iteritems():
            child.attrib[i[0]] = str(child.attrib[i[0]])
      tree = ET.ElementTree( self.__xml_root)
      tree.write(fptr)
      # Write the offset (first 8 bytes = endianness):
      offset_endianness = 8
      fptr.seek( offset_endianness )
      # Write the offset:
      np.array(current_offset, dtype=np.uint64).tofile(fptr)
      # Go back to the previous offset:
      fptr.seek(current_offset)

   def close( self ):
      self.__write_xml_footer()
      self.__fptr.close()


#   def __initialize( self, vlsvReader ):
#      ''' Writes the xml footer as well as the cell ids from the vlsvReader to the file and everything else needed for the grid
#      '''
#      # Get the xml sheet:
#      xml_root = vlsvReader._VlsvReader__xml_root
#      # Copy the parameters:
#      for child in xml_root:
#         if (child.tag == "PARAMETER" or child.tag == "PARAMETERS") and ("name" in child.attrib):
#            name = child.attrib['name']
#            data = vlsvReader.read_parameter(name)
#            if 'mesh' in child.attrib:
#               self.write(data=data, name=name, tag="PARAMETER", mesh=child.attrib['mesh'])
#            else:
#               self.write(data=data, name=name, tag="PARAMETER", mesh='SpatialGrid')
#
#      wrote_bbox=False
#      for child in xml_root:
#         if child.tag == "MESH_BBOX":
#            # Write mesh bounding box:
#            self.write(data=vlsvReader.read(name="", tag="MESH_BBOX", mesh=child.attrib['mesh']), name="", tag="MESH_BBOX", mesh=child.attrib['mesh'])
#            wrote_bbox=True
#      if wrote_bbox == False:
#         xcells = vlsvReader._VlsvReader__xcells
#         ycells = vlsvReader._VlsvReader__ycells
#         zcells = vlsvReader._VlsvReader__zcells
#         notBlockBasedMesh = 1 # 1 because we are not interested in block based mesh
#         self.write(data=np.array([xcells,ycells,zcells, notBlockBasedMesh, notBlockBasedMesh, notBlockBasedMesh]), name="", tag="MESH_BBOX", mesh="SpatialGrid")
#
#      wrote_nodes=False
#      for child in xml_root:
#         if child.tag == "MESH_NODE_CRDS_X":
#            # Write nodes:
#            self.write(data=vlsvReader.read(name="", tag="MESH_NODE_CRDS_X", mesh=child.attrib['mesh']), name="", tag="MESH_NODE_CRDS_X", mesh="SpatialGrid")
#            wrote_nodes=True
#
#
#      # Write cell ids:
#      self.write(data=vlsvReader.read_variable(name="CellID"), name="CellID", tag="VARIABLE", mesh="SpatialGrid")
#
#      # Some attributes for the MESH array that are mandatory to define:
#      newformat=False
#      for child in xml_root:
#         if child.tag == "MESH" and 'type' in child.attrib:
#            newformat=True
#            extra_attribs = {}
#            for i in child.attrib.iteritems():
#               extra_attribs[i[0]] = i[1]
#
#      if newformat == False:
#         extra_attribs = {}
#         extra_attribs['type'] = "multi_ucd"
#         extra_attribs['xperiodic'] = 'yes'
#         extra_attribs['yperiodic'] = 'yes'
#         extra_attribs['zperiodic'] = 'yes'
#
#      # Write zone global ids:
#      self.write(data=vlsvReader.read(name="SpatialGrid", tag="MESH", mesh=""), name="SpatialGrid", tag="MESH", mesh="", extra_attribs=extra_attribs)
#
#      # Write domain sizes
#      self.write(data=vlsvReader.read( name='', tag='MESH_DOMAIN_SIZES', mesh="SpatialGrid" ), name='', tag='MESH_DOMAIN_SIZES', mesh="SpatialGrid" )
#
