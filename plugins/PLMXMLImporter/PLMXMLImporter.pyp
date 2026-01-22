"""
PLMXML Assembly Importer Plugin for Cinema 4D 2025
Plugin ID: 1054321
Version: 3.13
"""

import c4d
from c4d import plugins, gui, documents
import sys
import os
import xml.etree.ElementTree as ET
from collections import defaultdict
import traceback
import time
import redshift
import maxon
import math

# Redshift constants
REDSHIFT_SHADER_GV_ID = 1036746
REDSHIFT_NODESPACE_ID = "com.redshift3d.redshift4c4d.class.nodespace"

# Plugin ID
PLUGIN_ID = 1054321

# Store the file path for reloading
PLUGIN_FILE_PATH = __file__

def reload_plugin_classes():
    """Reload only the class definitions from the plugin file"""
    try:
        print(f"📂 Reading plugin code from: {PLUGIN_FILE_PATH}")
        
        # Read the current file
        with open(PLUGIN_FILE_PATH, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # Find the start of class definitions and end before plugin registration
        # We want to reload everything between imports and the "if __name__" block
        
        # Split the code to exclude the registration part
        lines = code.split('\n')
        class_code_lines = []
        in_main_block = False
        
        for line in lines:
            # Skip the registration block
            if 'if __name__ ==' in line or in_main_block:
                in_main_block = True
                continue
            # Skip import statements we already have
            if line.strip().startswith('import ') or line.strip().startswith('from '):
                continue
            # Skip the reload function itself
            if 'def reload_plugin_classes' in line:
                break
                
            class_code_lines.append(line)
        
        class_code = '\n'.join(class_code_lines)
        
        # Execute just the class definitions in the current module's namespace
        exec(class_code, globals())
        
        print(f"✓ Reloaded plugin classes successfully")
        return True
        
    except Exception as e:
        print(f"✗ Failed to reload plugin classes: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


class Logger:
    """Dual output logging system with immediate flush capability"""
    
    def __init__(self, log_file_path):
        self.log_file_path = log_file_path
        self.file_handle = None
        self._open_file()
    
    def _open_file(self):
        """Open the log file"""
        try:
            self.file_handle = open(self.log_file_path, 'w', encoding='utf-8')
        except Exception as e:
            print(f"Could not create log file: {e}")
    
    def log(self, message, level='INFO', indent_level=0):
        """Log message to both console and file"""
        import datetime
        indent = " " * indent_level
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}:{indent} {message}"
        
        print(formatted_message)
        
        if self.file_handle:
            try:
                self.file_handle.write(formatted_message + "\n")
                self.file_handle.flush()
            except:
                pass
    
    def close(self):
        """Close the log file"""
        if self.file_handle:
            self.file_handle.close()

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union
import re
import sys

class Transform:
    def __init__(self, element):
        self.id = element.get('id')
        # Parse the 16 float values into a 4x4 matrix
        text_content = element.text or ""
        float_values = [float(x) for x in text_content.split() if x.strip()]
        # Reshape into 4x4 matrix
        self.matrix = [float_values[i:i+4] for i in range(0, 16, 4)]

    def to_dict(self):
        return {
            'id': self.id,
            'matrix': self.matrix
        }

    def matrix_as_string(self):
        """Return the matrix as a single line string representation with 3 decimal places.
        Returns 'Identity' if the matrix is an identity matrix."""
        if self.matrix:
            # Check if it's an identity matrix
            is_identity = True
            for i in range(4):
                for j in range(4):
                    expected_val = 1.0 if i == j else 0.0
                    if abs(self.matrix[i][j] - expected_val) > 1e-9:  # Use small epsilon for float comparison
                        is_identity = False
                        break
                if not is_identity:
                    break

            if is_identity:
                return "Identity"

            # Flatten the 4x4 matrix to a single line with 3 decimal places
            flat_matrix = [f"{val:.3f}" for row in self.matrix for val in row]
            return "[" + " ".join(flat_matrix) + "]"
        return "[]"

class UserData:
    def __init__(self, element):
        self.type = element.get('type')
        self.user_values = [UserValue(child) for child in element if child.tag.endswith('UserValue')]

    def to_dict(self):
        return {
            'type': self.type,
            'user_values': [uv.to_dict() for uv in self.user_values]
        }

class UserValue:
    def __init__(self, element):
        self.title = element.get('title')
        self.value = element.get('value')

    def to_dict(self):
        return {
            'title': self.title,
            'value': self.value
        }

class TableAttribute:
    def __init__(self, element):
        self.definition_ref = element.get('definitionRef')
        self.rows = [Row(child) for child in element if child.tag.endswith('Row')]

    def to_dict(self):
        return {
            'definition_ref': self.definition_ref,
            'rows': [row.to_dict() for row in self.rows]
        }

class Row:
    def __init__(self, element):
        self.columns = [Column(child) for child in element if child.tag.endswith('Column')]

    def to_dict(self):
        return {
            'columns': [col.to_dict() for col in self.columns]
        }

class Column:
    def __init__(self, element):
        self.col = int(element.get('col'))
        self.value = element.get('value')

    def to_dict(self):
        return {
            'col': self.col,
            'value': self.value
        }

class BaseObject:
    """Base class for objects that have an id attribute"""
    def __init__(self, element):
        self.id = element.get('id')

    def to_dict(self):
        return {
            'id': self.id
        }

class Part(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.name = element.get('name')
        self.representation_refs = element.get('representationRefs')
        self.instance_refs = element.get('instanceRefs')

        # Child elements
        self.representation = None
        self.transform = None
        self.user_data = []
        self.table_attribute = None
        # Will be populated later with referenced objects
        self.child_objects = []

        for child in element:
            if child.tag.endswith('Representation'):
                self.representation = Representation(child)
            elif child.tag.endswith('Transform'):
                self.transform = Transform(child)
            elif child.tag.endswith('UserData'):
                self.user_data.append(UserData(child))
            elif child.tag.endswith('TableAttribute'):
                self.table_attribute = TableAttribute(child)

        # Initialize nomenclature from UserData with title 'Nomenclature'
        self.nomenclature = None
        for user_data in self.user_data:
            for user_value in user_data.user_values:
                if user_value.title == 'Nomenclature':
                    self.nomenclature = user_value.value
                    break
            if self.nomenclature is not None:
                break

    def to_dict(self):
        result = {
            'id': self.id,
            'name': self.name,
            'representation_refs': self.representation_refs,
            'instance_refs': self.instance_refs,
        }
        if self.representation:
            result['representation'] = self.representation.to_dict()
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        if self.table_attribute:
            result['table_attribute'] = self.table_attribute.to_dict()
        if self.child_objects:
            result['child_objects'] = [co.id for co in self.child_objects]  # Only show IDs to avoid circular refs
        return result

class Representation(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.format = element.get('format')
        self.compound_reps = [CompoundRep(child) for child in element if child.tag.endswith('CompoundRep')]

    def to_dict(self):
        return {
            'id': self.id,
            'format': self.format,
            'compound_reps': [cr.to_dict() for cr in self.compound_reps]
        }

class CompoundRep(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.format = element.get('format')
        self.location = element.get('location')
        self.name = element.get('name')

        # Child elements
        self.transform = None
        self.user_data = []
        self.table_attributes = []

        for child in element:
            if child.tag.endswith('Transform'):
                self.transform = Transform(child)
            elif child.tag.endswith('UserData'):
                self.user_data.append(UserData(child))
            elif child.tag.endswith('TableAttribute'):
                self.table_attributes.append(TableAttribute(child))

    def to_dict(self):
        result = {
            'id': self.id,
            'format': self.format,
            'location': self.location,
            'name': self.name
        }
        if self.transform:
            result['transform'] = self.transform.to_dict()
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        if self.table_attribute:
            result['table_attribute'] = self.table_attribute.to_dict()
        return result

class Instance(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.part_ref = element.get('partRef')
        self.quantity = int(element.get('quantity', 1)) if element.get('quantity') else 1

        # Child elements
        self.transform = None
        self.user_data = []

        for child in element:
            if child.tag.endswith('Transform'):
                self.transform = Transform(child)
            elif child.tag.endswith('UserData'):
                self.user_data.append(UserData(child))

        # Will be populated later with referenced Part objects
        self.part_references = []

        # Initialize nomenclature from UserData with title 'Nomenclature'
        self.nomenclature = None
        for user_data in self.user_data:
            for user_value in user_data.user_values:
                if user_value.title == 'Nomenclature':
                    self.nomenclature = user_value.value
                    break
            if self.nomenclature is not None:
                break

    def to_dict(self):
        result = {
            'id': self.id,
            'part_ref': self.part_ref,
            'quantity': self.quantity
        }
        if self.transform:
            result['transform'] = self.transform.to_dict()
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        if self.part_references:
            result['part_references'] = [pr.id for pr in self.part_references]  # Only show IDs to avoid circular refs
        return result

class GeneralObject(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.class_name = element.get('class')
        self.user_data = [UserData(child) for child in element if child.tag.endswith('UserData')]

    def to_dict(self):
        result = {
            'id': self.id,
            'class_name': self.class_name
        }
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        return result

class Relation(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.related_refs = element.get('relatedRefs')
        self.sub_type = element.get('subType')
        self.user_data = [UserData(child) for child in element if child.tag.endswith('UserData')]

        # Will be populated later with referenced objects
        self.related_objects = []

    def to_dict(self):
        result = {
            'id': self.id,
            'related_refs': self.related_refs,
            'sub_type': self.sub_type
        }
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        if self.related_objects:
            result['related_objects'] = [ro.id for ro in self.related_objects]  # Only show IDs to avoid circular refs
        return result

class Context(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.ref_config = element.get('refConfig')

    def to_dict(self):
        return {
            'id': self.id,
            'ref_config': self.ref_config
        }

class Contexts:
    def __init__(self, element):
        self.context = None
        for child in element:
            if child.tag.endswith('Context'):
                self.context = Context(child)

    def to_dict(self):
        result = {}
        if self.context:
            result['context'] = self.context.to_dict()
        return result

class TableAttributeDefinition(BaseObject):
    def __init__(self, element):
        super().__init__(element)
        self.columns = [Column(child) for child in element if child.tag.endswith('Column')]

    def to_dict(self):
        return {
            'id': self.id,
            'columns': [col.to_dict() for col in self.columns]
        }

class Definitions:
    def __init__(self, element):
        self.table_attribute_definitions = [
            TableAttributeDefinition(child)
            for child in element
            if child.tag.endswith('TableAttributeDefinition')
        ]

    def to_dict(self):
        return {
            'table_attribute_definitions': [tad.to_dict() for tad in self.table_attribute_definitions]
        }

class Header:
    def __init__(self, element):
        self.author = element.get('author')
        self.creation_date = element.get('creationDate')
        self.definition = element.get('definition')
        self.extension_version = element.get('extensionVersion')
        self.smaragd_version = element.get('smaragdVersion')

        self.user_data = []
        self.contexts = None
        self.definitions = None

        for child in element:
            if child.tag.endswith('UserData'):
                self.user_data.append(UserData(child))
            elif child.tag.endswith('Contexts'):
                self.contexts = Contexts(child)
            elif child.tag.endswith('Definitions'):
                self.definitions = Definitions(child)

    def to_dict(self):
        result = {
            'author': self.author,
            'creation_date': self.creation_date,
            'definition': self.definition,
            'extension_version': self.extension_version,
            'smaragd_version': self.smaragd_version
        }
        if self.user_data:
            result['user_data'] = [ud.to_dict() for ud in self.user_data]
        if self.contexts:
            result['contexts'] = self.contexts.to_dict()
        if self.definitions:
            result['definitions'] = self.definitions.to_dict()
        return result

class InstanceGraph:
    def __init__(self, element):
        self.root_refs = element.get('rootRefs')
        self.instances = [Instance(child) for child in element if child.tag.endswith('Instance')]
        self.parts = [Part(child) for child in element if child.tag.endswith('Part')]
        self.general_objects = [GeneralObject(child) for child in element if child.tag.endswith('GeneralObject')]
        self.relations = [Relation(child) for child in element if child.tag.endswith('Relation')]

    def to_dict(self):
        return {
            'root_refs': self.root_refs,
            'instances': [inst.to_dict() for inst in self.instances],
            'parts': [part.to_dict() for part in self.parts],
            'general_objects': [go.to_dict() for go in self.general_objects],
            'relations': [rel.to_dict() for rel in self.relations]
        }

class ProductDef:
    def __init__(self, element):
        self.instance_graph = None
        for child in element:
            if child.tag.endswith('InstanceGraph'):
                self.instance_graph = InstanceGraph(child)

    def to_dict(self):
        result = {}
        if self.instance_graph:
            result['instance_graph'] = self.instance_graph.to_dict()
        return result

class PLMXML:
    def __init__(self, element):
        self.author = element.get('author')
        self.date = element.get('date')
        self.schema_version = float(element.get('schemaVersion'))
        self.time = element.get('time')
        self.schema_location = element.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation')

        self.product_def = None
        self.header = None

        for child in element:
            if child.tag.endswith('ProductDef'):
                self.product_def = ProductDef(child)
            elif child.tag.endswith('Header'):
                self.header = Header(child)

    def to_dict(self):
        result = {
            'author': self.author,
            'date': self.date,
            'schema_version': self.schema_version,
            'time': self.time,
            'schema_location': self.schema_location
        }
        if self.product_def:
            result['product_def'] = self.product_def.to_dict()
        if self.header:
            result['header'] = self.header.to_dict()
        return result

def parse_plmxml(xml_string: str) -> PLMXML:
    """
    Parse the PLMXML XML string and build the object relational structure in memory.
    Creates global ID map and resolves references.
    """
    root = ET.fromstring(xml_string)

    # Create the main PLMXML object
    plmxml = PLMXML(root)

    # Build global object map
    id_to_object_map: Dict[str, BaseObject] = {}

    # Add all objects with IDs to the map
    def add_to_map(obj_list):
        for obj in obj_list:
            if hasattr(obj, 'id') and obj.id:
                id_to_object_map[obj.id] = obj

    # Add objects from the parsed structure
    if plmxml.product_def and plmxml.product_def.instance_graph:
        graph = plmxml.product_def.instance_graph
        add_to_map(graph.instances)
        add_to_map(graph.parts)
        add_to_map(graph.general_objects)
        add_to_map(graph.relations)

    # Handle parts in representations
    if plmxml.product_def and plmxml.product_def.instance_graph:
        for rep in [part.representation for part in plmxml.product_def.instance_graph.parts if part.representation]:
            if rep:
                add_to_map(rep.compound_reps)

    # Resolve partRef references for Instance objects
    if plmxml.product_def and plmxml.product_def.instance_graph:
        for instance in plmxml.product_def.instance_graph.instances:
            if instance.part_ref:
                refs = instance.part_ref.split()
                instance.part_references = [id_to_object_map[ref] for ref in refs if ref in id_to_object_map]

    # Resolve relatedRefs for Relation objects
    if plmxml.product_def and plmxml.product_def.instance_graph:
        for relation in plmxml.product_def.instance_graph.relations:
            if relation.related_refs:
                refs = relation.related_refs.split()
                relation.related_objects = [id_to_object_map[ref] for ref in refs if ref in id_to_object_map]

    # Resolve instanceRefs for Part objects
    if plmxml.product_def and plmxml.product_def.instance_graph:
        for part in plmxml.product_def.instance_graph.parts:
            if part.instance_refs:
                refs = part.instance_refs.split()
                part.child_objects = [id_to_object_map[ref] for ref in refs if ref in id_to_object_map]

    return plmxml

def find_line_number(text: str, position: int) -> int:
    """
    Find the line number for a given character position in text.
    """
    lines = text[:position].splitlines()
    return len(lines)


###---------------------------------
###---------------------------------
###---------------------------------
###---------------------------------

class AssemlyCreator:
    """Step 3: Assembly creation"""
    
    def traverse_hierarchy(self, op):
        """Generator that yields all objects in the hierarchy."""
        while op:
            yield op
            # Traverse children
            for child in self.traverse_hierarchy(op.GetDown()):
                yield child
            op = op.GetNext()

    def __init__(self, logger, doc, working_directory):
        self.logger = logger
        self.doc = doc
        self.working_directory = working_directory

    def get_child_node(self, name, parentNode=None, indent_level=0):
        """Get or create root node """
        it = None
        if parentNode is None:
            it = self.doc.GetFirstObject()
        else:
            it = parentNode.GetDown()
        while it:
            if it.GetName() == name:
                return it
            it = it.GetNext()
        # not found, create it
        node = c4d.BaseObject(c4d.Onull)
        node.SetName(name)
        node[c4d.NULLOBJECT_DISPLAY] = 14
        if parentNode is None:
            self.doc.InsertObject(node)
        else:
            node.InsertUnder(parentNode)
        return node

    def create_c4d_transfrom_from_transform(self, transform_matrix, scale_factor=100.0):
        """Convert 4x4 matrix to Cinema 4D transformation matrix and scale from meter to centimeters"""
        m = c4d.Matrix()
        
        # Apply coordinate flip directly to rotation columns
        m.v1 = c4d.Vector(transform_matrix[0][0], transform_matrix[0][1], -transform_matrix[0][2]) 
        m.v2 = c4d.Vector(transform_matrix[1][0], transform_matrix[1][1], -transform_matrix[1][2])
        m.v3 = c4d.Vector(-transform_matrix[2][0], -transform_matrix[2][1], transform_matrix[2][2])

        m.off = c4d.Vector(
            transform_matrix[3][0] * scale_factor,
            transform_matrix[3][1] * scale_factor,
            -transform_matrix[3][2] * scale_factor
        )
        return m

    def create_null_node(self, parentNode, name, transform=None, indent_level=0):
        """Create a new c4d null node"""
        node = c4d.BaseObject(c4d.Onull)
        node.SetName(name)
        node[c4d.NULLOBJECT_DISPLAY] = 14
        self.doc.InsertObject(node)
        node.InsertUnder(parentNode)
        if transform:
            c4d_transform = self.create_c4d_transfrom_from_transform(transform.matrix, 100.0)
            node.SetMl(c4d_transform)
            self.logger.log(F"+-> Create Null: name='{node.GetName()}', transform={transform.matrix}", indent_level=indent_level)
            self.logger.log(F"+-> Create Null: name='{node.GetName()}', transform={c4d_transform} ===================", indent_level=indent_level)
        else:
            self.logger.log(F"+-> Create Null: name='{node.GetName()}', transform=IDENTITY", indent_level=indent_level)
        return node

    def create_redshift_proxy(self, proxy_root, parent_obj, jt_path, transform=None, indent_level=0):
        """Process compile redshift proxies mode - creates assembly with proxy references"""
        # check if proxy is already loaded
        jt_name = os.path.splitext(os.path.basename(jt_path))[0]
        jt_null_obj = None
        child = proxy_root.GetDown()  # Get the first child
        while child:
            if child.GetName() == jt_name:  # Replace with your target child name
                print(F"Found child {jt_name}, reuse rs proxy ***************")
                jt_null_obj = child
                break  # Stop once found
            child = child.GetNext()  # Move to the next sibling

        if jt_null_obj:
            self.logger.log(F"+-> reuse from proxy lib: name='jt_name'", indent_level=indent_level)
        else:
            self.logger.log(F"+-> add to proxy lib: name='{jt_name}'", indent_level=indent_level)
            jt_null_obj = self.create_null_node(proxy_root, jt_name, indent_level=indent_level)
            
            # Check if proxy file exists
            proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
            proxy_path = os.path.join(self.working_directory, proxy_filename)    
            proxy_exists = os.path.exists(proxy_path)
            if proxy_exists:
                self.logger.log(F"+-> proxy file {proxy_path} exists, load the proxy file", indent_level=indent_level)
                # Create a new Redshift Proxy object
                proxy_obj = c4d.BaseObject(1038649) # Redshift proxy plugin ID: com.redshift3d.redshift4c4d.proxyloader
                # Set the proxy file path (just the filename, not full path, as per requirements)
                proxy_filename_only = os.path.basename(proxy_path)
                proxy_obj.SetName(proxy_filename_only)
                self.doc.InsertObject(proxy_obj)
                proxy_obj.InsertUnder(parent_obj)

                # Create User Data and XPresso Tag -> work around to be able to set the proxy file name
                bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
                bc[c4d.DESC_NAME] = "ProxyName"
                bc[c4d.DESC_SHORT_NAME] = "ProxyName"
                bc[c4d.DESC_DEFAULT] = proxy_filename_only
                user_data_id = proxy_obj.AddUserData(bc)
                proxy_obj[user_data_id] = proxy_filename_only
                xpresso_tag = c4d.BaseTag(c4d.Texpresso)
                proxy_obj.InsertTag(xpresso_tag)
                xpresso_tag.SetName("XPresso")
                node_master = xpresso_tag.GetNodeMaster()
                proxy_node = node_master.CreateNode(node_master.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=100, y=100)
                proxy_node[c4d.GV_OBJECT_OBJECT_ID] = proxy_obj
                userdata_node = node_master.CreateNode(node_master.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=100, y=250)
                userdata_node[c4d.GV_OBJECT_OBJECT_ID] = proxy_obj
                userdata_output = userdata_node.AddPort(c4d.GV_PORT_OUTPUT, user_data_id)
                file_desc_id = c4d.DescID(c4d.DescLevel(10000, 1036765, 1038649))
                proxy_input = proxy_node.AddPort(c4d.GV_PORT_INPUT, file_desc_id)
                userdata_output.Connect(proxy_input)
                
                # move node under the JT null object
                proxy_obj.InsertUnder(jt_null_obj)  
                proxy_obj[c4d.REDSHIFT_PROXY_DISPLAY_BOUNDBOX] = False
                proxy_obj[c4d.REDSHIFT_PROXY_DISPLAY_MODE] = 2
            else:
                self.logger.log(F"+-> proxy file {proxy_path} DOES NOT exist, create placeholder cube", indent_level=indent_level)
                proxy_obj = c4d.BaseObject(c4d.Ocube)
                proxy_obj[c4d.PRIM_CUBE_LEN] = c4d.Vector(500.0, 500.0, 500.0)  # Size in Cinema 4D units
                proxy_obj.SetName("Placeholder_Cube")
                self.doc.InsertObject(proxy_obj)
                proxy_obj.InsertUnder(jt_null_obj)
                proxy_obj[c4d.ID_BASEOBJECT_GENERATOR_FLAG] = False
        
        # In the Assemply tree: Create an instance reference to the proxy null object in the library and add transformation
        instance = c4d.BaseObject(c4d.Oinstance)
        instance.SetName(jt_name + "_Instance")
        instance[c4d.INSTANCEOBJECT_LINK] = jt_null_obj
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        self.doc.InsertObject(instance)
        instance.InsertUnder(parent_obj)
        if transform:
            c4d_transform = self.create_c4d_transfrom_from_transform(transform.matrix, 100.0)
            instance.SetMl(c4d_transform)
            self.logger.log(F"+-> Proxy instance added to assembly: {instance.GetName()} with transform {transform.matrix}", indent_level=indent_level)
            self.logger.log(F"+-> Proxy instance added to assembly: {instance.GetName()} with transform {c4d_transform} *******************************", indent_level=indent_level)
        else:
            self.logger.log(F"+-> Proxy instance added to assembly: {instance.GetName()} with transform IDENTITY", indent_level=indent_level)




################
################
################

    def collect_materials(self, fileName, plmxml_obj: PLMXML):
        self.numberOfProcessedObjects = 0

        """ Output the object hierarchy in a brief format showing only key attributes and indentation for nesting. """
        # Add header information if available (headers don't have IDs, only attributes)
        if plmxml_obj.header:
            self.logger.log(f"Header: author={plmxml_obj.header.author}")

        # Add ProductDef information with proper nesting
        if plmxml_obj.product_def and plmxml_obj.product_def.instance_graph:
            graph = plmxml_obj.product_def.instance_graph
            self.logger.log(f"InstanceGraph: rootRefs={graph.root_refs}")

            # Create maps of all objects for quick lookup
            self.part_map = {part.id: part for part in graph.parts}
            self.instance_map = {instance.id: instance for instance in graph.instances}

            # Create maps for representations and compound reps
            self.repr_map = {}
            self.compound_rep_map = {}
            for part in graph.parts:
                if part.representation:
                    self.repr_map[part.representation.id] = part.representation
                    for compound_rep in part.representation.compound_reps:
                        self.compound_rep_map[compound_rep.id] = compound_rep

            # Track which objects have already been output to avoid duplicates
            self.output_objects = set()

            # Determine root objects from rootRefs attribute
            if graph.root_refs:
                root_ids = graph.root_refs.split()
            else:
                # If no rootRefs, consider all top-level parts and instances
                root_ids = []

            # Output all root objects and their hierarchy
            for root_id in root_ids:
                self.collect_materials_recursive(root_id, 0)

    # Function to recursively output the hierarchy starting from a root object ID
    def collect_materials_recursive(self, obj_id, indent_level):
        if self.numberOfProcessedObjects > 0:
            return

        # If it's a part
        if obj_id in self.part_map:
            part = self.part_map[obj_id]
            part_line = f"Part: id={part.id}"
            if part.instance_refs:
                part_line += f", instanceRefs={part.instance_refs}"
            if part.representation_refs:
                part_line += f", representationRefs={part.representation_refs}"
            if part.nomenclature:
                part_line += f", nomenclature='{part.nomenclature}'"
            self.logger.log(part_line, indent_level=indent_level)
            self.output_objects.add(obj_id)

            # Dive deeper: Show representation of this part if it exists
            if part.representation:
                self.collect_materials_recursive(part.representation.id, indent_level + 1)

            # Show child objects of this part (from instanceRefs)
            if part.child_objects:
                for child_obj in part.child_objects:
                    if isinstance(child_obj, Instance) or isinstance(child_obj, Part) or isinstance(child_obj, CompoundRep):
                        self.collect_materials_recursive(child_obj.id, indent_level + 1)

        # If it's an instance
        elif obj_id in self.instance_map:
            instance = self.instance_map[obj_id]
            instance_line = f"Instance: id={instance.id}"
            if instance.part_ref:
                instance_line += f", partRef={instance.part_ref}"
            # Add nomenclature if it exists
            if instance.nomenclature:
                instance_line += f", nomenclature='{instance.nomenclature}'"
            self.output_objects.add(obj_id)

            # write line for this instance to the logger
            self.logger.log(instance_line, indent_level=indent_level)

            # Dive deeper: If the instance references a part, output that part as a child
            if instance.part_ref:
                referenced_part_ids = instance.part_ref.split()
                for ref_part_id in referenced_part_ids:
                    self.collect_materials_recursive(ref_part_id, indent_level + 1)

        # If it's a representation
        elif obj_id in self.repr_map:
            repr_obj = self.repr_map[obj_id]
            if repr_obj.id not in self.output_objects:
                repr_line = f"Representation: id={repr_obj.id}"
                self.logger.log(repr_line, indent_level=indent_level)
                self.output_objects.add(repr_obj.id)

                # Dive deeper: Show compound reps associated with this representation
                for compound_rep in repr_obj.compound_reps:
                    self.collect_materials_recursive(compound_rep.id, indent_level + 1)

        # If it's a compound rep
        elif obj_id in self.compound_rep_map:
            compound_rep_obj = self.compound_rep_map[obj_id]
            if compound_rep_obj.id not in self.output_objects:
                cr_line = f"CompoundRep: id={compound_rep_obj.id}"
                if compound_rep_obj.location:
                    cr_line += f", location={compound_rep_obj.location}"
                if compound_rep_obj.name:
                    cr_line += f", name={compound_rep_obj.name}"
                self.logger.log(cr_line, indent_level=indent_level)
                self.output_objects.add(compound_rep_obj.id)

            # Check if jt file exists - ignore if not found
            jt_path = os.path.join(self.working_directory, compound_rep_obj.location)
            if not os.path.exists(jt_path):
                self.logger.log(f"⚠ JT file does not exist: {jt_path} - ignoring materials an geometry", "WARNING")
                return         

            # ensure all materials of this part ar in material c4d meterial libary as redshift materials
            for table in compound_rep_obj.table_attributes:
                if table.definition_ref == "j0MaterialDetailMatrix":
                    self.logger.log(F"Material Table:", indent_level=indent_level)
                    for row in table.rows:
                        for column in row.columns:
                            self.logger.log(F"{column.col} = '{column.value}'", indent_level=indent_level)
                    materialName = F"{table.rows[0].columns[0].value} {table.rows[0].columns[4].value} {table.rows[0].columns[7].value}"
                    materialName = re.sub(r'[^A-Za-z0-9_.]', "_", materialName)
                    materialName = re.sub(r'_+', "_", materialName)
                    self.logger.log(F"Material Name: {materialName}", indent_level=indent_level)

            # check wheter a redshift proxy file already exists - if so we are done
            proxy_path = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
            proxy_path = os.path.join(self.working_directory, proxy_path)

            self.logger.log(f"ℹ working   : {self.working_directory}")
            self.logger.log(f"ℹ jt_path   : {jt_path}")
            self.logger.log(f"ℹ proxy_path: {proxy_path}")

            proxy_exists = os.path.exists(proxy_path)
            if proxy_exists:
                self.logger.log(f"ℹ Redshift proxy already exists, skipping creation: {proxy_path}")
                return
            self.logger.log(f"ℹ Redshift proxy DOES NOT exist: {proxy_path}")

            # Load geometry from JT file into temporary c4d document
            temp_doc = self.doc # c4d.documents.BaseDocument()
            load_success = False                
            try:
                self.logger.log(f"⏳ Loading JT file: {jt_path}")
                load_success = c4d.documents.MergeDocument(
                    temp_doc, 
                    jt_path, 
                    c4d.SCENEFILTER_OBJECTS # | c4d.SCENEFILTER_MATERIALS
                )
            except Exception as e:
                self.logger.log(f"✗ EXCEPTION during JT load: {str(e)}", "ERROR")
                temp_doc = None
                return

            # Get the first object from temp document (there may be multiple root objects)
            self.logger.log(f"⏳ JT file loaded sucessfully: {jt_path}")
            temp_obj = temp_doc.GetFirstObject()
            if temp_obj is None:
                self.logger.log(f"⚠ No geometry found in JT file: {jt_path}", "WARNING")
                temp_doc = None
                return

            # If there is at least one object that names contains the substring FINAL_PART: Delete all other objects
            all_objects = list(self.traverse_hierarchy(temp_doc.GetFirstObject()))
            keep = [obj for obj in all_objects if "FINAL_PART" in obj.GetName()]
            if keep:
                self.logger.log("✓ Found objects with 'FINAL_PART'. Deleting all others...")
                proxy_root = self.get_child_node("Proxy", None)
                keep_set = set(keep)

                # Move objects not in 'keep' to root before removing anything
                for obj in all_objects:
                    if obj in keep_set:
                        if obj.GetUp() is not None: # if not a root node already
                            obj.Remove()  
                            obj.InsertUnder(proxy_root)

                # delete all nodes except proxy root
                it = temp_doc.GetFirstObject()
                while it:
                    if it != proxy_root:
                        it.Remove()
                    it = it.GetNext()

                # Now safe to remove objects that are not in 'keep'
#                for obj in all_objects:
#                    if obj not in keep_set:
#                        obj.Remove()
#            else:                
#                self.logger.log(f"✓ There were no objects that names contains the substring FINAL_PART")

            self.numberOfProcessedObjects = self.numberOfProcessedObjects + 1

            # select all objects for export
            first_obj = self.doc.GetFirstObject()
            if first_obj:
                for obj in self.traverse_hierarchy(first_obj):
                    obj.SetBit(c4d.BIT_ACTIVE)

            self.logger.log("⏳ pause after replace with materials from the PLMXML file specification to prevent race conditions...")
            c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
            self.doc.FlushUndoBuffer()  # If you don't need undo
            c4d.EventAdd()
            c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
            # Light viewport update
            c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
            self.doc.FlushUndoBuffer()  # If you don't need undo
            c4d.EventAdd()
            c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

            # save temp_doc as redhift proxy file
            try:
                format_id = 1038650
                self.logger.log(f"✓ Save redshift proxy in this file: {proxy_path}")
                if c4d.documents.SaveDocument(temp_doc, proxy_path, c4d.SAVEDOCUMENTFLAGS_DONTADDTORECENTLIST, format_id):
                    self.logger.log(f"✅ Redshift proxy processing completed.")
                else:
                    self.logger.log(f"❌ Redshift proxy export failed.", "ERROR")
            except Exception as e:
                self.logger.log(f"✗ Redshift proxy export failed with format {format_id} into {proxy_path}, Exception {str(e)}", "ERROR")
            
            # Clean up temp document
#            first_obj = self.doc.GetFirstObject()
#            if first_obj:
#                for obj in self.traverse_hierarchy(first_obj):
#                    obj.Remove()
            temp_doc = None

            # Update Cinema 4D to reflect selection changes
            c4d.EventAdd()







################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################
################################################################################################################################






    def build_assembly(self, fileName, plmxml_obj: PLMXML):
        """ Output the object hierarchy in a brief format showing only key attributes and indentation for nesting. """
        # Add header information if available (headers don't have IDs, only attributes)
        if plmxml_obj.header:
            self.logger.log(f"Header: author={plmxml_obj.header.author}")

        # Add ProductDef information with proper nesting
        if plmxml_obj.product_def and plmxml_obj.product_def.instance_graph:
            graph = plmxml_obj.product_def.instance_graph
            self.logger.log(f"InstanceGraph: rootRefs={graph.root_refs}")

            # Create maps of all objects for quick lookup
            self.part_map = {part.id: part for part in graph.parts}
            self.instance_map = {instance.id: instance for instance in graph.instances}

            # Create maps for representations and compound reps
            self.repr_map = {}
            self.compound_rep_map = {}
            for part in graph.parts:
                if part.representation:
                    self.repr_map[part.representation.id] = part.representation
                    for compound_rep in part.representation.compound_reps:
                        self.compound_rep_map[compound_rep.id] = compound_rep

            # Track which objects have already been output to avoid duplicates
            self.output_objects = set()

            # Determine root objects from rootRefs attribute
            if graph.root_refs:
                root_ids = graph.root_refs.split()
            else:
                # If no rootRefs, consider all top-level parts and instances
                root_ids = []

            # Create the root structure that will contain the whole PLMXML contents
            document_root = self.get_child_node(os.path.basename(fileName), None)
            proxy_root    = self.get_child_node("Proxies", document_root)
            proxy_root[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.MODE_OFF
            proxy_root[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = c4d.MODE_OFF
            assembly_root = self.get_child_node("Assembly", document_root)
            assembly_root.SetRelRot(c4d.Vector(0, -c4d.utils.DegToRad(90), 0))

            # Output all root objects and their hierarchy
            for root_id in root_ids:
                self.output_object_recursive(root_id, proxy_root, assembly_root, document_root, 0)

            # Output relations
            for relation in graph.relations:
                relation_line = f"Relation: id={relation.id}"
                if relation.related_refs:
                    relation_line += f", relatedRefs={relation.related_refs}"
                self.logger.log(relation_line)

    # Function to recursively output the hierarchy starting from a root object ID
    # obj_id          Object ID in the plmxml file
    # proxy_root      Null node that is the parent to all prxy nodes
    # assembly_root   Null node that is the parent to all assemply root nodes
    # parent_node     Parent node that should be tha parent of the new node
    # indent_level    Indet level for debug output
    def output_object_recursive(self, obj_id, proxy_root, assembly_root, parent_node, indent_level):
        # Check if this object has already been output
#            if obj_id in self.output_objects:
#                return

        # If it's a part
        if obj_id in self.part_map:
            part = self.part_map[obj_id]
            part_line = f"Part: id={part.id}"
            if part.instance_refs:
                part_line += f", instanceRefs={part.instance_refs}"
            if part.representation_refs:
                part_line += f", representationRefs={part.representation_refs}"
            if part.nomenclature:
                part_line += f", nomenclature='{part.nomenclature}'"
            self.logger.log(part_line, indent_level=indent_level)
            self.output_objects.add(obj_id)

            # Show transform if it exists
            if part.transform:
                transform_line = f"+-> Transform: id={part.transform.id}"
                if part.transform.matrix:
                    transform_line += f", matrix={part.transform.matrix}"
                self.logger.log(transform_line, indent_level=indent_level)

            # Create a new child node for this part
            new_child_node = self.create_null_node(parent_node, F"Part: {part.nomenclature}", part.transform, indent_level=indent_level)

            # Dive deeper: Show representation of this part if it exists
            if part.representation:
                self.output_object_recursive(part.representation.id, proxy_root, assembly_root, new_child_node, indent_level + 1)

            # Show child objects of this part (from instanceRefs)
            if part.child_objects:
                for child_obj in part.child_objects:
                    if isinstance(child_obj, Instance) or isinstance(child_obj, Part) or isinstance(child_obj, CompoundRep):
                        self.output_object_recursive(child_obj.id, proxy_root, assembly_root, new_child_node, indent_level + 1)

        # If it's an instance
        elif obj_id in self.instance_map:
            instance = self.instance_map[obj_id]
            instance_line = f"Instance: id={instance.id}"
            if instance.part_ref:
                instance_line += f", partRef={instance.part_ref}"
            # Add nomenclature if it exists
            if instance.nomenclature:
                instance_line += f", nomenclature='{instance.nomenclature}'"
            self.output_objects.add(obj_id)

            # write line for this instance to the logger
            self.logger.log(instance_line, indent_level=indent_level)

            # Show transform if it exists
            if instance.transform:
                transform_line = f"+-> Transform: id={instance.transform.id}"
                if instance.transform.matrix:
                    transform_line += f", matrix={instance.transform.matrix}"
                self.logger.log(transform_line, indent_level=indent_level)

            # Create a new child node for this part
            new_child_node = self.create_null_node(parent_node, F"Inst: {instance.nomenclature}", instance.transform, indent_level=indent_level)

            # Dive deeper: If the instance references a part, output that part as a child
            if instance.part_ref:
                referenced_part_ids = instance.part_ref.split()
                for ref_part_id in referenced_part_ids:
                    self.output_object_recursive(ref_part_id, proxy_root, assembly_root, new_child_node, indent_level + 1)

        # If it's a representation
        elif obj_id in self.repr_map:
            repr_obj = self.repr_map[obj_id]
            if repr_obj.id not in self.output_objects:
                repr_line = f"Representation: id={repr_obj.id}"
                self.logger.log(repr_line, indent_level=indent_level)
                self.output_objects.add(repr_obj.id)

                # Dive deeper: Show compound reps associated with this representation
                for compound_rep in repr_obj.compound_reps:
                    self.output_object_recursive(compound_rep.id, proxy_root, assembly_root, parent_node, indent_level + 1)

        # If it's a compound rep
        elif obj_id in self.compound_rep_map:
            compound_rep_obj = self.compound_rep_map[obj_id]
            if compound_rep_obj.id not in self.output_objects:
                cr_line = f"CompoundRep: id={compound_rep_obj.id}"
                if compound_rep_obj.location:
                    cr_line += f", location={compound_rep_obj.location}"
                if compound_rep_obj.name:
                    cr_line += f", name={compound_rep_obj.name}"
                self.logger.log(cr_line, indent_level=indent_level)
                self.output_objects.add(compound_rep_obj.id)

                # Show transform if it exists
                if compound_rep_obj.transform:
                    transform_line = f"+-> Transform: id={compound_rep_obj.transform.id}"
                    if compound_rep_obj.transform.matrix:
                        transform_line += f", matrix={compound_rep_obj.transform.matrix}"
                    self.logger.log(transform_line, indent_level=indent_level)

                # add instance reference to proxy
                self.create_redshift_proxy(proxy_root, parent_node, compound_rep_obj.location, compound_rep_obj.transform, indent_level)





def step1_collect_materials(logger, doc, working_directory, plmxml_file_path):
    xml_content = None  # Initialize to avoid UnboundLocalError
    try:
        with open(plmxml_file_path, 'r', encoding="latin-1") as file:
            xml_content = file.read()
        plmxml_obj = parse_plmxml(xml_content)
        assemly_creator = AssemlyCreator(logger, doc, working_directory)
        assemly_creator.collect_materials(plmxml_file_path, plmxml_obj)
    except FileNotFoundError:
        print(f"Error: File '{plmxml_file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        # Find the line number where the error occurred
        position = e.start if hasattr(e, 'start') else 0
        if xml_content is not None:
            line_num = find_line_number(xml_content, position)
            print(f"Error decoding file: {e}", file=sys.stderr)
            print(f"Error occurred around line {line_num} (position {position})", file=sys.stderr)
        else:
            print(f"Error decoding file: {e}", file=sys.stderr)
            print(f"Error occurred at position {e.start if hasattr(e, 'start') else 0}", file=sys.stderr)
        print(f"Try using a different encoding with --encoding option.", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        print(f"Error occurred at line {e.lineno}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


def step3_build_assembly(logger, doc, working_directory, plmxml_file_path):
    xml_content = None  # Initialize to avoid UnboundLocalError
    try:
        with open(plmxml_file_path, 'r', encoding="latin-1") as file:
            xml_content = file.read()
        plmxml_obj = parse_plmxml(xml_content)
        assemly_creator = AssemlyCreator(logger, doc, working_directory)
        assemly_creator.build_assembly(plmxml_file_path, plmxml_obj)
    except FileNotFoundError:
        print(f"Error: File '{plmxml_file_path}' not found.", file=sys.stderr)
        sys.exit(1)
    except UnicodeDecodeError as e:
        # Find the line number where the error occurred
        position = e.start if hasattr(e, 'start') else 0
        if xml_content is not None:
            line_num = find_line_number(xml_content, position)
            print(f"Error decoding file: {e}", file=sys.stderr)
            print(f"Error occurred around line {line_num} (position {position})", file=sys.stderr)
        else:
            print(f"Error decoding file: {e}", file=sys.stderr)
            print(f"Error occurred at position {e.start if hasattr(e, 'start') else 0}", file=sys.stderr)
        print(f"Try using a different encoding with --encoding option.", file=sys.stderr)
        sys.exit(1)
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}", file=sys.stderr)
        print(f"Error occurred at line {e.lineno}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)








    
class MaterialPropertyInference:
    """Static methods for inferring PBR properties based on keywords"""
    
    # Define known material keywords
    METAL_KEYWORDS = ['stahl', 'steel', 'aluminium', 'aluminum', 'kupfer', 'copper', 
                     'brass', 'messing', 'bronze', 'titan', 'titanium', 'eisen', 'iron']
    PLASTIC_KEYWORDS = ['thermoplast', 'plastic', 'kunststoff', 'polymer', 'abs', 'pc', 'pom', 'pa', 'pfa']
    RUBBER_KEYWORDS = ['elastomer', 'gummi', 'rubber', 'tpe', 'tps']
    WOOD_KEYWORDS = ['holz', 'wood']
    GLASS_KEYWORDS = ['glas', 'glass']
    SEALANT_KEYWORDS = ['dichtstoff', 'sealant', 'dichtung']
    
    # Track unknown keywords encountered
    unknown_keywords = set()
    
    @staticmethod
    def infer_material_properties(material_data, logger=None):
        """Infer material properties from material data dictionary - using improved algorithm"""
        # Extract material properties from dcx:TableAttribute columns
        mat_group = material_data.get('mat_group', '')
        mat_standard = material_data.get('mat_standard', '')
        mat_number = material_data.get('mat_number', '')
        mat_term = material_data.get('mat_term', '')
        treatment = material_data.get('treatment', '')
        body_name = material_data.get('body_name', '')
        
        # Use the improved inference algorithm from the example
        props = MaterialPropertyInference.infer_properties(
            mat_group, mat_standard, mat_number, mat_term, treatment
        )
        
        # Track unknown keywords as before
        full_material_desc = f"{mat_group} {mat_standard} {mat_number} {mat_term} {treatment} {body_name}".lower()
        MaterialPropertyInference._track_unknown_keywords(full_material_desc, [], logger)
        
        return props
    
    @staticmethod
    def infer_properties(mat_group, mat_standard, mat_number, mat_term, treatment=''):
        """Infer PBR properties from material description - improved algorithm"""
        text = f"{mat_group} {mat_standard} {mat_number} {mat_term} {treatment}".lower()
        
        props = {
            'base_color': c4d.Vector(0.7, 0.7, 0.7),
            'metalness': 0.0,
            'roughness': 0.5,
            'ior': 1.5,
            'transparency': 0.0  # Added for compatibility
        }
        
        if any(keyword in text for keyword in MaterialPropertyInference.METAL_KEYWORDS):
            props.update(MaterialPropertyInference._metal_properties(text, mat_term))
        elif any(keyword in text for keyword in MaterialPropertyInference.PLASTIC_KEYWORDS):
            props.update(MaterialPropertyInference._plastic_properties(text, mat_term))
        elif any(keyword in text for keyword in MaterialPropertyInference.RUBBER_KEYWORDS):
            props.update(MaterialPropertyInference._rubber_properties(text))
        elif any(keyword in text for keyword in MaterialPropertyInference.WOOD_KEYWORDS):
            props.update(MaterialPropertyInference._wood_properties(text))
        elif any(keyword in text for keyword in MaterialPropertyInference.GLASS_KEYWORDS):
            props.update(MaterialPropertyInference._glass_properties(text))
        elif any(keyword in text for keyword in MaterialPropertyInference.SEALANT_KEYWORDS):
            props.update(MaterialPropertyInference._sealant_properties(text))
        
        return props
    
    @staticmethod
    def _track_unknown_keywords(full_material_desc, known_keywords, logger):
        """Track keywords that are not in our predefined lists"""
        # Split the full description into individual words
        desc_words = full_material_desc.split()
        
        # Check each word against known keywords
        for word in desc_words:
            word = word.strip('.,;:!?()[]{}"\'').lower()
            # If word is not in known keywords and is not empty
            if word and word not in known_keywords:
                # Check if it's also not in any of the other keyword lists
                all_known = (MaterialPropertyInference.METAL_KEYWORDS + 
                           MaterialPropertyInference.PLASTIC_KEYWORDS + 
                           MaterialPropertyInference.RUBBER_KEYWORDS + 
                           MaterialPropertyInference.WOOD_KEYWORDS + 
                           MaterialPropertyInference.GLASS_KEYWORDS + 
                           MaterialPropertyInference.SEALANT_KEYWORDS)
                
                if word not in all_known:
                    # This is a truly unknown keyword
                    MaterialPropertyInference.unknown_keywords.add(word)
                    if logger:
                        logger.log(f"🔍 New material keyword detected: '{word}'", "INFO")
    
    @staticmethod
    def _metal_properties(text, mat_term):
        if 'stahl' in text or 'steel' in text:
            color = c4d.Vector(0.72, 0.72, 0.75)
        elif 'alumin' in text:
            color = c4d.Vector(0.87, 0.88, 0.89)
        elif 'kupfer' in text or 'copper' in text:
            color = c4d.Vector(0.95, 0.64, 0.54)
        elif 'gold' in text:
            color = c4d.Vector(1.0, 0.85, 0.57)
        else:
            color = c4d.Vector(0.7, 0.7, 0.75)
        
        roughness = 0.15 if 'poliert' in text or 'polished' in text else 0.3
        
        return {
            'base_color': color,
            'metalness': 1.0,
            'roughness': roughness,
            'ior': 2.5,
            'transparency': 0.0  # Added for compatibility
        }
    
    @staticmethod
    def _plastic_properties(text, mat_term):
        color = c4d.Vector(0.25, 0.25, 0.30)
        
        if 'schwarz' in text or 'black' in text:
            color = c4d.Vector(0.08, 0.08, 0.08)
        elif 'weiss' in text or 'white' in text:
            color = c4d.Vector(0.95, 0.95, 0.95)
        elif 'grau' in text or 'gray' in text:
            color = c4d.Vector(0.5, 0.5, 0.5)
        
        roughness = 0.3 if 'glanz' in text or 'gloss' in text else 0.5
        
        return {
            'base_color': color,
            'metalness': 0.0,
            'roughness': roughness,
            'ior': 1.49,
            'transparency': 0.0  # Added for compatibility
        }
    
    @staticmethod
    def _rubber_properties(text):
        return {
            'base_color': c4d.Vector(0.10, 0.10, 0.10),
            'metalness': 0.0,
            'roughness': 0.9,
            'ior': 1.52,
            'transparency': 0.0
        }
    
    @staticmethod
    def _wood_properties(text):
        if 'eiche' in text or 'oak' in text:
            color = c4d.Vector(0.65, 0.50, 0.35)
        elif 'buche' in text or 'beech' in text:
            color = c4d.Vector(0.75, 0.60, 0.45)
        else:
            color = c4d.Vector(0.55, 0.35, 0.22)
        
        return {
            'base_color': color,
            'metalness': 0.0,
            'roughness': 0.75,
            'ior': 1.53,
            'transparency': 0.0
        }
    
    @staticmethod
    def _glass_properties(text):
        return {
            'base_color': c4d.Vector(0.95, 0.95, 0.95),
            'metalness': 0.0,
            'roughness': 0.05,
            'ior': 1.52,
            'transparency': 0.95
        }
    
    @staticmethod
    def _sealant_properties(text):
        return {
            'base_color': c4d.Vector(0.15, 0.15, 0.15),
            'metalness': 0.0,
            'roughness': 0.8,
            'ior': 1.5,
            'transparency': 0.0
        }
    
    @staticmethod
    def _default_properties(text):
        return {
            'base_color': c4d.Vector(0.7, 0.7, 0.7),  # Similar to the example
            'metalness': 0.0,
            'roughness': 0.5,
            'ior': 1.5,
            'transparency': 0.0
        }


class Cinema4DMaterialManager:
    """Material creation, caching, and deduplication system"""
    
    def __init__(self, logger):
        self.logger = logger
        self.material_cache = {}  # Dictionary to store created materials
        self.material_properties_cache = {}
    
    def create_material(self, material_data, doc, mode="assembly"):
        """Create a material based on material data - using improved algorithm"""
        # Create a unique material name based on material properties
        mat_name = self._generate_material_name(material_data)
        self.logger.log(f"🔍 Material creation requested for: {mat_name} in mode: {mode}")
        
        # For Step 1 (material extraction), check if we should create Redshift materials
        is_step1 = mode == "material_extraction"
        
        # Show current cache contents for debugging
        self.logger.log(f"📦 Current cache contents: {len(self.material_cache)} items")
        for cache_key, cache_mat in self.material_cache.items():
            self.logger.log(f"  📦 Cache[{cache_key}]: {cache_mat.GetName() if cache_mat else 'None'}")
        
        # Check if we already have this material in our cache
        if mat_name in self.material_cache:
            cached_mat = self.material_cache[mat_name]
            self.logger.log(f"📦 Found material in cache: {cached_mat.GetName() if cached_mat else 'None'}")
            # Verify the cached material is still valid/alive
            # Check if material is a standard material or a Redshift material (if Redshift is available)
            standard_check = (cached_mat.GetType() == c4d.Mmaterial)
            redshift_plugin_id = 1036223  # Redshift plugin ID
            redshift_check = (cached_mat.GetType() == redshift_plugin_id)
            mat_type_check = standard_check or redshift_check
            
            if cached_mat and mat_type_check:
                self.logger.log(f"♻ Reusing cached material: {cached_mat.GetName()}")
                return cached_mat
            else:
                self.logger.log(f"⚠ Cached material is invalid, removing from cache")
                del self.material_cache[mat_name]
        
        # Check if we already have a similar material in the current document
        self.logger.log(f"🔍 Checking if material '{mat_name}' already exists in document")
        # Show all materials currently in the document for debugging
        mat_count = 0
        doc_mat = doc.GetFirstMaterial()
        while doc_mat:
            mat_count += 1
            self.logger.log(f"  🎨 Document material #{mat_count}: {doc_mat.GetName()}")
            doc_mat = doc_mat.GetNext()
        self.logger.log(f"  📊 Total materials in document: {mat_count}")
        
        # For Step 1, use simpler logic - only check for exact name match
        if is_step1:
            existing_material_in_doc = self._find_material_in_document(mat_name, doc)
            if existing_material_in_doc:
                self.logger.log(f"♻ Reusing existing material in document: {existing_material_in_doc.GetName()}")
                # Cache this material to avoid recreation using the actual material name
                actual_mat_name = existing_material_in_doc.GetName()
                self.material_cache[actual_mat_name] = existing_material_in_doc
                # Also make sure the requested name maps to the same material
                self.material_cache[mat_name] = existing_material_in_doc
                # Get its properties for cache
                props = self._extract_material_properties(existing_material_in_doc)
                if props:
                    self.material_properties_cache[actual_mat_name] = props
                    self.material_properties_cache[mat_name] = props
                return existing_material_in_doc
        else:
            # For other modes, use the existing improved algorithm
            existing_material_in_doc = self._find_material_in_document(mat_name, doc)
            if existing_material_in_doc:
                self.logger.log(f"♻ Reusing existing material in document: {existing_material_in_doc.GetName()}")
                # Cache this material to avoid recreation using the actual material name
                actual_mat_name = existing_material_in_doc.GetName()
                self.material_cache[actual_mat_name] = existing_material_in_doc
                # Also make sure the requested name maps to the same material
                self.material_cache[mat_name] = existing_material_in_doc
                # Get its properties for cache
                props = self._extract_material_properties(existing_material_in_doc)
                if props:
                    self.material_properties_cache[actual_mat_name] = props
                    self.material_properties_cache[mat_name] = props
                return existing_material_in_doc
        
        # For Step 1, we can also try to find materials that might have been named differently by C4D
        # This is to handle the case where C4D renamed the material during first creation
        if is_step1:
            # Check if there's already a material that was created from the same source data
            # but got renamed by C4D (e.g. requested "Material.123" but C4D created "Material")
            existing_material = self._find_material_with_same_source_properties(material_data, doc, mode)
            if existing_material:
                self.logger.log(f"♻ Reusing existing material with same source properties: {existing_material.GetName()}")
                # Cache this material to avoid recreation using the actual material name
                actual_mat_name = existing_material.GetName()
                self.material_cache[actual_mat_name] = existing_material
                # Also make sure the requested name maps to the same material
                self.material_cache[mat_name] = existing_material
                # Get its properties for cache
                props = self._extract_material_properties(existing_material)
                if props:
                    self.material_properties_cache[actual_mat_name] = props
                    self.material_properties_cache[mat_name] = props
                return existing_material
        
        # Check if we already have a similar material in our cache using improved algorithm
        if not is_step1:  # Only for non-Step 1 modes
            existing_material = self.find_existing_material(material_data, doc, mode)
            if existing_material:
                self.logger.log(f"♻ Reusing cached material: {existing_material.GetName()}")
                return existing_material
        
        # Get material properties using improved inference algorithm
        props = MaterialPropertyInference.infer_material_properties(material_data, self.logger)
        
        # For Step 1, Redshift must be available
        if is_step1:
            # Create Redshift OpenPBR material for Step 1
            mat = self._create_redshift_material(mat_name, props, doc)
            if mat:
                self.logger.log(f"🎨 Creating Redshift OpenPBR material: {mat_name} (Step 1)")
            else:
                self.logger.log(f"❌ Failed to create Redshift OpenPBR material: {mat_name} (Step 1)", "ERROR")
                return None  # This will cause the process to stop
        else:
            # Create standard Cinema 4D material for other modes
            mat = self._create_standard_material(material_data.get('mat_group', ''), 
                                               material_data.get('mat_standard', ''),
                                               material_data.get('mat_number', ''),
                                               material_data.get('mat_term', ''),
                                               props)
            self.logger.log(f"🎨 Creating standard Cinema 4D material: {mat_name} (Mode: {mode})")
        
        if not mat:
            self.logger.log("✗ Failed to create new material", "ERROR")
            return None
        
        # For standard materials, we may need to insert them into the document
        # Redshift materials are inserted within their creation function
        # Check if the material is already in the document, and if not, insert it
        if not self._verify_material_in_document(mat.GetName(), doc):
            self.logger.log(f"📦 Material '{mat.GetName()}' not found in document, inserting now")
            doc.InsertMaterial(mat)
            # Check if C4D renamed the material during insertion
            actual_name_after_insert = mat.GetName()
            original_name = mat_name if 'mat_name' in locals() else (material_data.get('mat_group', '') + '_' + material_data.get('mat_term', '') + '_' + material_data.get('mat_number', ''))
            if actual_name_after_insert != original_name and '_' in original_name:
                self.logger.log(f"🚨 C4D renamed standard material from something like '{original_name}' to '{actual_name_after_insert}'")
        
        # Verify the material was actually added to the document
        if not self._verify_material_in_document(mat.GetName(), doc):
            self.logger.log(f"⚠ Material may not have been properly added to document: {mat.GetName()}", "WARNING")
        
        # Cache this material using the actual name assigned by C4D (in case it was renamed)
        actual_mat_name = mat.GetName()
        self.material_cache[actual_mat_name] = mat
        self.material_properties_cache[actual_mat_name] = props
        
        # Also make sure the originally requested name maps to the same material for consistency
        if mat_name != actual_mat_name:
            self.material_cache[mat_name] = mat
        
        self.logger.log(f"→ Created material: {actual_mat_name}")
        return mat
    
    def _create_standard_material(self, mat_group, mat_standard, mat_number, mat_term, props):
        """Create Cinema 4D standard material with PBR properties - similar to example"""
        mat = c4d.BaseMaterial(c4d.Mmaterial)
        
        if not mat:
            self.logger.log("ERROR: Could not create Cinema 4D material", "ERROR")
            return None
        
        name_parts = [p for p in [mat_group, mat_term, mat_number] if p]
        original_mat_name = "_".join(name_parts) if name_parts else "Material"
        
        # Sanitize the name to only contain alphanumeric characters, underscores, hyphens, and dots
        import re
        mat_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', original_mat_name)
        self.logger.log(f"🎨 Creating Standard material with original name: '{original_mat_name}' -> sanitized name: '{mat_name}'")
        
        mat.SetName(mat_name)
        self.logger.log(f"   Material object created with requested name: '{mat.GetName()}'")
        
        # Set base color
        mat[c4d.MATERIAL_COLOR_COLOR] = props['base_color']
        mat[c4d.MATERIAL_USE_COLOR] = True
        
        # Setup reflectance for PBR workflow
        mat[c4d.MATERIAL_USE_REFLECTION] = True
        
        # Remove default specular layers
        try:
            reflectance = mat.GetReflectionLayerIndex(0)
            if reflectance:
                layer = reflectance.GetDataID()
                mat.RemoveReflectionLayerID(layer)
        except:
            pass
        
        # Add GGX (PBR) reflection layer
        layer = mat.AddReflectionLayer()
        if layer:
            layer_id = layer.GetDataID()
            
            # Set to GGX (PBR model)
            try:
                mat[layer_id + c4d.REFLECTION_LAYER_MAIN_DISTRIBUTION] = c4d.REFLECTION_DISTRIBUTION_GGX
            except:
                self.logger.log(f"  ⚠ Could not set GGX distribution for '{mat_name}'", "WARNING")
            
            # Set color/reflectivity based on metalness
            try:
                if props['metalness'] > 0.5:
                    # Metallic - use base color as reflection color
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = props['base_color']
                    mat[c4d.MATERIAL_COLOR_COLOR] = c4d.Vector(0, 0, 0)  # Black base for metals
                    
                    # Set fresnel to conductor (metal)
                    try:
                        mat[layer_id + c4d.REFLECTION_LAYER_FRESNEL_MODE] = c4d.REFLECTION_FRESNEL_CONDUCTOR
                    except:
                        pass
                else:
                    # Dielectric - white reflection
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = c4d.Vector(1, 1, 1)
                    
                    # Set fresnel to dielectric
                    try:
                        mat[layer_id + c4d.REFLECTION_LAYER_FRESNEL_MODE] = c4d.REFLECTION_FRESNEL_DIELECTRIC
                    except:
                        pass
            except:
                self.logger.log(f"  ⚠ Could not set reflection color for '{mat_name}'", "WARNING")
            
            # Set roughness
            try:
                # Try different roughness parameter names
                roughness_params = [
                    c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS,
                ]
                for param in roughness_params:
                    try:
                        mat[layer_id + param] = props['roughness']
                        break
                    except:
                        continue
            except:
                self.logger.log(f"  ⚠ Could not set roughness for '{mat_name}'", "WARNING")
            
            # Set reflection strength/brightness
            strength = 1.0 if props['metalness'] > 0.5 else 0.3
            brightness_params = [
                'REFLECTION_LAYER_MAIN_VALUE_BRIGHTNESS',
                'REFLECTION_LAYER_MAIN_SHADER_BRIGHTNESS',
            ]
            
            for param_name in brightness_params:
                try:
                    param = getattr(c4d, param_name, None)
                    if param is not None:
                        mat[layer_id + param] = strength
                        break
                except:
                    continue
        
        # Handle transparency for glass materials
        if 'transparency' in props and props['transparency'] > 0.1:
            try:
                mat[c4d.MATERIAL_USE_TRANSPARENCY] = True
                mat[c4d.MATERIAL_TRANSPARENCY_BRIGHTNESS] = props['transparency']
            except:
                self.logger.log(f"  ⚠ Could not set transparency for '{mat_name}'", "WARNING")
        
        mat.Update(True, True)
        return mat
    

    def _create_redshift_material(self, mat_name, props, doc):
        
        # Sanitize the material name to only contain alphanumeric characters, underscores, hyphens, and dots
        import re
        original_mat_name = mat_name
        mat_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_name)
        self.logger.log(f"🎨 Creating Redshift material with original name: '{original_mat_name}' -> sanitized name: '{mat_name}'")
        
        # Check if a material with identical name already exists in the document
        existing_material = self._find_material_in_document(mat_name, doc)
        if existing_material:
            self.logger.log(f"⚠ Material with name '{mat_name}' already exists in document, reusing existing material")
            return existing_material
        
        # Create material
        mat = c4d.BaseMaterial(c4d.Mmaterial)
        mat.SetName(mat_name)
        self.logger.log(f"   Material object created with requested name: '{mat.GetName()}'")
        
        # Get node material and create graph
        nodeMaterial = mat.GetNodeMaterialReference()
        REDSHIFT_NODESPACE_ID = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")
        graph = nodeMaterial.CreateEmptyGraph(REDSHIFT_NODESPACE_ID)
        
        if graph.IsNullValue():
            raise RuntimeError(f"Failed to create Redshift graph")
        
        # Insert material first and immediately check what name C4D assigned
        doc.InsertMaterial(mat)
        actual_assigned_name = mat.GetName()
        self.logger.log(f"   Material inserted into document. Requested: '{mat_name}', C4D assigned: '{actual_assigned_name}'")
        
        # If C4D changed the name, we should check if this new name already exists
        if actual_assigned_name != mat_name:
            self.logger.log(f"   🚨 WARNING: C4D renamed material from '{mat_name}' to '{actual_assigned_name}'")
            # Check if the material with the new assigned name already exists
            # (this shouldn't happen in a normal case, but if it does we should handle it)
            other_material_with_same_name = self._find_material_in_document(actual_assigned_name, doc)
            if other_material_with_same_name and other_material_with_same_name != mat:
                self.logger.log(f"   ⚠️  Another material with name '{actual_assigned_name}' already exists!")
        
        try:
            # Use the most common/reliable node: Standard Material
            with graph.BeginTransaction() as transaction:
                # These IDs are confirmed to work in most C4D 2025 installations
                outputNode = graph.AddChild(
                    maxon.Id(), 
                    maxon.Id("com.redshift3d.redshift4c4d.node.output")
                )
                materialNode = graph.AddChild(
                    maxon.Id(), 
                    maxon.Id("com.redshift3d.redshift4c4d.nodes.core.standardmaterial")
                )
                
                # Connect them
                outPort = materialNode.GetOutputs().FindChild(
                    "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.outcolor")
                surfacePort = outputNode.GetInputs().FindChild(
                    "com.redshift3d.redshift4c4d.node.output.surface")
                
                if outPort and surfacePort:
                    outPort.Connect(surfacePort)
                
                # Apply PBR properties
                if props:
                    # Base Color
                    if 'base_color' in props:
                        colorPort = materialNode.GetInputs().FindChild(
                            "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color")
                        if colorPort:
                            color = props['base_color']
                            if isinstance(color, (list, tuple)) and len(color) >= 3:
                                colorPort.SetPortValue(maxon.Color(color[0], color[1], color[2]))
                    
                    # Metalness (0.0 for dielectric, 1.0 for metal)
                    if 'metalness' in props:
                        metalnessPort = materialNode.GetInputs().FindChild(
                            "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.metalness")
                        if metalnessPort:
                            metalnessPort.SetPortValue(float(props['metalness']))
                        
                    # Specular roughness
                    if 'roughness' in props:
                        roughnessPort = materialNode.GetInputs().FindChild(
                            "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refl_roughness")
                        if roughnessPort:
                            roughnessPort.SetPortValue(float(props['roughness']))
                    
                    # Specular IOR
                    if 'ior' in props:
                        iorPort = materialNode.GetInputs().FindChild(
                            "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refl_ior")
                        if iorPort:
                            iorPort.SetPortValue(float(props['ior']))
                            
                    # Handle transparency for glass materials
                    if 'transparency' in props and props['transparency'] > 0.1:
                        transparencyPort = materialNode.GetInputs().FindChild(
                            "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.refr_weight")
                        if transparencyPort:
                            transparencyPort.SetPortValue(float(props['transparency']))
                    
                transaction.Commit()
        
        except Exception as e:
            self.logger.log(f"ERROR creating Redshift material nodes: {str(e)}", "ERROR")
            return None

        # Insert material into document
#        doc.InsertMaterial(mat)

        c4d.EventAdd()
        final_name = mat.GetName()
        self.logger.log(f"   ✅ Material creation completed. Final name: '{final_name}'")
        return mat

    def _set_openpbr_properties(self, openpbr_node, props):
        """
        Set properties on an OpenPBR node using the maxon nodes API
        
        Args:
            openpbr_node: The OpenPBR maxon.GraphNode
            props: Dictionary with material properties
        """
        # Port IDs for OpenPBR Surface
        port_ids = {
            'base_color': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.base_color"),
            'base_weight': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.base_weight"),
            'base_metalness': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.base_metalness"),
            'specular_weight': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.specular_weight"),
            'specular_roughness': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.specular_roughness"),
            'specular_ior': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.specular_ior"),
            'transmission_weight': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.transmission_weight"),
            'transmission_color': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.transmission_color"),
            'transmission_depth': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.transmission_depth"),
            'subsurface_weight': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.subsurface_weight"),
            'subsurface_color': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.subsurface_color"),
            'subsurface_radius': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.subsurface_radius"),
        }

        try:
            # Base Color
            if 'base_color' in props:
                color = props['base_color']
                self._set_port_value(openpbr_node, port_ids['base_color'], 
                              maxon.Color(color.x, color.y, color.z))

            # Base Weight
            self._set_port_value(openpbr_node, port_ids['base_weight'], 1.0)

            # Metalness
            if 'metalness' in props:
                self._set_port_value(openpbr_node, port_ids['base_metalness'], props['metalness'])

            # Specular Weight
            self._set_port_value(openpbr_node, port_ids['specular_weight'], 1.0)

            # Roughness
            if 'roughness' in props:
                self._set_port_value(openpbr_node, port_ids['specular_roughness'], props['roughness'])

            # IOR
            if 'ior' in props:
                self._set_port_value(openpbr_node, port_ids['specular_ior'], props['ior'])

            # Transmission (for glass)
            if 'transmission_weight' in props and props['transmission_weight'] > 0:
                self._set_port_value(openpbr_node, port_ids['transmission_weight'], props['transmission_weight'])
                
                if 'transmission_color' in props:
                    color = props['transmission_color']
                    self._set_port_value(openpbr_node, port_ids['transmission_color'],
                                 maxon.Color(color.x, color.y, color.z))
                
                if 'transmission_depth' in props:
                    self._set_port_value(openpbr_node, port_ids['transmission_depth'], props['transmission_depth'])

            # Subsurface (for rubber/skin)
            if 'subsurface_weight' in props and props['subsurface_weight'] > 0:
                self._set_port_value(openpbr_node, port_ids['subsurface_weight'], props['subsurface_weight'])
                
                if 'subsurface_color' in props:
                    color = props['subsurface_color']
                    self._set_port_value(openpbr_node, port_ids['subsurface_color'],
                                 maxon.Color(color.x, color.y, color.z))
                
                if 'subsurface_radius' in props:
                    self._set_port_value(openpbr_node, port_ids['subsurface_radius'], props['subsurface_radius'])

        except Exception as e:
            self.logger.log(f"Error setting OpenPBR properties: {str(e)}", "ERROR")

    def _set_port_value(self, node, port_id, value):
        """
        Set a value on a node port
        """
        try:
            # Find the input port
            for port in node.GetInputs():
                if port.GetId() == port_id:
                    port.SetDefaultValue(value)
                    return True

            # If not found in inputs, try direct value setting
            node.SetValue(port_id, value)
            return True
        except Exception as e:
            self.logger.log(f"Warning: Could not set port {port_id}: {str(e)}", "WARNING")
            return False
    
    def _find_material_in_document(self, mat_name, doc):
        """Find a material with specific name in the document"""
        import re
        # Sanitize the name for consistent comparison
        sanitized_mat_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_name)
        self.logger.log(f"🔍 Searching for material '{mat_name}' (sanitized: {sanitized_mat_name}) in document")
        mat_count = 0
        mat = doc.GetFirstMaterial()
        while mat:
            mat_count += 1
            self.logger.log(f"  🎨 Found material: {mat.GetName()}")
            # Sanitize the existing material name for comparison
            sanitized_existing_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat.GetName())
            if sanitized_existing_name == sanitized_mat_name:
                self.logger.log(f"  ✅ Match found for '{mat_name}' (sanitized: {sanitized_existing_name})")
                return mat
            mat = mat.GetNext()
        self.logger.log(f"  ❌ No match found for '{mat_name}' (checked {mat_count} materials)")
        return None
    
    def _find_material_with_same_source_properties(self, material_data, doc, mode):
        """Find a material that was created from the same source properties (for Step 1)"""
        # This method looks for materials that may have been created from the same source
        # but renamed by C4D (e.g., requested "Material.123" but C4D created "Material")
        import re
        
        # Look for materials that start with the same base pattern but might have been truncated
        mat_group = material_data.get('mat_group', 'Unknown')
        mat_term = material_data.get('mat_term', 'Unknown') 
        mat_number = material_data.get('mat_number', 'Unknown')
        
        # Create base pattern (sanitized)
        base_parts = [p for p in [mat_group, mat_term, mat_number] if p]
        base_name = "_".join(base_parts) if base_parts else "Material"
        base_name_sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', base_name)
        
        self.logger.log(f"🔍 Searching for material with same source properties. Base pattern: '{base_name_sanitized}'")
        
        mat = doc.GetFirstMaterial()
        while mat:
            existing_name = mat.GetName()
            existing_name_sanitized = re.sub(r'[^a-zA-Z0-9_.-]', '_', existing_name)
            
            self.logger.log(f"  🎨 Checking material: '{existing_name}' (sanitized: '{existing_name_sanitized}')")
            
            # Check if this material name starts with our base pattern (could be truncated version)
            if existing_name_sanitized.startswith(base_name_sanitized):
                self.logger.log(f"    🔄 Base pattern match found: '{existing_name_sanitized}' starts with '{base_name_sanitized}'")
                
                # Check if it's just a truncated version (like "Material" for "Material.123")
                remaining = existing_name_sanitized[len(base_name_sanitized):]
                if not remaining or (remaining.startswith('.') and remaining[1:].replace('-', '').replace('_', '').isalnum()):
                    self.logger.log(f"    ✅ Potential truncated version: '{existing_name}' matches '{base_name_sanitized}'")
                    self.logger.log(f"    ✅ Returning material based on name pattern match: '{existing_name}'")
                    return mat
            
            # Check the reverse - if our requested pattern is a truncated version of existing
            elif base_name_sanitized.startswith(existing_name_sanitized):
                remaining = base_name_sanitized[len(existing_name_sanitized):]
                if remaining.startswith('.') and remaining[1:].replace('-', '').replace('_', '').isalnum():
                    self.logger.log(f"    🔄 Reverse pattern match: requested '{base_name_sanitized}' vs existing '{existing_name_sanitized}'")
                    self.logger.log(f"    ✅ Returning material based on reverse pattern match: '{existing_name}'")
                    return mat
            
            mat = mat.GetNext()
        
        self.logger.log(f"  ❌ No material found with same source properties")
        return None
    
    def _verify_material_in_document(self, mat_name, doc):
        """Verify that a material with specific name exists in the document"""
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == mat_name:
                return True
            mat = mat.GetNext()
        return False
    
    def _extract_material_properties(self, mat):
        """Extract material properties from an existing material"""
        # This is a simplified property extraction - in a real implementation 
        # you might want to extract more properties
        props = {
            'base_color': mat[c4d.MATERIAL_COLOR_COLOR] if mat[c4d.MATERIAL_COLOR_COLOR] else c4d.Vector(0.5, 0.5, 0.5),
            'metalness': 0.0,  # Would need to calculate from reflections in a real implementation
            'roughness': 0.4,  # Default value
            'ior': 1.4,
            'transparency': 0.0
        }
        return props
    
    def find_existing_material(self, material_data, doc, mode="assembly"):
        """Find existing similar material using improved algorithm"""
        self.logger.log("🔍 Checking for existing material using improved algorithm")
        
        # Extract material properties for comparison
        mat_group = material_data.get('mat_group', '')
        mat_standard = material_data.get('mat_standard', '')
        mat_number = material_data.get('mat_number', '')
        mat_term = material_data.get('mat_term', '')
        treatment = material_data.get('treatment', '')
        
        # Generate material name
        name_parts = [p for p in [mat_group, mat_term, mat_number] if p]
        mat_name = "_".join(name_parts) if name_parts else "Material"
        self.logger.log(f"  🏷️ Looking for material with name: {mat_name}")
        
        # Check cache first (already created in this import session)
        signature = self._get_material_signature(mat_group, mat_standard, mat_number, mat_term)
        self.logger.log(f"  📦 Checking cache for signature: {signature}")
        if signature in self.material_cache:
            cached_mat = self.material_cache[signature]
            self.logger.log(f"  📦 Found material in cache by signature: {cached_mat.GetName() if cached_mat else 'None'}")
            # Check if the cached material is valid
            # Check if material is a standard material or a Redshift material (if Redshift is available)
            standard_check = (cached_mat.GetType() == c4d.Mmaterial)
            redshift_plugin_id = 1036223  # Redshift plugin ID
            redshift_check = (cached_mat.GetType() == redshift_plugin_id)
            mat_type_check = standard_check or redshift_check
            
            if cached_mat and mat_type_check:
                return cached_mat
        
        # Check if identical material already exists in document
        self.logger.log(f"  🔍 Searching document for existing material: {mat_name}")
        existing_mat = self._find_existing_material_improved(mat_name, mat_group, mat_standard, mat_number, mat_term, treatment, doc, mode)
        if existing_mat:
            self.logger.log(f"♻ Reusing existing material: {existing_mat.GetName()}")
            # Cache using both the signature and the actual material name
            actual_mat_name = existing_mat.GetName()
            self.material_cache[signature] = existing_mat
            self.material_cache[actual_mat_name] = existing_mat
            return existing_mat
        
        return None
    
    def _get_material_signature(self, mat_group, mat_standard, mat_number, mat_term):
        """Generate a signature for material caching"""
        sig = f"{mat_group}|{mat_standard}|{mat_number}|{mat_term}".strip()
        return sig
    
    def _find_existing_material_improved(self, mat_name, mat_group, mat_standard, mat_number, mat_term, treatment, doc, mode="assembly"):
        """Check if a material with matching name and properties already exists - using improved algorithm"""
        self.logger.log(f"🔍 _find_existing_material_improved called with: name={mat_name}, group={mat_group}, standard={mat_standard}, number={mat_number}, term={mat_term}, treatment={treatment}, mode={mode}")
        
        # Extract material properties for comparison
        props = MaterialPropertyInference.infer_material_properties(
            {
                'mat_group': mat_group,
                'mat_standard': mat_standard,
                'mat_number': mat_number,
                'mat_term': mat_term,
                'treatment': treatment
            }, self.logger
        )
        
        # Use the provided document parameter
        
        # First pass: Look for exact name match (using sanitized names for consistency)
        import re
        sanitized_mat_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_name)
        self.logger.log(f"  🔍 First pass - searching for exact name match: {mat_name} (sanitized: {sanitized_mat_name})")
        mat = doc.GetFirstMaterial()
        while mat:
            self.logger.log(f"    🎨 Checking material: {mat.GetName()}, Type: {mat.GetType()}")
            
            # Check if material matches type requirements based on mode
            material_type_match = False
            if mode == "material_extraction":
                # In Step 1, look for Redshift materials if available - use plugin ID instead of Mredshift
                redshift_plugin_id = 1036223  # Redshift plugin ID
                material_type_match = (mat.GetType() == redshift_plugin_id)
            else:
                # For other modes, look for either standard or Redshift materials (if available)
                standard_match = (mat.GetType() == c4d.Mmaterial)
                redshift_plugin_id = 1036223  # Redshift plugin ID
                redshift_match = (mat.GetType() == redshift_plugin_id)
                material_type_match = standard_match or redshift_match
            
            # Sanitize the existing material name for comparison  
            sanitized_existing_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat.GetName())
            if material_type_match and sanitized_existing_name == sanitized_mat_name:
                self.logger.log(f"    ✅ Exact name match found: {mat.GetName()} (sanitized: {sanitized_existing_name})")
                if self._compare_material_properties(mat, props):
                    self.logger.log(f"    ✅ Properties also match, returning: {mat.GetName()}")
                    return mat
                else:
                    self.logger.log(f"    ❌ Properties don't match for: {mat.GetName()}")
            mat = mat.GetNext()
        
        self.logger.log(f"  ❌ No exact name match found for: {mat_name}")
        
        # Second pass: Look for materials with same base type (more lenient)
        # Extract material base type (first part before underscore/slash) and sanitize it
        import re
        mat_base_type = mat_name.split('_')[0] if '_' in mat_name else mat_name
        mat_base_type = mat_base_type.split('/')[0] if '/' in mat_base_type else mat_base_type
        mat_base_type = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_base_type)  # Sanitize base type
        self.logger.log(f"  🔍 Second pass - searching for materials with base type: {mat_base_type}")
        
        mat = doc.GetFirstMaterial()
        while mat:
            # Check if material matches type requirements based on mode
            material_type_match = False
            if mode == "material_extraction":
                # In Step 1, look for Redshift materials if available - use plugin ID instead of Mredshift
                redshift_plugin_id = 1036223  # Redshift plugin ID
                material_type_match = (mat.GetType() == redshift_plugin_id)
            else:
                # For other modes, look for either standard or Redshift materials (if available)
                standard_match = (mat.GetType() == c4d.Mmaterial)
                redshift_plugin_id = 1036223  # Redshift plugin ID
                redshift_match = (mat.GetType() == redshift_plugin_id)
                material_type_match = standard_match or redshift_match
            
            if material_type_match:
                # Sanitize the existing material's name for consistent comparison
                existing_name = mat.GetName()
                existing_base_type = existing_name.split('_')[0] if '_' in existing_name else existing_name
                existing_base_type = existing_base_type.split('/')[0] if '/' in existing_base_type else existing_base_type
                existing_base_type = re.sub(r'[^a-zA-Z0-9_.-]', '_', existing_base_type)  # Sanitize base type
                self.logger.log(f"    🎨 Checking material base type: {existing_base_type} for material: {mat.GetName()}")
                
                # If base types match (e.g., both "STAHL"), check if properties are similar
                if existing_base_type == mat_base_type:
                    self.logger.log(f"    ✅ Base type match found: {mat.GetName()}")
                    if self._compare_material_properties(mat, props):
                        self.logger.log(f"  → Grouping '{mat_name}' with existing '{mat.GetName()}'")
                        return mat
                    else:
                        self.logger.log(f"    ❌ Properties don't match for base type: {mat.GetName()}")
            mat = mat.GetNext()
        
        self.logger.log(f"  ❌ No base type matches found for: {mat_base_type}")
        
        # Third pass: Look for materials created from the same source properties
        # by inferring properties from existing materials and comparing to target properties
        self.logger.log(f"  🔍 Third pass - searching for materials with matching source properties")
        mat = doc.GetFirstMaterial()
        while mat:
            # Check if material matches type requirements based on mode
            material_type_match = False
            if mode == "material_extraction":
                # In Step 1, look for Redshift materials if available - use plugin ID instead of Mredshift
                redshift_plugin_id = 1036223  # Redshift plugin ID
                material_type_match = (mat.GetType() == redshift_plugin_id)
            else:
                # For other modes, look for either standard or Redshift materials (if available)
                standard_match = (mat.GetType() == c4d.Mmaterial)
                redshift_plugin_id = 1036223  # Redshift plugin ID
                redshift_match = (mat.GetType() == redshift_plugin_id)
                material_type_match = standard_match or redshift_match
            
            if material_type_match:
                # Try to infer what the source properties of this material would have been
                # by using some characteristics of the material name or properties
                inferred_existing_props = self._infer_material_properties_from_existing_material(mat, self.logger)
                
                if inferred_existing_props and self._materials_are_similar(props, inferred_existing_props):
                    self.logger.log(f"  → Found material with similar source properties: {mat.GetName()}")
                    return mat
            mat = mat.GetNext()
        
        self.logger.log(f"  ❌ No materials found with matching source properties")
        
        # Fourth pass: Look for materials that might have been created from similar source
        # but have different names due to C4D renaming (e.g., "Material.1", "Material.2", etc.)
        self.logger.log(f"  🔍 Fourth pass - searching for materials with similar names that might be renamed versions")
        
        # Check if the document already contains a material that was likely created from the same source
        # by looking for materials that have similar starting patterns but were suffixed by C4D
        # For example, if we're looking for "STAHL_STAHLGUSS_20MnB4_1_5525", check for "STAHL_STAHLGUSS_20MnB4_1" or similar
        mat = doc.GetFirstMaterial()
        while mat:
            # Check if material matches type requirements based on mode
            material_type_match = False
            if mode == "material_extraction":
                # In Step 1, look for Redshift materials if available - use plugin ID instead of Mredshift
                redshift_plugin_id = 1036223  # Redshift plugin ID
                material_type_match = (mat.GetType() == redshift_plugin_id)
            else:
                # For other modes, look for either standard or Redshift materials (if available)
                standard_match = (mat.GetType() == c4d.Mmaterial)
                redshift_plugin_id = 1036223  # Redshift plugin ID
                redshift_match = (mat.GetType() == redshift_plugin_id)
                material_type_match = standard_match or redshift_match
            
            if material_type_match:
                existing_name = mat.GetName()
                
                # Check if this material name could be a C4D-renamed version of our requested name
                # by comparing the common prefix and checking if the difference is just a suffix like ".1", ".2", etc.
                # Apply sanitization to both names for consistent comparison
                import re
                sanitized_original = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_name)
                sanitized_existing = re.sub(r'[^a-zA-Z0-9_.-]', '_', existing_name)
                
                if self._could_be_renamed_version(sanitized_original, sanitized_existing):
                    self.logger.log(f"    🔄 Found potentially renamed version: {existing_name} (for requested: {mat_name}, sanitized: {sanitized_original} vs {sanitized_existing})")
                    
                    # If it's likely the same material but with a renamed suffix, check properties too
                    if self._compare_material_properties(mat, props):
                        self.logger.log(f"    ✅ Properties also match, returning: {mat.GetName()}")
                        return mat
                    else:
                        self.logger.log(f"    ❌ Properties don't match for potentially renamed material: {mat.GetName()}")
            mat = mat.GetNext()
        
        self.logger.log(f"  ❌ No renamed version matches found")
        return None
    
    def _could_be_renamed_version(self, original_name, existing_name):
        """
        Check if an existing material name could be a C4D-renamed version of the original name.
        For example: "STAHL_STAHLGUSS_20MnB4_1" vs "STAHL_STAHLGUSS_20MnB4_1.1"
        """
        # Remove any suffixes that look like C4D's numbering (.1, .2, .3, etc.)
        import re
        # Split on the last dot and check if what follows is just numbers
        if '.' in existing_name:
            parts = existing_name.rsplit('.', 1)
            if len(parts) == 2 and parts[1].isdigit():  # If suffix is numeric
                base_existing_name = parts[0]
                return base_existing_name == original_name
        
        # Or check if original_name is a prefix of existing_name with some separator
        if existing_name.startswith(original_name):
            # Check if the rest is a separator followed by numbers (e.g., "_1", "_2")
            remaining = existing_name[len(original_name):]
            if remaining.startswith('_') and remaining[1:].isdigit():
                return True
        
        # Also handle case where C4D truncated part of the name (e.g., original was "name_part1_part2" 
        # but C4D created "name_part1" because it was too long or already existed)
        if original_name.startswith(existing_name):
            # The existing name is a truncated/partial version of the original
            # This could happen when C4D shortens names that are too long or already exist
            original_remaining = original_name[len(existing_name):]
            # If the remaining part starts with underscore or dot (like "_part2" or ".part2"), it might be truncated
            if original_remaining.startswith('_') or original_remaining.startswith('.'):
                # Check if the truncated part is numeric or specific material ID-like
                separator = original_remaining[0]  # '_' or '.'
                remaining_part = original_remaining[1:]
                if remaining_part.replace('.', '').replace('-', '').replace('_', '').isalnum():
                    return True
        
        # Also handle the reverse case where the existing name is the truncated version
        # For example: we're looking for "Material" but C4D truncated "Material.123" to "Material"
        if existing_name.startswith(original_name):
            existing_remaining = existing_name[len(original_name):]
            if existing_remaining.startswith('_') or existing_remaining.startswith('.'):
                remaining_part = existing_remaining[1:]
                if remaining_part.replace('.', '').replace('-', '').replace('_', '').isalnum():
                    return True
        
        return False
    
    def _infer_material_properties_from_existing_material(self, mat, logger):
        """Infer source material properties from an existing material"""
        try:
            # Start with default values
            props = {
                'base_color': c4d.Vector(0.7, 0.7, 0.7),
                'metalness': 0.0,
                'roughness': 0.5,
                'ior': 1.5,
                'transparency': 0.0
            }
            
            # Get the material name to extract keyword-based inferences
            mat_name = mat.GetName().lower()
            
            # Update properties based on material name keywords (similar to inference algorithm)
            if any(keyword in mat_name for keyword in MaterialPropertyInference.METAL_KEYWORDS):
                props.update(MaterialPropertyInference._metal_properties(mat_name, mat_name))
            elif any(keyword in mat_name for keyword in MaterialPropertyInference.PLASTIC_KEYWORDS):
                props.update(MaterialPropertyInference._plastic_properties(mat_name, mat_name))
            elif any(keyword in mat_name for keyword in MaterialPropertyInference.RUBBER_KEYWORDS):
                props.update(MaterialPropertyInference._rubber_properties(mat_name))
            elif any(keyword in mat_name for keyword in MaterialPropertyInference.WOOD_KEYWORDS):
                props.update(MaterialPropertyInference._wood_properties(mat_name))
            elif any(keyword in mat_name for keyword in MaterialPropertyInference.GLASS_KEYWORDS):
                props.update(MaterialPropertyInference._glass_properties(mat_name))
            elif any(keyword in mat_name for keyword in MaterialPropertyInference.SEALANT_KEYWORDS):
                props.update(MaterialPropertyInference._sealant_properties(mat_name))
            else:
                # Extract base properties from actual material values
                try:
                    props['base_color'] = mat[c4d.MATERIAL_COLOR_COLOR] if mat[c4d.MATERIAL_COLOR_COLOR] else c4d.Vector(0.7, 0.7, 0.7)
                except:
                    pass
                
                # Get reflection properties if available
                try:
                    if mat[c4d.MATERIAL_USE_REFLECTION]:
                        layer = mat.GetReflectionLayerIndex(0)
                        if layer:
                            layer_id = layer.GetDataID()
                            try:
                                props['roughness'] = mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS]
                            except:
                                pass
                                
                            # Estimate metalness based on reflection color and Fresnel settings
                            try:
                                fresnel_mode = mat[layer_id + c4d.REFLECTION_LAYER_FRESNEL_MODE]
                                props['metalness'] = 1.0 if fresnel_mode == c4d.REFLECTION_FRESNEL_CONDUCTOR else 0.0
                            except:
                                # If we can't determine from fresnel, estimate based on reflection color
                                try:
                                    refl_color = mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR]
                                    # If reflection color is grayish, likely dielectric; if colored, possibly metallic
                                    props['metalness'] = 0.0  # Default to non-metallic
                                except:
                                    pass
                except:
                    pass
            
            return props
        except Exception as e:
            logger.log(f"Error inferring properties from existing material: {str(e)}", "WARNING")
            return None
    
    def _compare_material_properties(self, mat, props):
        """Compare existing material properties with target properties - uses lenient tolerance"""
        
        # Use lenient tolerance to group very similar materials
        color_tolerance = 0.1  # Allow 10% difference in color
        property_tolerance = 0.15  # Allow 15% difference in roughness/properties
        
        mat_type = mat.GetType()

        # Handle Redshift material comparison - check using plugin ID instead of Mredshift constant
        redshift_plugin_id = 1036223  # Redshift plugin ID (built into C4D 2025)
        if mat_type == redshift_plugin_id:
            # Since Redshift is built into Cinema 4D 2025, import is always available
            import redshift
            import maxon

            # Handle Redshift material comparison using the modern nodes API
            try:
                # Get node material reference
                nodeMaterial = mat.GetNodeMaterialReference()
                if not nodeMaterial:
                    return False
                
                # Get the graph - try multiple approaches for Redshift integration
                graph = None
                try:
                    graph = nodeMaterial.GetGraph(maxon.Id(REDSHIFT_NODESPACE_ID))
                except:
                    try:
                        graph = nodeMaterial.GetGraph(REDSHIFT_NODESPACE_ID)
                    except:
                        # If both fail, try active graph
                        try:
                            graph = nodeMaterial.GetActiveGraph()
                        except:
                            pass
                if not graph:
                    return False
                
                # Find the OpenPBR node in the graph
                openpbr_node = None
                rs_openpbr_id = maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface")
                
                for node in graph.GetRoot().GetChildren():
                    if node.GetValue(maxon.NODE.BASE.ASSETID) == rs_openpbr_id:
                        openpbr_node = node
                        break
                
                if not openpbr_node:
                    # If no OpenPBR node found, fallback to other methods
                    return False
                
                # Port IDs for OpenPBR Surface
                port_ids = {
                    'base_color': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.base_color"),
                    'base_metalness': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.base_metalness"),
                    'specular_roughness': maxon.Id("com.redshift3d.redshift4c4d.nodes.core.openpdrsurface.specular_roughness"),
                }
                
                # Get base color from node
                try:
                    color_port = None
                    for port in openpbr_node.GetInputs():
                        if port.GetId() == port_ids['base_color']:
                            color_port = port
                            break
                    
                    if color_port:
                        existing_color = color_port.GetDefaultValue()
                        if isinstance(existing_color, maxon.Color):
                            existing_color = c4d.Vector(existing_color.x, existing_color.y, existing_color.z)
                        else:
                            # Get default value differently if it's not a color
                            existing_color = c4d.Vector(0.5, 0.5, 0.5)
                    else:
                        existing_color = c4d.Vector(0.5, 0.5, 0.5)
                except:
                    existing_color = c4d.Vector(0.5, 0.5, 0.5)
                
                target_color = props['base_color']
                if (abs(existing_color.x - target_color.x) > color_tolerance or
                    abs(existing_color.y - target_color.y) > color_tolerance or
                    abs(existing_color.z - target_color.z) > color_tolerance):
                    return False
                
                # Check metalness
                try:
                    metalness_port = None
                    for port in openpbr_node.GetInputs():
                        if port.GetId() == port_ids['base_metalness']:
                            metalness_port = port
                            break
                    
                    if metalness_port:
                        existing_metalness = metalness_port.GetDefaultValue()
                    else:
                        existing_metalness = 0.0
                except:
                    existing_metalness = 0.0
                
                target_metalness = props['metalness']
                if abs(existing_metalness - target_metalness) > property_tolerance:
                    return False
                
                # Check roughness
                try:
                    roughness_port = None
                    for port in openpbr_node.GetInputs():
                        if port.GetId() == port_ids['specular_roughness']:
                            roughness_port = port
                            break
                    
                    if roughness_port:
                        existing_roughness = roughness_port.GetDefaultValue()
                    else:
                        existing_roughness = 0.5  # Default roughness
                except:
                    existing_roughness = 0.5  # Default roughness
                
                target_roughness = props['roughness']
                if abs(existing_roughness - target_roughness) > property_tolerance:
                    return False
                
                return True
            except:
                # If Redshift comparison fails, fall back to basic comparison
                pass

        # Default to standard Cinema 4D material comparison
        # Check base color
        try:
            existing_color = mat[c4d.MATERIAL_COLOR_COLOR]
        except:
            return False  # Can't access required property
            
        target_color = props['base_color']
        if (abs(existing_color.x - target_color.x) > color_tolerance or
            abs(existing_color.y - target_color.y) > color_tolerance or
            abs(existing_color.z - target_color.z) > color_tolerance):
            return False

        # For standard materials, check reflection
        try:
            if not mat[c4d.MATERIAL_USE_REFLECTION]:
                return False
        except:
            pass  # Continue even if we can't check reflection setting

        # For standard materials
        try:
            # Check reflectance layer
            layer = mat.GetReflectionLayerIndex(0)
            if not layer:
                # If no reflection layer, try to check if we can create one or make a basic assumption
                pass
            else:
                layer_id = layer.GetDataID()
                
                # Check roughness with lenient tolerance
                try:
                    existing_roughness = mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS]
                    if abs(existing_roughness - props['roughness']) > property_tolerance:
                        return False
                except:
                    pass  # If we can't check roughness, continue

                # Check metalness (approximated by fresnel mode and color)
                try:
                    fresnel_mode = mat[layer_id + c4d.REFLECTION_LAYER_FRESNEL_MODE]
                    is_metal = (fresnel_mode == c4d.REFLECTION_FRESNEL_CONDUCTOR)
                    target_is_metal = (props['metalness'] > 0.5)
                    
                    if is_metal != target_is_metal:
                        return False
                except:
                    pass  # If we can't check fresnel mode, continue
        except:
            pass  # If reflection layer checks fail, continue with basic checks

        # All properties are similar enough!
        return True
    
    def _materials_are_similar(self, props1, props2, color_tolerance=0.1, property_tolerance=0.15):
        """Check if two material properties are similar within tolerance"""
        # Compare base colors
        color_diff = abs(props1['base_color'] - props2['base_color'])
        color_similar = all(c < color_tolerance for c in [color_diff.x, color_diff.y, color_diff.z])
        
        # Compare other properties
        roughness_similar = abs(props1['roughness'] - props2['roughness']) < property_tolerance
        metalness_similar = abs(props1['metalness'] - props2['metalness']) < property_tolerance
        
        return color_similar and roughness_similar and metalness_similar
    
    def _generate_material_name(self, material_data):
        """Generate material name based on material properties"""
        mat_group = material_data.get('mat_group', 'Unknown')
        mat_term = material_data.get('mat_term', 'Unknown')
        mat_number = material_data.get('mat_number', 'Unknown')
        
        # Format: {mat_group}_{mat_term}_{mat_number}
        mat_name = f"{mat_group}_{mat_term}_{mat_number}"
        
        # Sanitize the name to only contain alphanumeric characters, underscores, hyphens, and dots
        # Replace any character that is not alphanumeric, underscore, hyphen, or dot with underscore
        import re
        sanitized_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', mat_name)
        
        self.logger.log(f"🏷️ Generated material name: {mat_name} -> {sanitized_name} (from group='{mat_group}', term='{mat_term}', number='{mat_number}')")
        return sanitized_name


class PLMXMLParser:
    """XML parsing with namespace handling and hierarchy extraction"""
    
    def __init__(self, logger):
        self.logger = logger
        self.namespaces = {
            'plm': 'http://www.plmxml.org/Schemas/PLMXMLSchema',
            'dcx': 'http://www.smaragd.dcx.com/Schemas/Smaragd'
        }
        self.parts = {}
        self.instances = {}
        self.instance_graph = {}
        self.root_refs = []
    
    def parse_plmxml(self, file_path):
        """Parse the main PLMXML file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract instance graph
            self._parse_instance_graph(root)
            
            # Extract parts
            self._parse_parts(root)
            
            self.logger.log(f"✓ Parsed PLMXML: {len(self.instances)} instances, {len(self.parts)} parts")
            return True
            
        except Exception as e:
            self.logger.log(f"✗ Failed to parse PLMXML: {str(e)}", "ERROR")
            return False
    
    def _parse_instance_graph(self, root):
        """Parse the instance graph from the PLMXML"""
        instance_graph_elem = root.find('.//plm:InstanceGraph', self.namespaces)
        if instance_graph_elem is not None:
            # Get root references
            root_refs_attr = instance_graph_elem.get('rootRefs', '')
            self.root_refs = root_refs_attr.split() if root_refs_attr else []
            
            # Parse all instances
            for instance_elem in instance_graph_elem.findall('.//plm:Instance', self.namespaces):
                instance_id = instance_elem.get('id')
                part_ref = instance_elem.get('partRef')
                quantity = instance_elem.get('quantity', '1')
                
                # Extract transform
                transform_elem = instance_elem.find('plm:Transform', self.namespaces)
                transform = None
                if transform_elem is not None:
                    transform = [float(x) for x in transform_elem.text.strip().split()]
                
                # Extract user values
                user_data = {}
                for user_value in instance_elem.findall('.//plm:UserValue', self.namespaces):
                    title = user_value.get('title')
                    value = user_value.get('value')
                    if title and value:
                        user_data[title] = value
                
                self.instances[instance_id] = {
                    'id': instance_id,
                    'part_ref': part_ref,
                    'quantity': int(quantity),
                    'transform': transform,
                    'user_data': user_data,
                    'children': []  # Will be populated later
                }
    
    def _parse_parts(self, root):
        """Parse the parts from the PLMXML"""
        for part_elem in root.findall('.//plm:Part', self.namespaces):
            part_id = part_elem.get('id')
            part_name = part_elem.get('name', '')
            
            # Find representations
            jt_files = []
            for rep_elem in part_elem.findall('.//plm:Representation[@format="JT"]', self.namespaces):
                for compound_elem in rep_elem.findall('.//plm:CompoundRep', self.namespaces):
                    location = compound_elem.get('location')
                    if location:
                        # Extract transform for this representation
                        transform_elem = compound_elem.find('plm:Transform', self.namespaces)
                        transform = None
                        if transform_elem is not None:
                            transform = [float(x) for x in transform_elem.text.strip().split()]
                        
                        # Extract material properties from TableAttribute
                        material_properties = {}
                        table_attr = compound_elem.find('.//dcx:TableAttribute[@definitionRef="j0MaterialDetailMatrix"]', self.namespaces)
                        if table_attr is not None:
                            for row in table_attr.findall('.//dcx:Row', self.namespaces):
                                mat_group = None
                                mat_standard = None
                                mat_number = None
                                treatment = None
                                mat_term = None
                                body_name = None
                                
                                for col in row.findall('.//dcx:Column', self.namespaces):
                                    col_idx = int(col.get('col', '-1'))
                                    col_value = col.get('value', '')
                                    
                                    if col_idx == 0:
                                        mat_group = col_value
                                    elif col_idx == 1:
                                        mat_standard = col_value
                                    elif col_idx == 2:
                                        mat_number = col_value
                                    elif col_idx == 3:
                                        treatment = col_value
                                    elif col_idx == 7:
                                        mat_term = col_value
                                    elif col_idx == 10:
                                        body_name = col_value
                                
                                material_properties = {
                                    'mat_group': mat_group,
                                    'mat_standard': mat_standard,
                                    'mat_number': mat_number,
                                    'treatment': treatment,
                                    'mat_term': mat_term,
                                    'body_name': body_name
                                }
                        
                        jt_files.append({
                            'file': location,
                            'transform': transform,
                            'material_properties': material_properties
                        })
            
            self.parts[part_id] = {
                'id': part_id,
                'name': part_name,
                'jt_files': jt_files
            }
    
    def build_hierarchy(self):
        """Build parent-child relationships in the instance graph"""
        # Create a mapping of parent to children
        parent_child_map = defaultdict(list)
        
        # For now, we'll assume all instances that reference a part are children of root refs
        # In a real implementation, you'd need to parse the full hierarchy structure
        for instance_id, instance_data in self.instances.items():
            # Simple approach - attach to root if it's a root reference
            if instance_id in self.root_refs:
                continue  # Root nodes have no parent in this context
            else:
                # For this example, we'll attach to the first root reference
                if self.root_refs:
                    parent_child_map[self.root_refs[0]].append(instance_id)
        
        # Update instance data with children information
        for parent_id, children_ids in parent_child_map.items():
            if parent_id in self.instances:
                self.instances[parent_id]['children'] = children_ids
        
        return self.root_refs


class GeometryInstanceManager:
    """Geometry caching and instance creation system"""
    
    def __init__(self, logger):
        self.logger = logger
        self.geometry_cache = {}  # JT file path to object mapping
        self._hidden_container = None
    
    def get_or_create_hidden_container(self, doc):
        """Get or create the hidden container for original geometries"""
        if self._hidden_container is None:
            obj = doc.GetFirstObject()
            while obj:
                if obj.GetName() == "_PLMXML_Proxies":
                    self._hidden_container = obj
                    break
                obj = obj.GetNext()
            if self._hidden_container is None:
                self._hidden_container = c4d.BaseObject(c4d.Onull)
                self._hidden_container.SetName("_PLMXML_Proxies")
                self._hidden_container[c4d.NULLOBJECT_DISPLAY] = 14
                self._hidden_container[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR] = c4d.MODE_OFF
                self._hidden_container[c4d.ID_BASEOBJECT_VISIBILITY_RENDER] = c4d.MODE_OFF
                doc.InsertObject(self._hidden_container)
        

        return self._hidden_container
    
    def get_cached_geometry(self, jt_path, doc):
        """Get cached geometry for a JT file, or load and cache it"""
        if jt_path in self.geometry_cache:
            self.logger.log(f"✓ Using cached geometry for: {os.path.basename(jt_path)}")
            return self.geometry_cache[jt_path]
        
        # Check if file exists
        if not os.path.exists(jt_path):
            self.logger.log(f"✗ File not found: {jt_path}", "ERROR")
            # Create placeholder
            obj = self._create_placeholder_cube()
            obj.SetName(f"Placeholder_{os.path.basename(jt_path)}")
            self.logger.log(f"🟦 Created placeholder for missing file: {os.path.basename(jt_path)}")
            return obj
        
        # Load geometry from JT file
        temp_doc = c4d.documents.BaseDocument()
        load_success = False
        
        try:
            self.logger.log(f"⏳ Loading JT file: {jt_path}")
            load_success = c4d.documents.MergeDocument(
                temp_doc, 
                jt_path, 
                c4d.SCENEFILTER_OBJECTS  # Geometry only, NO materials
            )
        except Exception as e:
            self.logger.log(f"✗ EXCEPTION during JT load: {str(e)}", "ERROR")
            load_success = False
        
        if not load_success:
            self.logger.log(f"✗ Failed to load JT file: {jt_path}", "ERROR")
            # Create placeholder
            obj = self._create_placeholder_cube()
            obj.SetName(f"Placeholder_{os.path.basename(jt_path)}")
            self.logger.log(f"🟦 Created placeholder for failed load: {os.path.basename(jt_path)}")
            return obj
        
        # Count polygons in loaded geometry
        total_polygons = self._count_polygons_in_document(temp_doc)
        self.logger.log(f"📊 Polygons in {os.path.basename(jt_path)}: {total_polygons:,}")
        
        # Get the first object from temp document (there may be multiple root objects)
        temp_obj = temp_doc.GetFirstObject()
        if temp_obj is None:
            self.logger.log(f"⚠ No geometry found in JT file: {jt_path}", "WARNING")
            obj = self._create_placeholder_cube()
            obj.SetName(f"EmptyPlaceholder_{os.path.basename(jt_path)}")
            return obj
        
        # Clone the object to move it to the main document
        cloned_obj = temp_obj.GetClone(c4d.COPYFLAGS_NONE)
        if cloned_obj is None:
            self.logger.log(f"✗ Failed to clone geometry from: {jt_path}", "ERROR")
            return self._create_placeholder_cube()
        
        # Add to hidden container to keep original geometry
        hidden_container = self.get_or_create_hidden_container(doc)
        cloned_obj.InsertUnder(hidden_container)
        
        # Cache the geometry
        self.geometry_cache[jt_path] = cloned_obj
        
        # Clean up temp document
        temp_doc = None  # Allow garbage collection
        
        self.logger.log(f"✓ Geometry loaded successfully: {os.path.basename(jt_path)}")
        return cloned_obj
    
    def _perform_incremental_save(self, doc):
        """Perform incremental save to prevent data loss during long processing"""
        try:
            # Use Cinema 4D's built-in "Save Incremental" command
            # Command ID: 12098 - Save Incremental
            c4d.CallCommand(12098)
            self.logger.log("💾 Incremental save completed")
            return True
        except Exception as e:
            self.logger.log(f"⚠ Incremental save failed: {str(e)}", "WARNING")
            return False
    
    def _create_placeholder_cube(self, size=10000):
        """Create a cube placeholder for missing JT files"""
        cube = c4d.BaseObject(c4d.Ocube)
        if cube is None:
            return None
        cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(size, size, size)  # Size in Cinema 4D units
        return cube
    
    def _count_polygons_in_document(self, doc):
        """Count total polygons in a document"""
        def count_polygons_recursive(obj):
            count = 0
            if obj.GetType() == c4d.Opolygon:
                count += obj.GetPolygonCount()
            # Recurse through children
            child = obj.GetDown()
            while child:
                count += count_polygons_recursive(child)
                child = child.GetNext()
            return count
        
        total = 0
        obj = doc.GetFirstObject()
        while obj:
            total += count_polygons_recursive(obj)
            obj = obj.GetNext()
        return total
    
    def create_instance(self, original_obj):
        """Create an instance object that references the original geometry"""
        instance = c4d.BaseObject(c4d.Oinstance)
        instance[c4d.INSTANCEOBJECT_LINK] = original_obj
        instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        doc.InsertObject(instance)
        return instance
    
    def _count_polygons_in_object(self, obj):
        """Count polygons in a single object and its children"""
        count = 0
        if obj and obj.GetType() == c4d.Opolygon:
            count += obj.GetPolygonCount()
        
        # Count polygons in children
        child = obj.GetDown()
        while child:
            count += self._count_polygons_in_object(child)
            child = child.GetNext()
        
        return count


class Cinema4DImporter:
    """Hierarchy building and user data management"""
    
    def __init__(self, logger, material_manager, geometry_manager):
        self.logger = logger
        self.material_manager = material_manager
        self.geometry_manager = geometry_manager
        self.total_polygons = 0
        self.total_materials = 0
        self.total_files_processed = 0
        self.files_since_last_save = 0
        self.save_interval = 5  # Save every 5 files
        self.total_jt_files = 0  # Total number of JT files to process
        self.total_rs_files = 0  # Total number of RS files to process (for step 3)
        self.processed_jt_count = 0  # Counter for processed JT files (for progress tracking)
        self.processed_rs_count = 0  # Counter for processed RS files (for progress tracking)
    
    def build_hierarchy(self, plmxml_parser, doc, mode="assembly", plmxml_file_path=None, working_directory=None):        
        # Reset unknown keywords tracking for this import
        MaterialPropertyInference.unknown_keywords.clear()
        
        # Store the PLMXML file path and working directory to help resolve file paths
        self.plmxml_file_path = plmxml_file_path
        self.working_directory = working_directory
        
        # Count total JT files to process based on mode
        self._count_total_files(plmxml_parser, mode)
        
        # Reset progress counters for this import session
        self.processed_jt_count = 0
        self.processed_rs_count = 0
        
        self.logger.log("="*80)
        self.logger.log("🏗️  Starting hierarchy building process")
        self.logger.log(f"📁 Mode: {mode}")
        if mode == "create_redshift_proxies":
            self.logger.log(f"📊 Total JT files to convert to .rs: {self.total_jt_files}")
        elif mode == "compile_redshift_proxies":
            self.logger.log(f"📊 Total .rs files to check: {self.total_rs_files}")
        self.logger.log("="*80)
        
        # Special handling for Steps 1 and 2 - no assembly tree building
        if mode == "material_extraction":
            # Process all JT files directly without building assembly tree for material extraction
            self._process_all_jt_files_for_material_extraction(plmxml_parser, doc)
            return True  # Early return, no need to continue with assembly building
        elif mode == "create_redshift_proxies":
            # Process all JT files directly without building assembly tree
            self._process_all_jt_files_for_proxy_creation(plmxml_parser, doc)
            return True  # Early return, no need to continue with assembly building
        else:
            # Normal assembly building for other modes (compile_redshift_proxies)
            # Get root references for the hierarchy
            root_refs = plmxml_parser.build_hierarchy()
            
            if not root_refs:
                self.logger.log("⚠ No root references found in PLMXML", "WARNING")
                return False
            
            # Create main assembly container
            assembly_root = c4d.BaseObject(c4d.Onull)
            assembly_root.SetName("Assembly")

###            # Set rotation: HPB = Heading, Pitch, Bank
###            assembly_root.SetRelRot(c4d.Vector(-c4d.utils.DegToRad(90), 0, 0))
            doc.InsertObject(assembly_root)

            # Process each root reference
            for root_ref in root_refs:
                if root_ref in plmxml_parser.instances:
                    self._process_instance(
                        plmxml_parser.instances[root_ref], 
                        plmxml_parser, 
                        doc, 
                        assembly_root, 
                        mode
                    )
        
        # Update UI to reflect changes
        c4d.EventAdd()
        
        # Calculate final statistics
        unique_geometries = len(self.geometry_manager.geometry_cache)
        
        # Get total polygons across all loaded geometry
        for cached_geo in self.geometry_manager.geometry_cache.values():
            self.total_polygons += self.geometry_manager._count_polygons_in_object(cached_geo)
        
        # Log final statistics
        self.logger.log("-" * 80)
        self.logger.log(f"📊 Final Statistics:")
        self.logger.log(f"   Files Processed: {self.total_files_processed}")
        self.logger.log(f"   Total Materials: {self.total_materials:,}")
        self.logger.log(f"   Total Polygons: {self.total_polygons:,}")
        self.logger.log(f"   Unique Geometries: {unique_geometries}")
        self.logger.log(f"   Memory saved via instancing: {self._calculate_memory_saved(unique_geometries, self.total_files_processed):.1f}%")
        
        # Report any new material keywords found
        if MaterialPropertyInference.unknown_keywords:
            self.logger.log(f"🔍 New Material Keywords Found: {', '.join(sorted(MaterialPropertyInference.unknown_keywords))}")
        
        self.logger.log("✅ Hierarchy building completed successfully!")
        self.logger.log("-" * 80)
        
        return True
    







    def _process_all_jt_files_for_material_extraction(self, plmxml_parser, doc):
        """Process all JT files directly for material extraction without building assembly tree - Step 1 only"""
        # Since Redshift is built into Cinema 4D 2025, import is always available
        import redshift

        # Iterate through all instances and parts to collect all unique JT files
        processed_jt_files = set()  # Keep track of processed files to avoid duplicates
        
        # Process all instances
        for instance_id, instance_data in plmxml_parser.instances.items():
            part_ref = instance_data['part_ref']
            
            # Skip if part reference is invalid
            if not part_ref or part_ref not in plmxml_parser.parts:
                continue
            
            part_data = plmxml_parser.parts[part_ref]
            
            # Process all JT files for this part
            for jt_data in part_data.get('jt_files', []):
                jt_file = jt_data['file']
                
                # Skip if we've already processed this JT file
                if jt_file in processed_jt_files:
                    continue
                
                processed_jt_files.add(jt_file)
                
                # Get full path to JT file (relative to working directory)
                jt_full_path = os.path.join(self.working_directory, jt_file)
                
                # Get material properties from the JT data
                material_properties = jt_data.get('material_properties', {})
                
                # Process this JT file for material extraction directly
                self._process_material_extraction(jt_full_path, material_properties, doc)
                
                # Update GUI to reflect changes after processing each JT file in Step 1
                c4d.EventAdd()
                c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
                c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

    def _process_all_jt_files_for_proxy_creation(self, plmxml_parser, doc):
        """Process all JT files directly for proxy creation without building assembly tree - Step 2 only"""
        # Iterate through all instances and parts to collect all unique JT files
        processed_jt_files = set()  # Keep track of processed files to avoid duplicates
        
        # Process all instances
        for instance_id, instance_data in plmxml_parser.instances.items():
            part_ref = instance_data['part_ref']
            
            # Skip if part reference is invalid
            if not part_ref or part_ref not in plmxml_parser.parts:
                continue
            
            part_data = plmxml_parser.parts[part_ref]
            
            # Process all JT files for this part
            for jt_data in part_data.get('jt_files', []):
                jt_file = jt_data['file']
                
                # Skip if we've already processed this JT file
                if jt_file in processed_jt_files:
                    continue
                
                processed_jt_files.add(jt_file)
                
                # Get full path to JT file (relative to working directory)
                jt_full_path = os.path.join(self.working_directory, jt_file)
                
                # Get material properties from the JT data
                material_properties = jt_data.get('material_properties', {})
                
                # Process this JT file for proxy creation directly
                self._process_redshift_proxy_creation(jt_full_path, None, material_properties, doc)
                
                # Update GUI to reflect changes after processing each JT file in Step 2
                c4d.EventAdd()
                c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
                c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
    
    def _count_total_files(self, plmxml_parser, mode):
        """Count total files to be processed based on mode"""
        total_jt_count = 0
        total_rs_count = 0
        
        # Get all instances from the parser
        for instance_id, instance_data in plmxml_parser.instances.items():
            part_ref = instance_data['part_ref']
            if part_ref and part_ref in plmxml_parser.parts:
                part_data = plmxml_parser.parts[part_ref]
                # Count jt files for this part
                jt_files_count = len(part_data.get('jt_files', []))
                total_jt_count += jt_files_count
                total_rs_count += jt_files_count  # In mode 3, we check for .rs files for each JT file
                
        self.total_jt_files = total_jt_count
        self.total_rs_files = total_rs_count
        
    def _process_instance(self, instance_data, plmxml_parser, doc, parent_obj, mode):
        """Process a single instance and its hierarchy"""
        part_ref = instance_data['part_ref']
        
        # Skip if part reference is invalid
        if not part_ref or part_ref not in plmxml_parser.parts:
            self.logger.log(f"⚠ Skipping instance with invalid part reference: {part_ref}", "WARNING")
            return
        
        part_data = plmxml_parser.parts[part_ref]
        part_name = part_data['name'] or f"Part_{part_ref}"
        
        # Create a null object for this assembly node and insert under parent
        null_obj = c4d.BaseObject(c4d.Onull)
        null_obj[c4d.NULLOBJECT_DISPLAY] = 14
        null_obj.SetName(part_name)
        null_obj.InsertUnder(parent_obj)
        
        # Process JT files for this part (load geometry, apply materials)
        for jt_data in part_data['jt_files']:
            jt_file = jt_data['file']
            jt_transform = jt_data['transform']
            material_properties = jt_data['material_properties']
            
            # Get full path to JT file (relative to working directory)
            jt_full_path = os.path.join(self.working_directory, jt_file)
            
            # Log the directory where we're searching for JT files
            self.logger.log(f"🔍 Searching for JT file '{jt_file}' in working directory: {self.working_directory}", "INFO")
            
            # Mode-specific processing
            if mode == "material_extraction":
                # Only extract materials, don't load geometry
                self._process_material_extraction(jt_full_path, material_properties, doc)
                
                # Update GUI to reflect changes after processing each JT file in Step 1
                c4d.EventAdd()
                c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
                c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
            elif mode == "create_redshift_proxies":
                # Create redshift proxies
                self._process_redshift_proxy_creation(jt_full_path, null_obj, material_properties, doc)
                
                # Update GUI to reflect changes after processing each JT file in Step 2
                c4d.EventAdd()
                c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
                c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
            elif mode == "compile_redshift_proxies":
                # Add user data
                self._add_user_data(null_obj, instance_data['user_data'])
 
                # identity matrix
                global_matrix = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
                self.logger.log(f"🎨 indentity glob matrix: {global_matrix}")

                # apply instance transformation
                inst_transform = jt_data['transform']
                if inst_transform:
                    self.logger.log(f"🎨 plmxml inst matrix: {inst_transform}")
                    # Perform matrix multiplication
                    result = [0.0] * 16
                    for row in range(4):
                        for col in range(4):
                            sum_val = 0.0
                            for k in range(4):
                                sum_val += global_matrix[row * 4 + k] * inst_transform[k * 4 + col]
                            result[row * 4 + col] = sum_val
                    global_matrix = result        
                    self.logger.log(f"🎨 inst glob matrix: {global_matrix}")

                # apply part transformation
                part_transform = instance_data['transform']
                if part_transform:
                    self.logger.log(f"🎨 plmxml part matrix: {part_transform}")
                    # Perform matrix multiplication
                    result = [0.0] * 16
                    for row in range(4):
                        for col in range(4):
                            sum_val = 0.0
                            for k in range(4):
                                sum_val += global_matrix[row * 4 + k] * part_transform[k * 4 + col]
                            result[row * 4 + col] = sum_val
                    global_matrix = result        
                    self.logger.log(f"🎨 part glob matrix: {global_matrix}")

#                    c4d_transform = self._create_matrix_from_transform(global_matrix, 100.0)
#                    self.logger.log(f"🎨 part_tf       : {c4d_transform}")
#                    null_obj.SetMg(c4d_transform)
#                if jt_transform:
#                    # Apply part transform
#                    part_tf = self._create_matrix_from_transform(part_transform, 100.0)
#                    self.logger.log(f"🎨 part_tf       : {part_tf}")
#                    null_obj.SetMg(part_tf)

                # Compile assembly using existing redshift proxies
                c4d_transform = self._create_matrix_from_transform(global_matrix, 100.0)
                self.logger.log(f"🎨 c4d_transform   : {c4d_transform}")
                self._process_compile_redshift_proxies(jt_full_path, null_obj, material_properties, doc, c4d_transform)
            else:
                self.logger.log(f"🎨 ERROR: Mode not supported, should never happen.")
        
        # Process instance children
        for child_id in instance_data.get('children', []):
            self.logger.log(f"🎨🎨🎨🎨🎨🎨🎨 instantce child **************************")
            if child_id in plmxml_parser.instances:
                self._process_instance(
                    plmxml_parser.instances[child_id], 
                    plmxml_parser, 
                    doc, 
                    null_obj, 
                    mode
                )
    
#        # Process part children
#        for child_id in part_data.get('children', []):
#            self.logger.log(f"🎨🎨🎨🎨🎨🎨🎨 Child **************************")
#            if child_id in plmxml_parser.instances:
#                self._process_instance(
#                    plmxml_parser.instances[child_id], 
#                    plmxml_parser, 
#                    doc, 
#                    null_obj, 
#                    mode
#                )

    def _process_material_extraction(self, jt_path, material_properties, doc):
        """Process material extraction only - no geometry loading"""        
        self.logger.log(f"🎨 Extracting materials from: {os.path.basename(jt_path)}")
        
        # Create material from properties
        if material_properties:
            material = self.material_manager.create_material(material_properties, doc, "material_extraction")
            if material:
                self.total_materials += 1
            else:
                # If material creation failed (due to Redshift unavailability), return early
                self.logger.log(f"❌ Material creation failed, stopping Step 1 execution", "ERROR")
                return
        
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Skip incremental save in material extraction mode, just reset counter
        self.files_since_last_save = 0  # Reset counter to prevent incremental saves during material extraction
        
        # Update GUI to reflect changes after processing each JT file
        c4d.EventAdd()
        c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
    
    def _process_redshift_proxy_creation(self, jt_path, parent_obj_unused, material_properties, doc):
        """Process redshift proxy creation - Step 2: Create proxy files only, no assembly tree building"""
        # Update progress tracking counter
        self.processed_jt_count += 1
        remaining_files = max(0, self.total_jt_files - self.processed_jt_count)
                
        # SCheck first whether the .rs already exists.
        proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
        proxy_path = os.path.join(self.working_directory, proxy_filename)
        proxy_exists = os.path.exists(proxy_path)
        if proxy_exists:
            self.logger.log(f"ℹ Redshift proxy already exists, skipping creation: {proxy_path}")
            self.total_files_processed += 1
            return
        else:
            self.logger.log(f"🎬 Creating redshift proxy for: {os.path.basename(jt_path)} ({self.processed_jt_count}/{self.total_jt_files}, {remaining_files} left)")
        
        # Check if jt file exists
        if not os.path.exists(jt_path):
            self.logger.log(f"✗ JT file not found: {jt_path}", "ERROR")
            return
        
        # Clear any existing objects in the current document while keeping materials
        current_doc = c4d.documents.GetActiveDocument()
        obj = current_doc.GetFirstObject()
        while obj:
            next_obj = obj.GetNext()
            obj.Remove()
            obj = next_obj
#        self.logger.log("⏳ pause after tree deletion to prevent race conditions...")
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        # Light viewport update
#        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

        self.logger.log(f"⏳ Loading JT file into current document: {jt_path}")
        try:
            load_success = c4d.documents.MergeDocument(
                current_doc, 
                jt_path, 
                c4d.SCENEFILTER_OBJECTS  # Geometry only, NO materials
            )
        except Exception as e:
            self.logger.log(f"✗ EXCEPTION during JT load: {str(e)}", "ERROR")
            self.logger.log(f"✗ Failed to load JT file: {jt_path}", "ERROR")
            return

        self.logger.log("⏳ pause after loading JT file to prevent race conditions...")
        doc.FlushUndoBuffer()  # If you don't need undo
        c4d.EventAdd()
        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
        doc.FlushUndoBuffer()  # If you don't need undo
        c4d.EventAdd()
        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
        
        # Count polygons in loaded geometry using the geometry manager
        total_polygons = self.geometry_manager._count_polygons_in_document(current_doc)
        self.logger.log(f"📊 Polygons in {os.path.basename(jt_path)}: {total_polygons:,}")
        
        # Get the geometry from the current document - handle multiple objects if present
        current_doc_obj = current_doc.GetFirstObject()
        if current_doc_obj is None:
            self.logger.log(f"⚠ No geometry found in JT file: {jt_path}", "WARNING")
            return
        
        # Handle multiple root objects by getting them from the current document
        root_objects = []
        obj_iter = current_doc.GetFirstObject()
        while obj_iter:
            root_objects.append(obj_iter)
            obj_iter = obj_iter.GetNext()
        
        # Check for a child node of root objects named "AUS_FINAL_PART" or "OUT_FINAL_PART" and keep only that geometry mesh node if it exists
        aus_final_part_node = None
        parent_node = None
        
        # Search through root objects and their children for "AUS_FINAL_PART" or 
        for root_obj in root_objects:
#            # First check if the root object itself is named "AUS_FINAL_PART"
#            if root_obj.GetName() == "AUS_FINAL_PART" and root_obj.GetType() == c4d.Opolygon:
#                aus_final_part_node = root_obj
#                parent_node = None  # This is already a root node
#                break
            
            # Then check children of each root object
            child = root_obj.GetDown()
            while child:
                if child.GetName() == "AUS_FINAL_PART" or child.GetName() ==  "OUT_FINAL_PART":
                    aus_final_part_node = child
                    parent_node = root_obj
                    break
                child = child.GetNext()
            
            if aus_final_part_node:
                break
        
        # If AUS_FINAL_PART | "OUT_FINAL_PART" node exists as a child, delete all other child nodes from its parent
        if aus_final_part_node is not None:
            self.logger.log(f"🔍 Found AUS_FINAL_PART | OUT_FINAL_PART node: {aus_final_part_node.GetName()}")
            
            if parent_node is not None:
                self.logger.log(f"📁 AUS_FINAL_PART | OUT_FINAL_PART found as child of: {parent_node.GetName()}")
                
                # Get all children of the parent to remove
                child_to_keep = aus_final_part_node
                child = parent_node.GetDown()
                children_to_remove = []
                
                while child:
                    if child != child_to_keep:
                        children_to_remove.append(child)
                    child = child.GetNext()
                
                # Remove all other children
                for child_to_remove in children_to_remove:
                    child_to_remove.Remove()
                
                # Update root_objects to contain only the parent with just the AUS_FINAL_PART child
                # Move the AUS_FINAL_PART node to root level and remove its parent if it had no other children originally
                # Actually, let's just make the AUS_FINAL_PART node a root node by moving it up
                aus_final_part_node.Remove()  # Remove from parent
                current_doc.InsertObject(aus_final_part_node)  # Insert as root object
                
                # Now remove the original parent if it has no other children
                if parent_node.GetDown() is None:
                    parent_node.Remove()
                
                # Update root_objects to contain only the AUS_FINAL_PART node
                root_objects = [aus_final_part_node]
                self.logger.log(f"✅ Kept only AUS_FINAL_PART node, removed {len(children_to_remove)} other child objects")
            else:
                # AUS_FINAL_PART was already a root node
                # Remove all other root objects except the AUS_FINAL_PART node
                obj_to_keep = aus_final_part_node
                obj = current_doc.GetFirstObject()
                objects_to_remove = []
                
                while obj:
                    if obj != obj_to_keep:
                        objects_to_remove.append(obj)
                    obj = obj.GetNext()
                
                # Remove all other root objects
                for obj_to_remove in objects_to_remove:
                    obj_to_remove.Remove()
                
                # Update root_objects to contain only the AUS_FINAL_PART node
                root_objects = [obj_to_keep]
                self.logger.log(f"✅ Kept only AUS_FINAL_PART node (was already a root), removed {len(objects_to_remove)} other root objects")
        else:
            self.logger.log(f"⚠ AUS_FINAL_PART node not found as root or child, keeping all {len(root_objects)} root objects")

#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        # Light viewport update
#        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

        # Process materials: replace with materials from the PLMXML file specification
        if material_properties and len(root_objects) > 0:
            for obj in root_objects:
                self._replace_materials_with_closest_match(obj, material_properties, doc, "create_redshift_proxies")
        
#        self.logger.log("⏳ pause after replace with materials from the PLMXML file specification to prevent race conditions...")
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        # Light viewport update
#        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

        # Use only the known working format ID 1038650 for Redshift proxy export
        format_id = 1038650
        try:
            if c4d.documents.SaveDocument(current_doc, proxy_path, c4d.SAVEDOCUMENTFLAGS_0, format_id):
                self.logger.log(f"✓ Redshift proxy processing completed for: {os.path.basename(proxy_path)}")
            else:
                self.logger.log(f"✗ Redshift proxy export failed with format {format_id}", "ERROR")
        except Exception as e:
            self.logger.log(f"✗ Redshift proxy export failed with format {format_id}, Exception {str(e)}", "ERROR")

#        self.logger.log("⏳ pause at end of redshift proxy generation  to prevent race conditions...")
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
#        # Light viewport update
#        c4d.DrawViews(c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW | c4d.DRAWFLAGS_NO_THREAD)
#        doc.FlushUndoBuffer()  # If you don't need undo
#        c4d.EventAdd()
#        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)

        self.total_files_processed += 1
        
 #       # Update GUI to reflect changes after processing each JT file in Step 2
 #       c4d.EventAdd()
 #       c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
 #       c4d.GeSyncMessage(c4d.EVMSG_CHANGE)
            
    def _replace_materials_with_closest_match(self, obj, material_properties, doc, mode="assembly"):
        """Replace materials in the loaded JT geometry with existing materials from the document that match the PLMXML specification"""
        # Generate the material name that would have been created in Step 1
        reference_material_name = self.material_manager._generate_material_name(material_properties)
        
        # Find the existing material in the document that matches this name
        existing_material = doc.GetFirstMaterial()
        target_material = None
        while existing_material:
            if existing_material.GetName() == reference_material_name:
                target_material = existing_material
                self.logger.log(f"🎯 Found existing material to reuse: {reference_material_name}")
                break
            existing_material = existing_material.GetNext()
        
        # If we don't find an exact match, look for similar materials based on properties
        if target_material is None:
            self.logger.log(f"⚠️ No exact material match found for: {reference_material_name}. Searching for similar materials...")
            target_material = self._find_similar_material_in_document(material_properties, doc)
        
        # If still no match found, we have to create it (though this shouldn't happen in Step 2)
        if target_material is None:
            self.logger.log(f"⚠️ No matching material found in document for: {reference_material_name}. This might indicate Step 1 was not run first.", "WARNING")
            # As a fallback, we'll create a material, but this is not ideal for Step 2
            target_material = self.material_manager.create_material(material_properties, doc, mode)
            if target_material:
                self.logger.log(f"⚠️ Created fallback material: {target_material.GetName()}")
            else:
                self.logger.log("⚠️ Failed to create fallback material", "WARNING")
                return
        
        if target_material:
            # Replace all materials in the object hierarchy with the found material
            self._replace_materials_in_hierarchy(obj, target_material, obj.GetDocument())
    
    def _find_similar_material_in_document(self, material_properties, doc):
        """Find a similar material in the document based on material properties"""
        # Generate the expected material name
        expected_name = self.material_manager._generate_material_name(material_properties)
        
        # First, try to find a material that was created from the same material properties
        mat = doc.GetFirstMaterial()
        while mat:
            # Check if the material name starts with the expected pattern or is closely related
            mat_name = mat.GetName()
            if expected_name in mat_name or mat_name in expected_name:
                # Check if the material properties are similar
                if self._material_matches_properties(mat, material_properties):
                    self.logger.log(f"🎯 Found similar material: {mat_name}")
                    return mat
            mat = mat.GetNext()
        
        return None  # No similar material found

    def _setup_rs_proxy_file_path(self, proxy_obj, proxy_filename_only):
        """Simplified version focusing on the most common parameter IDs"""
        
        if not proxy_obj or not proxy_filename_only:
            return False
        
        # The most common parameter ID for RS Proxy file path is 2001
        PRIMARY_FILE_PARAM_ID = 2001
        
        try:
            proxy_obj[PRIMARY_FILE_PARAM_ID] = proxy_filename_only
            c4d.EventAdd()
            return True
        except:
            # If primary ID fails, try a few alternatives
            alternative_ids = [2000, 1000, 1001]
            
            for param_id in alternative_ids:
                try:
                    proxy_obj[param_id] = proxy_filename_only
                    c4d.EventAdd()
                    return True
                except:
                    continue
        
        # If all fails, report the issue
        print(f"Warning: Could not set RS Proxy file path for '{proxy_filename_only}'")
        print(f"  Object type: {proxy_obj.GetType()}")
        print(f"  Object name: {proxy_obj.GetName()}")
        
        # Still return True to not break the import process
        # The user can manually set the file path later
        return True
    
    def _material_matches_properties(self, material, material_properties):
        """Check if a material matches the given material properties"""
        # For Step 2, we primarily match by name pattern since the properties might not be directly accessible
        # This is a simplified check - a more sophisticated implementation would compare actual properties
        expected_name = self.material_manager._generate_material_name(material_properties)
        actual_name = material.GetName()
        
        # Check if names match (considering potential C4D name variations like .1, .2, etc.)
        if actual_name == expected_name:
            return True
            
        # Check for truncated names (e.g., "Material" when looking for "Material.123")
        if (actual_name.startswith(expected_name) and 
            len(actual_name) > len(expected_name) and
            actual_name[len(expected_name):].startswith('.')):
            return True
            
        # Check for the reverse case
        if (expected_name.startswith(actual_name) and 
            len(expected_name) > len(actual_name) and
            expected_name[len(actual_name):].startswith('.')):
            return True
            
        return False
        
    def _replace_materials_in_hierarchy(self, obj, reference_material, doc):
        """Replace materials in the object hierarchy with the reference material"""
        if obj is None:
            return
            
        # Process all texture tags on this object
        tag = obj.GetFirstTag()
        texture_tags_to_remove = []
        
        # Collect all texture tags first
        while tag:
            if tag.GetType() == c4d.Ttexture:  # Texture tag
                texture_tags_to_remove.append(tag)
            tag = tag.GetNext()
        
        # Remove all texture tags and replace with the reference material
        for tag in texture_tags_to_remove:
            # Get the old material to potentially delete it if not used elsewhere
            old_material = tag[c4d.TEXTURETAG_MATERIAL]
            
            # Remove the old tag
            tag.Remove()
            
            # Create a new texture tag with the reference material
            new_tag = c4d.BaseTag(c4d.Ttexture)
            if new_tag:
                new_tag[c4d.TEXTURETAG_MATERIAL] = reference_material
                new_tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
                new_tag[c4d.TEXTURETAG_TILE] = True
                obj.InsertTag(new_tag)
                
                self.logger.log(f"  → Replaced material on object: {obj.GetName()}")
        
        # Process children recursively
        child = obj.GetDown()
        while child:
            self._replace_materials_in_hierarchy(child, reference_material, doc)
            child = child.GetNext()
    
    def _calculate_material_distance(self, existing_mat, material_properties):
        """Calculate the similarity distance between an existing material and requested properties"""
        # Extract properties from the existing material
        existing_base_color = existing_mat[c4d.MATERIAL_COLOR_COLOR]
        existing_roughness = 0.0  # Would need to get from reflection layer
        
        # Get properties from material data
        inferred_props = MaterialPropertyInference.infer_material_properties(material_properties)
        
        # Calculate color distance
        target_color = inferred_props['base_color']
        color_distance = abs(existing_base_color.x - target_color.x) + \
                        abs(existing_base_color.y - target_color.y) + \
                        abs(existing_base_color.z - target_color.z)
        
        # Calculate roughness distance
        target_roughness = inferred_props['roughness']
        # For now, assume roughness is 0 if we can't extract it from existing material
        roughness_distance = abs(existing_roughness - target_roughness)
        
        # Combine distances (weight more heavily on color)
        total_distance = color_distance * 0.7 + roughness_distance * 0.3
        
        return total_distance
    
    def _apply_material_to_object_with_new_material(self, obj, mat):
        """Apply a material to an object using a texture tag"""
        # Create texture tag
        tag = c4d.BaseTag(c4d.Ttexture)
        if tag is None:
            return
            
        # Set the material
        tag[c4d.TEXTURETAG_MATERIAL] = mat
        tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
        tag[c4d.TEXTURETAG_TILE] = True
        
        # Insert tag on the object
        obj.InsertTag(tag)
    
    def _process_compile_redshift_proxies(self, jt_path, parent_obj, material_properties, doc, jt_transform=None):
        """Process compile redshift proxies mode - creates assembly with proxy references"""
        # Update progress tracking counter
        self.processed_rs_count += 1
        remaining_files = max(0, self.total_rs_files - self.processed_rs_count)
        self.logger.log(f"🔗 Compiling redshift proxy assembly for: {os.path.basename(jt_path)} ({self.processed_rs_count}/{self.total_rs_files}, {remaining_files} left)")
        
        # Get the hidden container for proxy objects (_PLMXML_Proxies)
        hidden_container = self.geometry_manager.get_or_create_hidden_container(doc)
        self.logger.log(f"📁 Using hidden container: {hidden_container.GetName() if hidden_container else 'None'}")
        
        jt_name = os.path.splitext(os.path.basename(jt_path))[0]

        # check if null object already exists
        jt_null_obj = None
        child = hidden_container.GetDown()  # Get the first child
        while child:
            if child.GetName() == jt_name:  # Replace with your target child name
                print(F"Found child {jt_name}, reuse rs proxy ***************")
                jt_null_obj = child
                break  # Stop once found
            child = child.GetNext()  # Move to the next sibling
        else:
            print("FChild named {jt_name} not found, Create a null object with the same name as the JT file directly under _PLMXML_Proxies")

        # if null object doesn't exist, create it
        if jt_null_obj == None:
            # Create a null object with the same name as the JT file directly under _PLMXML_Proxies
            jt_null_obj = c4d.BaseObject(c4d.Onull)
            jt_null_obj.SetName(jt_name)
            jt_null_obj[c4d.NULLOBJECT_DISPLAY] = 14
            doc.InsertObject(jt_null_obj)  # Insert into document first
            jt_null_obj.InsertUnder(hidden_container)  # Then under the hidden container
            self.logger.log(f"📁 Created null object: {jt_null_obj.GetName()} under {hidden_container.GetName() if hidden_container else 'None'}")
            
            # Check if proxy file exists
            # Use the working directory, not the document directory or JT path directory
            proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
            proxy_path = os.path.join(self.working_directory, proxy_filename)
            
            proxy_exists = os.path.exists(proxy_path)
            self.logger.log(f"📁 Checking for proxy: {proxy_path} (exists: {proxy_exists})")
            
            # Create proxy object (or placeholder if proxy doesn't exist) as a child of the JT null object
            if proxy_exists:
                # Create a new Redshift Proxy object
                proxy_obj = c4d.BaseObject(1038649) # Redshift proxy plugin ID: com.redshift3d.redshift4c4d.proxyloader
                # Set the proxy file path (just the filename, not full path, as per requirements)
                proxy_filename_only = os.path.basename(proxy_path)
                proxy_obj.SetName(proxy_filename_only)
                doc.InsertObject(proxy_obj)

                # Add User Data property "ProxyName" directly to the object
                bc = c4d.GetCustomDatatypeDefault(c4d.DTYPE_STRING)
                bc[c4d.DESC_NAME] = "ProxyName"
                bc[c4d.DESC_SHORT_NAME] = "ProxyName"
                bc[c4d.DESC_DEFAULT] = proxy_filename_only

                user_data_id = proxy_obj.AddUserData(bc)

                # Set the ProxyName value
                proxy_obj[user_data_id] = proxy_filename_only

                # Create XPresso Tag
                xpresso_tag = c4d.BaseTag(c4d.Texpresso)
                proxy_obj.InsertTag(xpresso_tag)
                xpresso_tag.SetName("XPresso")

                # Get the XPresso node master
                node_master = xpresso_tag.GetNodeMaster()

                # Create Object node for the Redshift Proxy
                proxy_node = node_master.CreateNode(node_master.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=100, y=100)
                proxy_node[c4d.GV_OBJECT_OBJECT_ID] = proxy_obj

                # Create Object node for User Data access
                userdata_node = node_master.CreateNode(node_master.GetRoot(), c4d.ID_OPERATOR_OBJECT, None, x=100, y=250)
                userdata_node[c4d.GV_OBJECT_OBJECT_ID] = proxy_obj

                # Add output port for ProxyName from user data node
                userdata_output = userdata_node.AddPort(c4d.GV_PORT_OUTPUT, user_data_id)

                # Create the DescID for the File parameter
                file_desc_id = c4d.DescID(c4d.DescLevel(10000, 1036765, 1038649))

                # Add input port for File parameter on Redshift Proxy node
                proxy_input = proxy_node.AddPort(c4d.GV_PORT_INPUT, file_desc_id)

                if proxy_input is None:
                    gui.MessageDialog("Could not create port for File parameter.")

                # Connect the ports
                userdata_output.Connect(proxy_input)
                print(f"Successfully created Redshift Proxy for: {proxy_filename}")
                
                # move node under the JT null object
                proxy_obj.InsertUnder(jt_null_obj)  
                proxy_obj[c4d.REDSHIFT_PROXY_DISPLAY_BOUNDBOX] = False
                proxy_obj[c4d.REDSHIFT_PROXY_DISPLAY_MODE] = 2
                self.logger.log(f"✅ Redshift proxy object created: {proxy_filename}")
            else:
                # Proxy file doesn't exist, create placeholder cube as child of JT null object
                proxy_obj = self.geometry_manager._create_placeholder_cube(500.0)  # 5m cube (500cm in Cinema 4D units)
                proxy_obj.SetName("Placeholder_Cube")
                doc.InsertObject(proxy_obj)  # Insert into document first
                proxy_obj.InsertUnder(jt_null_obj)  # Then under the JT null object
                proxy_obj[c4d.ID_BASEOBJECT_GENERATOR_FLAG] = False
                self.logger.log(f"🟦 Created placeholder cube for missing proxy file on disk: {proxy_filename}")
        
        # Create an instance of the JT null object to maintain transforms in the visible hierarchy
        if jt_null_obj:
            instance_obj = self.create_instance(jt_null_obj)
            if instance_obj:
                instance_obj.SetName(jt_name + "_Instance")
                # Insert instance under the parent to maintain assembly structure
                instance_obj.InsertUnder(parent_obj)
                
                # Apply JT transform to the instance if provided
                if jt_transform:
                    instance_obj.SetMl(jt_transform)
                
                self.logger.log(f"✓ Proxy instance added to assembly: {instance_obj.GetName()}")
        
        self.total_files_processed += 1
        self.files_since_last_save += 1
            
    def _create_matrix_from_transform(self, transform_matrix, scale_factor=100.0):
        """Convert 16-value row-major matrix from CAD Z-up in meters to Cinema 4D Y-up in centimeters with Z-axis inversion"""
        if len(transform_matrix) != 16:
            return c4d.Matrix()  # Return identity matrix if invalid
                
        # For coordinate system conversion from CAD Z-up to C4D Y-up:
        # First apply -90 degree rotation around the X-axis: (x,y,z) -> (x,-z,y)
        # Then invert the Z-axis: (x,-z,y) -> (x,-z,-y)
        # This is represented by the combined transformation matrix: 
        # |1  0  0   0|
        # |0  0  1   0| 
        # |0 -1  0   0|
        # |0  0  0  -1|
        
        # Extract the original 4x4 matrix from the 16-value row-major array
        # [ 0  1  2  3 ]
        # [ 4  5  6  7 ]
        # [ 8  9  10 11]
        # [ 12 13 14 15]
        m00, m01, m02, m03 = transform_matrix[0], transform_matrix[1], transform_matrix[2], transform_matrix[3]
        m10, m11, m12, m13 = transform_matrix[4], transform_matrix[5], transform_matrix[6], transform_matrix[7]
        m20, m21, m22, m23 = transform_matrix[8], transform_matrix[9], transform_matrix[10], transform_matrix[11]
        tx, ty, tz = transform_matrix[12], transform_matrix[13], transform_matrix[14]
        
        # Apply the coordinate system transformation: 
        # Convert from CAD coordinate system (Z-up) to C4D coordinate system (Y-up) with Z-axis inversion
        # This requires transforming the matrix to account for the coordinate frame change
        # For a coordinate system transformation, the resulting matrix is:
        # T * M * inverse(T), where T is the coordinate transformation
        #
        # But for this simple case where we're just converting the coordinate interpretation,
        # we can directly compute the transformed matrix components:
        
        # First transformation: -90° rotation around X-axis, followed by Z-axis inversion
        # To convert a matrix M from coordinate system A to B, 
        # we use T * M * T^(-1), where T converts from A to B coordinates
        # Since T is orthogonal (rotation), T^(-1) = T^T (transpose)
        
        # For the combined transformation: (x,y,z) -> (x,-z,-y), the 3x3 rotation matrix is:
        # [1  0  0]
        # [0  0 -1]
        # [0 -1  0]
        
        # Apply transformation: result = T * M
        # Where T is the coordinate transformation matrix
        # T * M (first three rows only):
        # [1  0  0  0] [m00 m01 m02 m03]   [m00 m01 m02 m03]
        # [0  0 -1  0] [m10 m11 m12 m13] = [-m20 -m21 -m22 -m23]
        # [0 -1  0  0] [m20 m21 m22 m23]   [-m10 -m11 -m12 -m13]
        # [0  0  0  1] [tx  ty  tz  1 ]    [tx   ty   tz   1  ]
        
        # So the resulting matrix has:
        # New X axis: (m00, -m20, -m10)
        # New Y axis: (m01, -m21, -m11) 
        # New Z axis: (m02, -m22, -m12)
        # New translation: (tx, -tz, -ty)
        
        m = c4d.Matrix()
#        m.v1 = c4d.Vector(m00, -m20, -m10)  # New X-axis (rotation part with Z inversion)
#        m.v2 = c4d.Vector(m01, -m21, -m11)  # New Y-axis (rotation part with Z inversion)
#        m.v3 = c4d.Vector(m02, -m22, -m12)  # New Z-axis (rotation part with Z inversion)
        m.v1 = c4d.Vector(m00, m10, m20)  # New X-axis (rotation part with Z inversion)
        m.v2 = c4d.Vector(m01, m11, m21)  # New Y-axis (rotation part with Z inversion)
        m.v3 = c4d.Vector(m02, m12, m22)  # New Z-axis (rotation part with Z inversion)
        # Apply unit conversion to translation (meters to cm) and Z inversion
        m.off = c4d.Vector(tx * scale_factor, tz * scale_factor, ty * scale_factor)
        
        return m
    
    def _calculate_memory_saved(self, unique_geometries, total_files):
        """Calculate percentage of memory saved through instancing"""
        if total_files <= 0 or unique_geometries == 0:
            return 0.0
        if total_files <= unique_geometries:
            return 0.0  # No instancing happening
        
        # Calculate memory savings: (total_files - unique_geometries) / total_files * 100
        memory_saved = ((total_files - unique_geometries) / total_files) * 100
        return max(0.0, memory_saved)  # Ensure non-negative result
    
    def _add_user_data(self, obj, user_data):
        """Add user data to an object"""
        if not user_data:
            return
            
        # Add each user value as a string user data
        for key, value in user_data.items():
            # Create a container for the user data parameter
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
            if bc is None:
                continue
                
            bc[c4d.DESC_NAME] = key
            bc[c4d.DESC_SHORT_NAME] = key
            bc[c4d.DESC_ANIMATE] = 0  # Turn off animation for user data
            bc[c4d.DESC_SHADERLINKFLAG] = False
            
            # Add the user data to the object
            id = obj.AddUserData(bc)
            if id:
                obj[id] = str(value)
    
    def _apply_material_to_geometry(self, obj, material, doc):
        """Apply material to geometry objects (not null containers)"""
        # For now, just apply to the instance object if it doesn't have other children
        # In a full implementation, you'd recursively find all geometry objects
        
        # Create texture tag
        tag = c4d.BaseTag(c4d.Ttexture)
        if tag is None:
            return
            
        # Set the material
        tag[c4d.TEXTURETAG_MATERIAL] = material
        tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
        tag[c4d.TEXTURETAG_TILE] = True
        
        # Insert tag on the object
        obj.InsertTag(tag)


class PLMXMLDialog(gui.GeDialog):
    """Dialog for the PLMXML Importer plugin"""
    
    # Dialog element IDs
    IDC_FILEPATH = 1000
    IDC_BROWSE_BUTTON = 1001
    IDC_MODE_GROUP = 1002
    IDC_MODE_MATERIAL = 1003
    IDC_MODE_PROXY = 1004
    IDC_MODE_COMPILE = 1005
    IDC_MODE_ASSEMBLY = 1006  # Changed from IDC_IMPORT_BUTTON to IDC_MODE_ASSEMBLY
    IDC_CANCEL_BUTTON = 1007  # Use standard ID for cancel
    
    def __init__(self):
        super().__init__()
        self.plmxml_path = ""
        self.selected_mode = 0  # 0: Step 1 Extract materials, 1: Step 2 Create Redshift Proxies, 2: Step 3 Build assembly
        # Initialize the working directory to the C4D file's directory
        doc = c4d.documents.GetActiveDocument()
        c4d_file_path = doc.GetDocumentPath()
        if c4d_file_path and os.path.exists(c4d_file_path):
            # Check if c4d_file_path is a file or directory
            if os.path.isfile(c4d_file_path):
                # If it's a file, use its parent directory
                self.working_directory = os.path.dirname(c4d_file_path)
            elif os.path.isdir(c4d_file_path):
                # If it's already a directory, use it directly
                self.working_directory = c4d_file_path
            else:
                # Fallback case
                self.working_directory = ""
        else:
            self.working_directory = ""
        
        # Initialize logger for the dialog
        # Set up a default log path in the working directory or temp directory
        import tempfile
        if self.working_directory:
            default_log_path = os.path.join(self.working_directory, "debug_dialog_log.txt")
        else:
            default_log_path = os.path.join(tempfile.gettempdir(), f"plmxml_debug_{os.getpid()}.txt")
        
        self.logger = Logger(default_log_path)
        
        self.logger.log(f"🔧 Dialog initialized - C4D file path: {c4d_file_path}", "INFO")
        print(f"🔧 Dialog initialized - C4D file path: {c4d_file_path}")
        self.logger.log(f"📂 Working directory set to: {self.working_directory}", "INFO")
        print(f"📂 Working directory set to: {self.working_directory}")
        
        if not c4d_file_path or not os.path.exists(c4d_file_path):
            self.logger.log(f"⚠️ C4D document not saved - no file path available", "WARNING")
            print(f"⚠️ C4D document not saved - no file path available")
    
    def CreateLayout(self):
        """Create the dialog layout"""
        self.SetTitle("PLMXML Assembly Importer")
        
        # Mode selection - Radio buttons
        self.GroupBegin(self.IDC_MODE_GROUP, c4d.BFH_LEFT, cols=1, rows=3)
        self.AddRadioText(self.IDC_MODE_MATERIAL, c4d.BFH_LEFT, 300, 20, "Step 1: Extract materials")
        self.AddRadioText(self.IDC_MODE_PROXY, c4d.BFH_LEFT, 300, 20, "Step 2: Create Redshift Proxies")
        self.AddRadioText(self.IDC_MODE_COMPILE, c4d.BFH_LEFT, 300, 20, "Step 3: Build assembly")
        self.GroupEnd()
        
        # Select first mode by default (Material Extraction) and set selected_mode accordingly
        # Set all radio buttons to proper initial state
        self.SetBool(self.IDC_MODE_MATERIAL, True)
        self.SetBool(self.IDC_MODE_PROXY, False)
        self.SetBool(self.IDC_MODE_COMPILE, False)
        self.selected_mode = 0
        
        # Buttons - Swapped OK and Cancel positions
        self.GroupBegin(0, c4d.BFH_CENTER, cols=2)
        self.AddButton(c4d.DLG_CANCEL, c4d.BFH_LEFT, name="Cancel")
        self.AddButton(c4d.DLG_OK, c4d.BFH_RIGHT, name="OK")
        self.GroupEnd()
        
        return True
    
    def Command(self, id, msg):
        """Handle dialog commands"""
        # Removed the browse button handling since we auto-detect PLMXML file
        if id == self.IDC_BROWSE_BUTTON:
            # Browse button is no longer part of the UI
            pass
        
        elif id == self.IDC_MODE_MATERIAL:
            self.selected_mode = 0
            self.SetBool(self.IDC_MODE_MATERIAL, True)
            self.SetBool(self.IDC_MODE_PROXY, False)
            self.SetBool(self.IDC_MODE_COMPILE, False)
        
        elif id == self.IDC_MODE_PROXY:
            self.selected_mode = 1
            self.SetBool(self.IDC_MODE_MATERIAL, False)
            self.SetBool(self.IDC_MODE_PROXY, True)
            self.SetBool(self.IDC_MODE_COMPILE, False)
        
        elif id == self.IDC_MODE_COMPILE:
            self.selected_mode = 2
            self.SetBool(self.IDC_MODE_MATERIAL, False)
            self.SetBool(self.IDC_MODE_PROXY, False)
            self.SetBool(self.IDC_MODE_COMPILE, True)
        
        elif id == c4d.DLG_OK:
            # Log detailed info before looking for PLMXML file
            doc = c4d.documents.GetActiveDocument()
            c4d_file_path = doc.GetDocumentPath()
            
            self.logger.log(f"🎬 Cinema 4D file path: {c4d_file_path}", "INFO")
            self.logger.log(f"📂 Working directory for search: {self.working_directory}", "INFO")
            
            # Verify that the working directory exists
            if not self.working_directory or not os.path.exists(self.working_directory):
                self.logger.log(f"❌ Working directory does not exist: {self.working_directory}", "ERROR")
                c4d.gui.MessageDialog("Please save your Cinema 4D file first.")
                return True
            
            # Log directory contents for debugging
            try:
                dir_contents = os.listdir(self.working_directory)
                self.logger.log(f"📁 Contents of working directory ({self.working_directory}): {dir_contents}", "INFO")
                
                # Look for .plmxml files in the working directory
                plmxml_files = [f for f in dir_contents if f.lower().endswith('.plmxml') and os.path.isfile(os.path.join(self.working_directory, f))]
                
                self.logger.log(f"🔍 Found PLMXML files: {plmxml_files}", "INFO")
            except Exception as e:
                self.logger.log(f"❌ Error accessing working directory {self.working_directory}: {str(e)}", "ERROR")
                c4d.gui.MessageDialog(f"Error accessing directory: {str(e)}")
                return True
            
            if not plmxml_files:
                self.logger.log(f"❌ No .plmxml files found in working directory: {self.working_directory}", "ERROR")
                # List all .plmxml files in the directory (case-insensitive)
                try:
                    all_files = [f for f in os.listdir(self.working_directory) if f.lower().endswith('.plmxml')]
                    if all_files:
                        self.logger.log(f"💡 Found files with .plmxml extension (possibly case-sensitive): {all_files}", "WARNING")
                except:
                    pass  # Don't let this error break the process
                
                c4d.gui.MessageDialog(f"No .plmxml files found in the working directory: {self.working_directory}")
                return True
            
            # If there are multiple .plmxml files, just take the first one
            # In a real implementation, you might want to show a selection dialog
            self.plmxml_path = os.path.join(self.working_directory, plmxml_files[0])
            self.logger.log(f"✅ PLMXML file selected: {self.plmxml_path}", "INFO")
            
            # For long-running import processes, use a MessageData plugin approach or ensure proper main thread execution
            # This ensures that all document modifications happen in the main thread
            c4d.CallCommand(12098)  # Force save before import
            
            # Run the import process directly in the main thread to ensure all operations are GUI-safe
            # Close the dialog first
            self.Close()
            
            # Execute the import process
            self._run_import_process()
            
            return True
        
        elif id == c4d.DLG_CANCEL:
            self.Close()
        
        return True
    
    def _run_import_process(self):
        """Run the import process based on selected mode"""
        # Get the current document
        doc = c4d.documents.GetActiveDocument()
        
        # Log the Cinema 4D document path
        c4d_document_path = doc.GetDocumentPath()
        self.logger.log(f"🎬 Cinema 4D document path: {c4d_document_path}", "INFO") if hasattr(self, 'logger') else None
        
        # Set up logging with requested format: importPlmxml_{Step}_log.txt
        mode_steps = ["1", "2", "3"]  # Material extraction, Create redshift proxies, Compile redshift proxies
        mode_step = mode_steps[self.selected_mode] if 0 <= self.selected_mode < len(mode_steps) else "1"
        log_filename = f"importPlmxml_{mode_step}_log.txt"
        log_path = os.path.join(self.working_directory, log_filename)
        logger = Logger(log_path)
        
        # Log the start of the process to the console as well
        print(f"🚀 Starting import process for: {os.path.basename(self.plmxml_path)}")
        print(f"📁 Using log file: {log_filename}")
        logger.log(f"🚀 Starting import process for: {os.path.basename(self.plmxml_path)}", "INFO")
        logger.log(f"📁 Using log file: {log_filename}", "INFO")
        logger.log(f"🎬 Cinema 4D document path: {c4d_document_path}", "INFO")        
        logger.log(f"🔧 Selected mode: {self.selected_mode}", "INFO")
        
        try:
            if self.selected_mode == 0:
                step1_collect_materials(logger, doc, self.working_directory, self.plmxml_path)
            elif self.selected_mode == 2:
                step3_build_assembly(logger, doc, self.working_directory, self.plmxml_path)
            else:
                # Initialize components
                plmxml_parser = PLMXMLParser(logger)
                material_manager = Cinema4DMaterialManager(logger)
                geometry_manager = GeometryInstanceManager(logger)
                importer = Cinema4DImporter(logger, material_manager, geometry_manager)
                
                # Map mode to string and create proper log file name
                mode_names = ["material_extraction", "create_redshift_proxies", "compile_redshift_proxies"]
                mode_steps = ["1", "2", "3"]  # Corresponding step numbers
                mode_name = mode_names[self.selected_mode] if 0 <= self.selected_mode < len(mode_names) else "material_extraction"
                mode_step = mode_steps[self.selected_mode] if 0 <= self.selected_mode < len(mode_steps) else "1"
                
                logger.log(f"🚀 Starting import process in mode: {mode_name}")
                
                # Parse the PLMXML file
                if not os.path.exists(self.plmxml_path):
                    logger.log(f"✗ PLMXML file does not exist: {self.plmxml_path}", "ERROR")
                    self.logger.log(f"❌ PLMXML file does not exist: {self.plmxml_path}", "ERROR")  # Also log to dialog logger
                    logger.close()
                    c4d.gui.MessageDialog(f"PLMXML file not found: {self.plmxml_path}")
                    return
                    
                if not plmxml_parser.parse_plmxml(self.plmxml_path):
                    logger.log("✗ PLMXML parsing failed", "ERROR")
                    logger.close()
                    c4d.gui.MessageDialog("PLMXML parsing failed. Check the log file for details.")
                    return
                
                # Build hierarchy based on selected mode
                success = importer.build_hierarchy(plmxml_parser, doc, mode_name, self.plmxml_path, self.working_directory)
                
                if success:
                    logger.log(f"🎉 Import completed successfully using mode: {mode_name}")
                    c4d.gui.MessageDialog(f"Import completed successfully using mode: {mode_name}\nLog saved to: {log_path}")
                else:
                    logger.log(f"✗ Import failed with mode: {mode_name}", "ERROR")
                    c4d.gui.MessageDialog(f"Import failed with mode: {mode_name}\nCheck log for details: {log_path}")
            
        except Exception as e:
            logger.log(f"✗ Import process failed: {str(e)}", "ERROR")
            logger.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            c4d.gui.MessageDialog(f"Import process failed: {str(e)}\nCheck log for details: {log_path}")
        finally:
            logger.close()

        # Refresh the Cinema 4D interface to show new materials
        c4d.EventAdd()
        c4d.DrawViews(c4d.DRAWFLAGS_FORCEFULLREDRAW)
        c4d.GeSyncMessage(c4d.EVMSG_CHANGE)


class PLMXMLImporter(plugins.CommandData):
    """Main plugin class with code reloading support"""
    
    def Execute(self, doc):
        """Execute the plugin command"""
        # Reload the plugin classes to pick up any code changes
        print("="*80)
        print("🔄 PLMXML Importer - Reloading code...")
        reload_plugin_classes()
        print("="*80)
        
        # Show the dialog
        dlg = PLMXMLDialog()
        dlg.Open(c4d.DLG_TYPE_MODAL)
        return True


# Plugin registration - only runs once when Cinema 4D loads the plugin
if __name__ == "__main__":
    success = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="PLMXML Assembly Importer",
        info=0,
        icon=None,
        help="Imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation",
        dat=PLMXMLImporter()
    )
    
    if success:
        print("🎉 PLMXML Assembly Importer plugin registered successfully!")
        print("💡 Edit code and run plugin again - classes will reload automatically")
    else:
        print("❌ Failed to register PLMXML Assembly Importer plugin!")

      