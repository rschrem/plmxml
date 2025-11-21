import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Union
import re
import yaml
import argparse
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
        self.user_data = []
        self.table_attribute = None
        # Will be populated later with referenced objects
        self.child_objects = []

        for child in element:
            if child.tag.endswith('Representation'):
                self.representation = Representation(child)
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
        self.table_attribute = None

        for child in element:
            if child.tag.endswith('Transform'):
                self.transform = Transform(child)
            elif child.tag.endswith('UserData'):
                self.user_data.append(UserData(child))
            elif child.tag.endswith('TableAttribute'):
                self.table_attribute = TableAttribute(child)

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

def output_as_yaml(plmxml_obj: PLMXML) -> str:
    """
    Output the object tree as YAML for debugging purposes.
    """
    return yaml.dump(plmxml_obj.to_dict(), default_flow_style=False, allow_unicode=True)

def find_line_number(text: str, position: int) -> int:
    """
    Find the line number for a given character position in text.
    """
    lines = text[:position].splitlines()
    return len(lines)

def output_as_brief(plmxml_obj: PLMXML) -> str:
    """
    Output the object hierarchy in a brief format showing only key attributes and indentation for nesting.
    """
    output_lines = []

    # Add header information if available (headers don't have IDs, only attributes)
    if plmxml_obj.header:
        output_lines.append(f"Header: author={plmxml_obj.header.author}")

    # Add ProductDef information with proper nesting
    if plmxml_obj.product_def and plmxml_obj.product_def.instance_graph:
        graph = plmxml_obj.product_def.instance_graph
        output_lines.append(f"InstanceGraph: rootRefs={graph.root_refs}")

        # Create maps of all objects for quick lookup
        part_map = {part.id: part for part in graph.parts}
        instance_map = {instance.id: instance for instance in graph.instances}

        # Create maps for representations and compound reps
        repr_map = {}
        compound_rep_map = {}
        for part in graph.parts:
            if part.representation:
                repr_map[part.representation.id] = part.representation
                for compound_rep in part.representation.compound_reps:
                    compound_rep_map[compound_rep.id] = compound_rep

        # Track which objects have already been output to avoid duplicates
        output_objects = set()

        # Function to recursively output the hierarchy starting from a root object ID
        def output_object_recursive(obj_id, indent_level):
            indent = "  " * indent_level

            # Check if this object has already been output
            if obj_id in output_objects:
                return

            # If it's a part
            if obj_id in part_map:
                part = part_map[obj_id]
                part_line = f"{indent}Part: id={part.id}"
                if part.instance_refs:
                    part_line += f", instanceRefs={part.instance_refs}"
                if part.representation_refs:
                    part_line += f", representationRefs={part.representation_refs}"
                # Add nomenclature if it exists
                if part.nomenclature:
                    part_line += f", nomenclature={part.nomenclature}"
                output_lines.append(part_line)
                output_objects.add(obj_id)

                # Show representation of this part if it exists
                if part.representation:
                    output_object_recursive(part.representation.id, indent_level + 1)

                # Show child objects of this part (from instanceRefs)
                if part.child_objects:
                    for child_obj in part.child_objects:
                        if isinstance(child_obj, Instance):
                            output_object_recursive(child_obj.id, indent_level + 1)
                        elif isinstance(child_obj, Part):
                            output_object_recursive(child_obj.id, indent_level + 1)
                        elif isinstance(child_obj, CompoundRep):
                            output_object_recursive(child_obj.id, indent_level + 1)

            # If it's an instance
            elif obj_id in instance_map:
                instance = instance_map[obj_id]
                instance_line = f"{indent}Instance: id={instance.id}"
                if instance.part_ref:
                    instance_line += f", partRef={instance.part_ref}"
                # Add nomenclature if it exists
                if instance.nomenclature:
                    instance_line += f", nomenclature={instance.nomenclature}"
                output_lines.append(instance_line)
                output_objects.add(obj_id)

                # Show transform if it exists
                if instance.transform:
                    transform_line = f"{indent}  Transform: id={instance.transform.id}"
                    if instance.transform.matrix:
                        transform_line += f", matrix={instance.transform.matrix_as_string()}"
                    output_lines.append(transform_line)

                # If the instance references a part, output that part as a child
                if instance.part_ref:
                    referenced_part_ids = instance.part_ref.split()
                    for ref_part_id in referenced_part_ids:
                        output_object_recursive(ref_part_id, indent_level + 1)

            # If it's a representation
            elif obj_id in repr_map:
                repr_obj = repr_map[obj_id]
                if repr_obj.id not in output_objects:
                    repr_line = f"{indent}Representation: id={repr_obj.id}"
                    output_lines.append(repr_line)
                    output_objects.add(repr_obj.id)

                    # Show compound reps associated with this representation
                    for compound_rep in repr_obj.compound_reps:
                        output_object_recursive(compound_rep.id, indent_level + 1)

            # If it's a compound rep
            elif obj_id in compound_rep_map:
                compound_rep_obj = compound_rep_map[obj_id]
                if compound_rep_obj.id not in output_objects:
                    cr_line = f"{indent}CompoundRep: id={compound_rep_obj.id}"
                    if compound_rep_obj.location:
                        cr_line += f", location={compound_rep_obj.location}"
                    if compound_rep_obj.name:
                        cr_line += f", name={compound_rep_obj.name}"
                    output_lines.append(cr_line)
                    output_objects.add(compound_rep_obj.id)

                    # Show transform if it exists
                    if compound_rep_obj.transform:
                        transform_line = f"{indent}  Transform: id={compound_rep_obj.transform.id}"
                        if compound_rep_obj.transform.matrix:
                            transform_line += f", matrix={compound_rep_obj.transform.matrix_as_string()}"
                        output_lines.append(transform_line)

        # Determine root objects from rootRefs attribute
        if graph.root_refs:
            root_ids = graph.root_refs.split()
        else:
            # If no rootRefs, consider all top-level parts and instances
            root_ids = []

        # Output all root objects and their hierarchy
        for root_id in root_ids:
            output_object_recursive(root_id, 0)

        # Output relations
        for relation in graph.relations:
            relation_line = f"Relation: id={relation.id}"
            if relation.related_refs:
                relation_line += f", relatedRefs={relation.related_refs}"
            output_lines.append(relation_line)

    return "\n".join(output_lines)

def main():
    parser = argparse.ArgumentParser(description='Parse PLMXML file and output as YAML')
    parser.add_argument('file_path', help='Path to the XML file to parse')
    parser.add_argument('-o', '--output', help='Output file path (default: stdout)')
    parser.add_argument('--encoding', default='utf-8', help='File encoding (default: utf-8)')
    parser.add_argument('--brief', action='store_true', help='Output brief format with indented hierarchy')

    args = parser.parse_args()

    xml_content = None  # Initialize to avoid UnboundLocalError

    try:
        with open(args.file_path, 'r', encoding=args.encoding) as file:
            xml_content = file.read()

        plmxml_obj = parse_plmxml(xml_content)

        if args.brief:
            brief_output = output_as_brief(plmxml_obj)
            output_content = brief_output
        else:
            yaml_output = output_as_yaml(plmxml_obj)
            output_content = yaml_output

        if args.output:
            with open(args.output, 'w', encoding=args.encoding) as output_file:
                output_file.write(output_content)
            print(f"Output written to {args.output}")
        else:
            print(output_content)

    except FileNotFoundError:
        print(f"Error: File '{args.file_path}' not found.", file=sys.stderr)
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

if __name__ == "__main__":
    main()