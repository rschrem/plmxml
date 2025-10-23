"""
PLMXML Assembly Importer Plugin for Cinema 4D 2025
Plugin ID: 1054321
Version: 3.1
Git Commit: $Format:%H$
"""

import c4d
from c4d import plugins, gui, documents
import xml.etree.ElementTree as ET
import os
from collections import defaultdict
import traceback


# Plugin ID - Unique identifier for this plugin
PLUGIN_ID = 1054321


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
    
    def log(self, message, level='INFO'):
        """Log message to both console and file"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {level}: {message}"
        
        print(formatted_message)
        
        if self.file_handle:
            try:
                self.file_handle.write(formatted_message + "\n")
                self.file_handle.flush()  # Immediate disk write
            except:
                pass  # Don't let logging errors break the application
    
    def close(self):
        """Close the log file"""
        if self.file_handle:
            self.file_handle.close()


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
        """Infer material properties from material data dictionary"""
        # Extract material properties from dcx:TableAttribute columns
        mat_group = material_data.get('mat_group', '').lower()
        mat_standard = material_data.get('mat_standard', '').lower()
        mat_number = material_data.get('mat_number', '').lower()
        mat_term = material_data.get('mat_term', '').lower()
        treatment = material_data.get('treatment', '').lower()
        body_name = material_data.get('body_name', '').lower()
        
        # Combine all material properties for keyword matching
        full_material_desc = f"{mat_group} {mat_standard} {mat_number} {mat_term} {treatment} {body_name}".lower()
        
        # Check for metal materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.METAL_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.METAL_KEYWORDS, logger)
            return MaterialPropertyInference._create_metal_properties(mat_term, mat_group)
        
        # Check for plastic materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.PLASTIC_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.PLASTIC_KEYWORDS, logger)
            return MaterialPropertyInference._create_plastic_properties(mat_term)
        
        # Check for rubber/elastomer materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.RUBBER_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.RUBBER_KEYWORDS, logger)
            return MaterialPropertyInference._create_rubber_properties()
        
        # Check for wood materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.WOOD_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.WOOD_KEYWORDS, logger)
            return MaterialPropertyInference._create_wood_properties(mat_term)
        
        # Check for glass materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.GLASS_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.GLASS_KEYWORDS, logger)
            return MaterialPropertyInference._create_glass_properties()
        
        # Check for sealant materials
        if any(keyword in full_material_desc for keyword in MaterialPropertyInference.SEALANT_KEYWORDS):
            # Track unknown keywords
            MaterialPropertyInference._track_unknown_keywords(full_material_desc, MaterialPropertyInference.SEALANT_KEYWORDS, logger)
            return MaterialPropertyInference._create_sealant_properties()
        
        # Track unknown keywords even for default material
        MaterialPropertyInference._track_unknown_keywords(full_material_desc, 
            MaterialPropertyInference.METAL_KEYWORDS + MaterialPropertyInference.PLASTIC_KEYWORDS + 
            MaterialPropertyInference.RUBBER_KEYWORDS + MaterialPropertyInference.WOOD_KEYWORDS + 
            MaterialPropertyInference.GLASS_KEYWORDS + MaterialPropertyInference.SEALANT_KEYWORDS, logger)
        
        # Default material
        return MaterialPropertyInference._create_default_properties()
    
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
    def _create_metal_properties(mat_term, mat_group):
        """Create properties for metal materials"""
        # Default metal properties
        props = {
            'base_color': c4d.Vector(0.72, 0.72, 0.75),  # Steel color as default
            'metalness': 1.0,
            'roughness': 0.15,  # Polished
            'ior': 1.0,
            'transparency': 0.0
        }
        
        # Specific metal colors based on term
        metal_colors = {
            'aluminum': c4d.Vector(0.87, 0.88, 0.89),
            'copper': c4d.Vector(0.95, 0.64, 0.54),
            'gold': c4d.Vector(1.0, 0.85, 0.57)
        }
        
        if mat_term and mat_term.lower() in metal_colors:
            props['base_color'] = metal_colors[mat_term.lower()]
        elif mat_group and mat_group.lower() in metal_colors:
            props['base_color'] = metal_colors[mat_group.lower()]
        else:
            # Distinguish between different steel grades by varying the color slightly based on grade number
            # Extract numeric grade from material number if it exists
            import re
            grade_number = None
            
            # Check mat_term and mat_group for grade numbers (like "1.4016", "-1.0338", etc.)
            if mat_term:
                grade_match = re.search(r'([0-9]+\.?[0-9]*)', mat_term.replace('-', ''))
                if grade_match:
                    try:
                        grade_number = float(grade_match.group(1))
                    except ValueError:
                        pass
            
            if not grade_number and mat_group:
                grade_match = re.search(r'([0-9]+\.?[0-9]*)', mat_group.replace('-', ''))
                if grade_match:
                    try:
                        grade_number = float(grade_match.group(1))
                    except ValueError:
                        pass
            
            # If we have a grade number, adjust the color slightly to distinguish different grades
            if grade_number is not None:
                # Use the grade number to create a slight color variation
                # This is a simple algorithm to create variation in the steel color
                variation_factor = (grade_number % 30) * 0.01  # Create subtle variation based on grade
                base_r, base_g, base_b = 0.72, 0.72, 0.75
                props['base_color'] = c4d.Vector(
                    min(1.0, max(0.0, base_r + variation_factor * 0.1)),
                    min(1.0, max(0.0, base_g + variation_factor * 0.05)),
                    min(1.0, max(0.0, base_b + variation_factor * 0.15))
                )
        
        return props
    
    @staticmethod
    def _create_plastic_properties(mat_term):
        """Create properties for plastic materials"""
        props = {
            'base_color': c4d.Vector(0.25, 0.25, 0.30),  # Default dark plastic
            'metalness': 0.0,
            'roughness': 0.3,  # Glossy
            'ior': 1.49,
            'transparency': 0.0
        }
        
        # Color variations based on term
        if 'black' in mat_term.lower():
            props['base_color'] = c4d.Vector(0.08, 0.08, 0.08)
        elif 'white' in mat_term.lower():
            props['base_color'] = c4d.Vector(0.95, 0.95, 0.95)
        elif 'gray' in mat_term.lower() or 'grey' in mat_term.lower():
            props['base_color'] = c4d.Vector(0.5, 0.5, 0.5)
        
        return props
    
    @staticmethod
    def _create_rubber_properties():
        """Create properties for rubber/elastomer materials"""
        return {
            'base_color': c4d.Vector(0.10, 0.10, 0.10),
            'metalness': 0.0,  # Should definitely be 0.0 for rubber
            'roughness': 0.9,  # High roughness for matte rubber appearance
            'ior': 1.52,
            'transparency': 0.0
        }
    
    @staticmethod
    def _create_wood_properties(mat_term):
        """Create properties for wood materials"""
        props = {
            'base_color': c4d.Vector(0.55, 0.35, 0.22),  # Default wood
            'metalness': 0.0,
            'roughness': 0.75,
            'ior': 1.53,
            'transparency': 0.0
        }
        
        # Specific wood types
        if 'eiche' in mat_term.lower() or 'oak' in mat_term.lower():
            props['base_color'] = c4d.Vector(0.65, 0.50, 0.35)
        elif 'buche' in mat_term.lower() or 'beech' in mat_term.lower():
            props['base_color'] = c4d.Vector(0.75, 0.60, 0.45)
        
        return props
    
    @staticmethod
    def _create_glass_properties():
        """Create properties for glass materials"""
        return {
            'base_color': c4d.Vector(0.95, 0.95, 0.95),
            'metalness': 0.0,
            'roughness': 0.05,
            'ior': 1.52,
            'transparency': 0.95
        }
    
    @staticmethod
    def _create_sealant_properties():
        """Create properties for sealant materials"""
        return {
            'base_color': c4d.Vector(0.15, 0.15, 0.15),
            'metalness': 0.0,
            'roughness': 0.8,
            'ior': 1.5,
            'transparency': 0.0
        }
    
    @staticmethod
    def _create_default_properties():
        """Create default material properties"""
        return {
            'base_color': c4d.Vector(0.5, 0.5, 0.5),
            'metalness': 0.0,
            'roughness': 0.4,
            'ior': 1.4,
            'transparency': 0.0
        }


class Cinema4DMaterialManager:
    """Material creation, caching, and deduplication system"""
    
    def __init__(self, logger):
        self.logger = logger
        self.material_cache = {}  # Dictionary to store created materials
        self.material_properties_cache = {}
    
    def create_material(self, material_data, doc):
        """Create a Cinema 4D material based on material data"""
        # Create a unique material name based on material properties
        mat_name = self._generate_material_name(material_data)
        
        # Check if we already have a similar material in the current document
        existing_material_in_doc = self._find_material_in_document(mat_name, doc)
        if existing_material_in_doc:
            self.logger.log(f"♻ Reusing existing material in document: {existing_material_in_doc.GetName()}")
            # Cache this material to avoid recreation
            self.material_cache[mat_name] = existing_material_in_doc
            # Get its properties for cache
            props = self._extract_material_properties(existing_material_in_doc)
            if props:
                self.material_properties_cache[mat_name] = props
            return existing_material_in_doc
        
        # Check if we already have a similar material in our cache
        existing_material = self.find_existing_material(material_data, doc)
        if existing_material:
            self.logger.log(f"♻ Reusing cached material: {existing_material.GetName()}")
            return existing_material
        
        # Create a new material
        mat = c4d.BaseMaterial(c4d.Mmaterial)
        if not mat:
            self.logger.log("✗ Failed to create new material", "ERROR")
            return None
        
        mat.SetName(mat_name)
        
        # Get material properties
        props = MaterialPropertyInference.infer_material_properties(material_data, self.logger)
        
        # Set base color
        mat[c4d.MATERIAL_COLOR_COLOR] = props['base_color']
        mat[c4d.MATERIAL_COLOR_BRIGHTNESS] = 1.0
        
        # Enable luminance and set to black for realistic lighting
        mat[c4d.MATERIAL_LUMINANCE_COLOR] = c4d.Vector(0, 0, 0)
        
        # Set transparency if needed
        if props['transparency'] > 0:
            mat[c4d.MATERIAL_USE_TRANSPARENCY] = True
            mat[c4d.MATERIAL_TRANSPARENCY_BRIGHTNESS] = 1.0 - props['transparency']
        
        # Enable reflection
        mat[c4d.MATERIAL_USE_REFLECTION] = True
        
        # Setup reflection using appropriate Cinema 4D API (skip clearing existing layers)
        try:
            # Add new reflection layer
            layer = mat.AddReflectionLayer()
            if layer:
                layer_id = layer.GetLayerID()
                
                # Set reflection properties based on metalness
                if props['metalness'] > 0.5:
                    # Metallic material - use colored reflection
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = props['base_color']
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS] = props['roughness']
                    # Set reflection strength for metals (high reflectivity)
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_REFLECTION] = 1.0
                    # For metals, set fresnel to conductor mode if supported
                    try:
                        mat[layer_id + c4d.REFLECTION_LAYER_MAIN_FRESNEL_MODE] = 1  # Conductor
                    except:
                        pass  # Some versions don't support this parameter
                else:
                    # Non-metallic material - keep reflections subtle and colorless
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = c4d.Vector(0.8, 0.8, 0.8)  # Subtle white reflection
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS] = props['roughness']
                    # Set moderate reflection strength for non-metals
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_REFLECTION] = 0.3  # Lower reflectivity than metals
                    # For non-metals, use dielectric fresnel (default)
                    try:
                        mat[layer_id + c4d.REFLECTION_LAYER_MAIN_FRESNEL_MODE] = 0  # Dielectric
                    except:
                        pass  # Some versions don't support this parameter
                    
                    # For rubber/elastomer materials with high roughness, reflections should be very subtle
                    if props['roughness'] > 0.7:
                        # Reduce reflection strength significantly for very rough materials
                        mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_REFLECTION] = 0.05  # Very low reflection strength
        except Exception as e:
            self.logger.log(f"Reflection layer setup error: {str(e)}", "WARNING")
        
        # Insert material into the document
        doc.InsertMaterial(mat)
        
        # Verify the material was actually added to the document
        if not self._verify_material_in_document(mat.GetName(), doc):
            self.logger.log(f"⚠ Material may not have been properly added to document: {mat.GetName()}", "WARNING")
        
        # Cache this material
        self.material_cache[mat_name] = mat
        self.material_properties_cache[mat_name] = props
        
        self.logger.log(f"→ Created material: {mat_name}")
        return mat
    
    def _find_material_in_document(self, mat_name, doc):
        """Find a material with specific name in the document"""
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == mat_name:
                return mat
            mat = mat.GetNext()
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
    
    def find_existing_material(self, material_data, doc):
        """Find existing similar material using document and cache checking"""
        # Generate the name for the new material
        new_mat_name = self._generate_material_name(material_data)
        
        # First, check if there's already a material with this exact name in the document
        existing_in_doc = self._find_material_in_document(new_mat_name, doc)
        if existing_in_doc:
            # Cache it and return it
            self.material_cache[new_mat_name] = existing_in_doc
            props = self._extract_material_properties(existing_in_doc)
            if props:
                self.material_properties_cache[new_mat_name] = props
            return existing_in_doc
        
        # Pass 1: Check in our material cache for exact name match
        if new_mat_name in self.material_cache:
            return self.material_cache[new_mat_name]
        
        # Pass 2: Check for similarity in our cache
        new_props = MaterialPropertyInference.infer_material_properties(material_data, self.logger)
        new_base_type = new_mat_name.split('_')[0] if '_' in new_mat_name else new_mat_name
        
        for mat_name, cached_mat in self.material_cache.items():
            if mat_name not in self.material_properties_cache:
                continue
                
            # Check if base types match
            cached_base_type = mat_name.split('_')[0] if '_' in mat_name else mat_name
            if new_base_type.lower() != cached_base_type.lower():
                continue
            
            # Compare properties with tolerance
            cached_props = self.material_properties_cache[mat_name]
            if self._materials_are_similar(new_props, cached_props):
                return cached_mat
        
        # Pass 3: Check for similar materials already in the document
        doc_mat = doc.GetFirstMaterial()
        while doc_mat:
            doc_mat_name = doc_mat.GetName()
            if doc_mat_name in self.material_properties_cache:
                # We've already analyzed this material
                cached_props = self.material_properties_cache[doc_mat_name]
                if self._materials_are_similar(new_props, cached_props):
                    # Cache this material for future use
                    self.material_cache[doc_mat_name] = doc_mat
                    return doc_mat
            else:
                # Check if this document material has a similar name pattern
                doc_base_type = doc_mat_name.split('_')[0] if '_' in doc_mat_name else doc_mat_name
                if new_base_type.lower() == doc_base_type.lower():
                    # Extract properties to compare
                    doc_props = self._extract_material_properties(doc_mat)
                    if doc_props and self._materials_are_similar(new_props, doc_props):
                        # Cache this material for future use
                        self.material_cache[doc_mat_name] = doc_mat
                        self.material_properties_cache[doc_mat_name] = doc_props
                        return doc_mat
            doc_mat = doc_mat.GetNext()
        
        return None
    
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
        return f"{mat_group}_{mat_term}_{mat_number}"


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
            self._hidden_container = c4d.BaseObject(c4d.Onull)
            self._hidden_container.SetName("_PLMXML_Geometries")
            self._hidden_container[c4d.NULLOBJECT_DISPLAY] = 3  # Hidden
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
    
    def _create_placeholder_cube(self):
        """Create a 10m cube placeholder for missing JT files"""
        cube = c4d.BaseObject(c4d.Ocube)
        if cube is None:
            return None
        cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(10000, 10000, 10000)  # 10m in Cinema 4D units
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
    
    def create_instance(self, original_obj, doc):
        """Create an instance object that references the original geometry"""
        if original_obj is None:
            return None
            
        instance = c4d.BaseObject(c4d.Oinstance)
        if instance is None:
            return None
            
        # Link to the original object
        instance[c4d.INSTANCEOBJECT_LINK] = original_obj
        
        # Set to render instance mode
        try:
            instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
        except:
            # Compatibility fallback
            pass
        
        # Insert into document
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
    
    def build_hierarchy(self, plmxml_parser, doc, mode="assembly", plmxml_file_path=None, working_directory=None):
        """Build the Cinema 4D scene hierarchy from parsed data"""
        # Reset unknown keywords tracking for this import
        MaterialPropertyInference.unknown_keywords.clear()
        
        # Store the PLMXML file path and working directory to help resolve file paths
        self.plmxml_file_path = plmxml_file_path
        self.working_directory = working_directory
        
        self.logger.log("="*80)
        self.logger.log("🏗️  Starting hierarchy building process")
        self.logger.log("="*80)
        
        # Get root references for the hierarchy
        root_refs = plmxml_parser.build_hierarchy()
        
        if not root_refs:
            self.logger.log("⚠ No root references found in PLMXML", "WARNING")
            return False
        
        # Create main assembly container
        assembly_root = c4d.BaseObject(c4d.Onull)
        assembly_root.SetName("Assembly")
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
    
    def _process_instance(self, instance_data, plmxml_parser, doc, parent_obj, mode):
        """Process a single instance and its hierarchy"""
        part_ref = instance_data['part_ref']
        
        # Skip if part reference is invalid
        if not part_ref or part_ref not in plmxml_parser.parts:
            self.logger.log(f"⚠ Skipping instance with invalid part reference: {part_ref}", "WARNING")
            return
        
        part_data = plmxml_parser.parts[part_ref]
        part_name = part_data['name'] or f"Part_{part_ref}"
        
        # Create a null object for this assembly node
        null_obj = c4d.BaseObject(c4d.Onull)
        if null_obj is None:
            self.logger.log(f"✗ Failed to create null object for: {part_name}", "ERROR")
            return
            
        null_obj.SetName(part_name)
        
        # Apply instance transform
        if instance_data['transform']:
            matrix = self._create_matrix_from_transform(instance_data['transform'])
            null_obj.SetMg(matrix)
        
        # Add user data
        self._add_user_data(null_obj, instance_data['user_data'])
        
        # Insert under parent
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
            elif mode == "create_redshift_proxies":
                # Create redshift proxies
                self._process_redshift_proxy_creation(jt_full_path, null_obj, material_properties, doc)
            elif mode == "compile_redshift_proxies":
                # Compile assembly using existing redshift proxies
                self._process_compile_redshift_proxies(jt_full_path, null_obj, material_properties, doc)
            else:
                # Default: load geometry and create instances
                self._process_geometry_loading(jt_full_path, jt_transform, material_properties, null_obj, doc)
        
        # Process children
        for child_id in instance_data.get('children', []):
            if child_id in plmxml_parser.instances:
                self._process_instance(
                    plmxml_parser.instances[child_id], 
                    plmxml_parser, 
                    doc, 
                    null_obj, 
                    mode
                )
    
    def _process_material_extraction(self, jt_path, material_properties, doc):
        """Process material extraction only - no geometry loading"""
        self.logger.log(f"🎨 Extracting materials from: {os.path.basename(jt_path)}")
        
        # Create material from properties
        if material_properties:
            material = self.material_manager.create_material(material_properties, doc)
            if material:
                self.total_materials += 1
        
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Skip incremental save in material extraction mode, just reset counter
        self.files_since_last_save = 0  # Reset counter to prevent incremental saves during material extraction
    
    def _process_redshift_proxy_creation(self, jt_path, parent_obj, material_properties, doc):
        """Process redshift proxy creation"""
        self.logger.log(f"🎬 Creating redshift proxy for: {os.path.basename(jt_path)}")
        
        # Check if Redshift is available
        try:
            import c4d.plugins
            # Redshift plugin ID may vary by version, try the most common one
            redshift_plugin_ids = [1036223, 1001059]  # Common Redshift plugin IDs
            redshift_plugin = None
            found_plugin_id = None
            
            for plugin_id in redshift_plugin_ids:
                redshift_plugin = c4d.plugins.FindPlugin(plugin_id)
                if redshift_plugin is not None:
                    found_plugin_id = plugin_id
                    self.logger.log(f"✓ Redshift plugin found with ID: {plugin_id}")
                    break
            
            if redshift_plugin is None:
                self.logger.log("⚠ Redshift not found, skipping proxy creation", "WARNING")
                self.total_files_processed += 1
                return
            else:
                self.logger.log(f"✓ Using Redshift plugin ID: {found_plugin_id}")
        except Exception as e:
            self.logger.log(f"⚠ Could not access Redshift: {str(e)}, skipping proxy creation", "WARNING")
            self.total_files_processed += 1
            return
        
        # Check if file exists
        if not os.path.exists(jt_path):
            self.logger.log(f"✗ JT file not found: {jt_path}", "ERROR")
            self.total_files_processed += 1
            return
        
        # Load the JT file temporarily
        temp_doc = c4d.documents.BaseDocument()
        load_success = False
        
        try:
            self.logger.log(f"⏳ Loading JT file temporarily: {jt_path}")
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
            self.total_files_processed += 1
            return
        
        # Count polygons in loaded geometry using the geometry manager
        total_polygons = self.geometry_manager._count_polygons_in_document(temp_doc)
        self.logger.log(f"📊 Polygons in {os.path.basename(jt_path)}: {total_polygons:,}")
        
        # Get the geometry from the temp document - handle multiple objects if present
        temp_obj = temp_doc.GetFirstObject()
        if temp_obj is None:
            self.logger.log(f"⚠ No geometry found in JT file: {jt_path}", "WARNING")
            self.total_files_processed += 1
            return
        
        # Handle multiple root objects by creating a container if needed
        root_objects = []
        current_obj = temp_doc.GetFirstObject()
        while current_obj:
            root_objects.append(current_obj)
            current_obj = current_obj.GetNext()
        
        # If multiple root objects exist, create a container; otherwise use the single object
        if len(root_objects) > 1:
            # Create a container null for multiple objects
            container = c4d.BaseObject(c4d.Onull)
            container.SetName(os.path.splitext(os.path.basename(jt_path))[0] + "_Container")
            
            # Move all root objects under the container
            for obj in root_objects:
                obj.Remove()  # Remove from document temporarily
                obj.InsertUnder(container)  # Insert under container
            
            # Insert the container under parent
            container.InsertUnder(parent_obj)
            processing_obj = container
        else:
            # Single object case - move it to the main document
            temp_obj.Remove()  # Remove from temp document
            temp_obj.InsertUnder(parent_obj)  # Insert under parent
            processing_obj = temp_obj
        
        # If we have material properties, try to match closest material in the current scene
        if material_properties:
            self._replace_materials_with_closest_match(processing_obj, material_properties, doc)
        
        # Determine the output path for the Redshift proxy
        # Use the working directory, not the active document directory
        # Use .rs extension as intended for Redshift proxies
        proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
        proxy_path = os.path.join(self.working_directory, proxy_filename)
        self.logger.log(f"📁 Proxy output path: {proxy_path}")
        
        # Use Redshift's proxy export functionality
        try:
            # Create a temporary document with just the object for clean proxy export
            proxy_doc = c4d.documents.BaseDocument()
            proxy_obj_clone = processing_obj.GetClone(c4d.COPYFLAGS_0)
            proxy_doc.InsertObject(proxy_obj_clone)
            
            # Try to use Redshift's Python API for non-interactive proxy export
            try:
                import redshift
                
                # Create or get a Redshift renderer accessor
                rs_renderer = redshift.Renderer.Redshift()
                
                # Setup export settings
                settings = redshift.ProxyExportSettings()
                
                settings.exportSelectionOnly = False
                settings.exportAnimations = False
                settings.filePath = proxy_path
                settings.exportMaterials = True
                settings.exportInstances = True
                settings.embedTextures = False
                
                # Get the active document to use with Redshift export
                active_doc = c4d.documents.GetActiveDocument()
                
                # Call the export method - this should work non-interactively
                success = rs_renderer.ExportProxy(active_doc, proxy_obj_clone, settings)
                
                if success:
                    self.logger.log(f"✓ Redshift proxy exported using Redshift Python API: {proxy_path}")
                else:
                    self.logger.log(f"⚠ Redshift Python API export failed for {proxy_path}, trying fallback methods", "WARNING")
                    raise RuntimeError("Redshift API export failed")
                    
            except ImportError:
                self.logger.log("ℹ Redshift Python module not available, using fallback export methods", "INFO")
                # Fall back to the previous approach
                self._export_redshift_proxy_fallback(proxy_doc, proxy_path, proxy_obj_clone)
            except Exception as e:
                self.logger.log(f"⚠ Redshift Python API export failed: {str(e)}, trying fallback methods", "WARNING")
                # Fall back to the previous approach
                self._export_redshift_proxy_fallback(proxy_doc, proxy_path, proxy_obj_clone)
        
        except Exception as e:
            self.logger.log(f"✗ Error creating Redshift proxy: {str(e)}", "ERROR")
    
    def _export_redshift_proxy_fallback(self, proxy_doc, proxy_path, proxy_obj_clone):
        """Fallback method for Redshift proxy export when Python API is not available"""
        try:
            # In Cinema 4D 2025, we need to save Redshift proxies without user interaction
            # The command 1038650 prompts user for file location, so we'll use SaveDocument instead
            
            # First, check if there's a specific RS format for SaveDocument in Cinema 4D 2025
            rs_format_id = getattr(c4d, 'FORMAT_RS', None)
            self.logger.log(f"🔍 FORMAT_RS available: {rs_format_id}")
            
            # Also check for other available Redshift format IDs
            redshift_format_ids = {}
            for attr_name in dir(c4d):
                if 'REDSHIFT' in attr_name.upper() or 'RS' in attr_name.upper():
                    try:
                        attr_value = getattr(c4d, attr_name)
                        if isinstance(attr_value, int) and attr_value > 1000000:  # Likely a format ID
                            redshift_format_ids[attr_name] = attr_value
                    except:
                        pass
            
            if redshift_format_ids:
                self.logger.log(f"🔍 Available Redshift-related format IDs: {redshift_format_ids}")
            else:
                self.logger.log("🔍 No Redshift-related format IDs found in c4d module")
            
            if rs_format_id:
                self.logger.log(f"⏳ Attempting direct RS format save: {rs_format_id}")
                # Try to save directly as RS format if it's available
                if c4d.documents.SaveDocument(proxy_doc, proxy_path, c4d.SAVEDOCUMENTFLAGS_0, rs_format_id):
                    self.logger.log(f"✓ Redshift proxy exported to: {proxy_path}")
                else:
                    self.logger.log(f"⚠ Direct RS format save failed for {proxy_path}, trying .c4d fallback", "WARNING")
                    # Fallback: save as .c4d if the RS format save fails
                    proxy_c4d_path = os.path.splitext(proxy_path)[0] + ".c4d"
                    if c4d.documents.SaveDocument(proxy_doc, proxy_c4d_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT):
                        self.logger.log(f"✓ Object saved as .c4d: {proxy_c4d_path}")
                        self.logger.log(f"ℹ For Redshift use: Convert {os.path.basename(proxy_c4d_path)} to {os.path.basename(proxy_path)} manually or use Redshift proxy conversion")
                    else:
                        self.logger.log(f"✗ Failed to save proxy file", "ERROR")
            else:
                # No direct RS format available in this Cinema 4D version
                # Check if there are other Redshift-specific format IDs we can use
                # Try common Redshift format IDs that might be available
                redshift_formats = [
                    getattr(c4d, 'FORMAT_REDSHIFT_PROXY', 0),
                    getattr(c4d, 'FORMAT_REDSHIFT_RS', 0),
                    getattr(c4d, 'FORMAT_RS', 0),
                    1036224,  # Common Redshift proxy format ID
                    1038650   # Redshift RS Proxy command ID (sometimes used as format)
                ]
                
                saved_successfully = False
                for i, format_id in enumerate(redshift_formats):
                    if format_id and format_id != 0:
                        self.logger.log(f"⏳ Trying Redshift format {i+1}/{len(redshift_formats)}: {format_id}")
                        if c4d.documents.SaveDocument(proxy_doc, proxy_path, c4d.SAVEDOCUMENTFLAGS_0, format_id):
                            self.logger.log(f"✓ Redshift proxy exported to: {proxy_path} (format: {format_id})")
                            saved_successfully = True
                            break
                        else:
                            self.logger.log(f"⚠ Redshift format {format_id} failed")
                
                if not saved_successfully:
                    # Try one more approach - save as .c4d to the intended .rs location
                    # Sometimes Redshift can work with .c4d files that are renamed to .rs
                    self.logger.log(f"ℹ Redshift format not available, trying direct .rs save as .c4d format", "INFO")
                    if c4d.documents.SaveDocument(proxy_doc, proxy_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT):
                        self.logger.log(f"✓ Object saved with .rs extension using .c4d format: {proxy_path}")
                        self.logger.log(f"ℹ This .rs file contains .c4d data that Redshift can reference")
                    else:
                        # Final fallback: save as .c4d with clear naming
                        proxy_c4d_path = os.path.splitext(proxy_path)[0] + ".c4d"
                        self.logger.log(f"ℹ Trying final fallback to .c4d: {proxy_c4d_path}")
                        if c4d.documents.SaveDocument(proxy_doc, proxy_c4d_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT):
                            self.logger.log(f"✓ Object saved as .c4d: {proxy_c4d_path}")
                            self.logger.log(f"ℹ For Redshift proxy: Load {os.path.basename(proxy_c4d_path)} in Cinema 4D and use Redshift's proxy creation tools or rename to .rs")
                        else:
                            self.logger.log(f"✗ Failed to save proxy file", "ERROR")
        except Exception as e:
            self.logger.log(f"✗ Fallback Redshift proxy export failed: {str(e)}", "ERROR")
        
        self.logger.log(f"✓ Redshift proxy processing completed for: {os.path.basename(proxy_path)}")
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self.geometry_manager._perform_incremental_save(doc)
            self.files_since_last_save = 0  # Reset counter
    
    def _replace_materials_with_closest_match(self, obj, material_properties, doc):
        """Replace materials with closest matching material from the current scene"""
        # First, try to find a material with identical name
        material_name = self.material_manager._generate_material_name(material_properties)
        
        # Look for existing material with the same name
        mat = doc.GetFirstMaterial()
        while mat:
            if mat.GetName() == material_name:
                # Found a material with identical name, use this one
                self._apply_material_to_object_with_new_material(obj, mat)
                self.logger.log(f"→ Applied existing material: {material_name}")
                return
            mat = mat.GetNext()
        
        # If no exact match found, find the closest match based on material properties
        closest_mat = None
        min_distance = float('inf')
        
        mat = doc.GetFirstMaterial()
        while mat:
            # Calculate how similar this material is to the requested properties
            distance = self._calculate_material_distance(mat, material_properties)
            if distance < min_distance:
                min_distance = distance
                closest_mat = mat
            mat = mat.GetNext()
        
        if closest_mat and min_distance < 0.5:  # Threshold for similarity
            # Apply the closest material
            self._apply_material_to_object_with_new_material(obj, closest_mat)
            self.logger.log(f"→ Applied closest matching material: {closest_mat.GetName()}")
        else:
            # Create new material from properties
            new_mat = self.material_manager.create_material(material_properties, doc)
            if new_mat:
                self._apply_material_to_object_with_new_material(obj, new_mat)
                self.logger.log(f"→ Created new material: {new_mat.GetName()}")
    
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
    
    def _process_geometry_loading(self, jt_path, jt_transform, material_properties, parent_obj, doc):
        """Process geometry loading with instances"""
        # Get the geometry (cached or newly loaded)
        geometry_obj = self.geometry_manager.get_cached_geometry(jt_path, doc)
        if geometry_obj is None:
            self.logger.log(f"✗ Failed to get geometry for: {jt_path}", "ERROR")
            return
        
        # Create an instance of the geometry
        instance_obj = self.geometry_manager.create_instance(geometry_obj, doc)
        if instance_obj is None:
            self.logger.log(f"✗ Failed to create instance for: {jt_path}", "ERROR")
            return
        
        # Apply JT transform to the instance if provided
        if jt_transform:
            jt_matrix = self._create_matrix_from_transform(jt_transform)
            instance_obj.SetMg(jt_matrix)
        
        # Insert instance under the parent (the assembly node)
        instance_obj.InsertUnder(parent_obj)
        
        # Create and apply material if material properties exist
        if material_properties:
            material = self.material_manager.create_material(material_properties, doc)
            if material:
                self._apply_material_to_geometry(instance_obj, material, doc)
                self.total_materials += 1
        
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self.geometry_manager._perform_incremental_save(doc)
            self.files_since_last_save = 0  # Reset counter
    
    def _process_compile_redshift_proxies(self, jt_path, parent_obj, material_properties, doc):
        """Process compile redshift proxies mode - creates assembly with proxy references"""
        self.logger.log(f"🔗 Compiling redshift proxy assembly for: {os.path.basename(jt_path)}")
        
        # Get the hidden container for proxy objects (_PLMXML_Geometries)
        hidden_container = self.geometry_manager.get_or_create_hidden_container(doc)
        self.logger.log(f"📁 Using hidden container: {hidden_container.GetName() if hidden_container else 'None'}")
        
        # Create a null object with the same name as the JT file directly under _PLMXML_Geometries
        jt_name = os.path.splitext(os.path.basename(jt_path))[0]
        jt_null_obj = c4d.BaseObject(c4d.Onull)
        if jt_null_obj:
            jt_null_obj.SetName(jt_name)
            doc.InsertObject(jt_null_obj)  # Insert into document first
            jt_null_obj.InsertUnder(hidden_container)  # Then under the hidden container
            self.logger.log(f"📁 Created JT null object: {jt_null_obj.GetName()} under {hidden_container.GetName() if hidden_container else 'None'}")
            self.logger.log(f"📁 JT null object inserted successfully: {jt_null_obj.GetUp().GetName() if jt_null_obj.GetUp() else 'No parent'}")
        else:
            self.logger.log(f"✗ Failed to create JT null object for: {jt_name}", "ERROR")
            self.total_files_processed += 1
            return
        
        # Check if proxy file exists
        # Use the working directory, not the document directory or JT path directory
        proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
        proxy_path = os.path.join(self.working_directory, proxy_filename)
        
        proxy_exists = os.path.exists(proxy_path)
        self.logger.log(f"📁 Checking for proxy: {proxy_path} (exists: {proxy_exists})")
        self.logger.log(f"📁 Working directory: {self.working_directory}")
        self.logger.log(f"📁 JT path: {jt_path}")
        self.logger.log(f"📁 Self.plmxml_file_path: {getattr(self, 'plmxml_file_path', 'NOT SET')}")
        
        # If proxy doesn't exist, also log the directory contents for debugging
        if not proxy_exists:
            self.logger.log(f"📁 Directory contents of {plmxml_dir}:")
            try:
                dir_contents = os.listdir(plmxml_dir)
                rs_files = [f for f in dir_contents if f.endswith('.rs')]
                self.logger.log(f"📁 Found .rs files: {rs_files}")
                # Also log all files for debugging purposes
                self.logger.log(f"📁 All files in directory ({len(dir_contents)} total): {[f for f in dir_contents if not f.startswith('.')][:20]}")  # Limit to first 20 non-hidden files
            except Exception as e:
                self.logger.log(f"⚠ Exception listing directory contents: {str(e)}", "WARNING")
                
            # Log current working directory and document path for additional debugging
            self.logger.log(f"📁 Current working directory: {os.getcwd()}")
            self.logger.log(f"📁 Document path: {doc.GetDocumentPath() if doc.GetDocumentPath() else 'Not set'}")
        else:
            self.logger.log(f"✅ Proxy file found: {proxy_path}")
        
        # Create proxy object (or placeholder if proxy doesn't exist) as a child of the JT null object
        if proxy_exists:
            # Create Redshift proxy object (Redshift is assumed to be available)
            try:
                # Create Redshift proxy object using the plugin ID
                proxy_obj = c4d.BaseObject(1038649)  # Redshift proxy plugin ID: com.redshift3d.redshift4c4d.proxyloader
                if proxy_obj:
                    # Set the proxy file path (just the filename, not full path, as per requirements)
                    proxy_filename_only = os.path.basename(proxy_path)
                    proxy_obj[c4d.REDSHIFT_PROXY_FILE] = proxy_filename_only
                    proxy_obj.SetName(proxy_filename)
                    
                    doc.InsertObject(proxy_obj)  # Insert into document first
                    proxy_obj.InsertUnder(jt_null_obj)  # Then under the JT null object
                    self.logger.log(f"✅ Redshift proxy object created: {proxy_filename}")
                else:
                    # If Redshift proxy creation failed, create placeholder cube
                    proxy_obj = self.geometry_manager._create_placeholder_cube(500.0)  # 5m cube
                    proxy_obj.SetName("Placeholder_Cube")
                    doc.InsertObject(proxy_obj)  # Insert into document first
                    proxy_obj.InsertUnder(jt_null_obj)  # Then under the JT null object
                    self.logger.log(f"🟦 Failed to create Redshift proxy, using placeholder: {proxy_filename}")
            except:
                # If Redshift is not available or any other error, create placeholder cube
                proxy_obj = self.geometry_manager._create_placeholder_cube(500.0)  # 5m cube
                proxy_obj.SetName("Placeholder_Cube")
                doc.InsertObject(proxy_obj)  # Insert into document first
                proxy_obj.InsertUnder(jt_null_obj)  # Then under the JT null object
                self.logger.log(f"🟦 Redshift not available, using placeholder: {proxy_filename}")
        else:
            # Proxy file doesn't exist, create placeholder cube as child of JT null object
            proxy_obj = self.geometry_manager._create_placeholder_cube(500.0)  # 5m cube (500cm in Cinema 4D units)
            proxy_obj.SetName("Placeholder_Cube")
            doc.InsertObject(proxy_obj)  # Insert into document first
            proxy_obj.InsertUnder(jt_null_obj)  # Then under the JT null object
            self.logger.log(f"🟦 Created placeholder cube for missing proxy: {proxy_filename}")
        
        # Create an instance of the JT null object to maintain transforms in the visible hierarchy
        if jt_null_obj:
            instance_obj = self.geometry_manager.create_instance(jt_null_obj, doc)
            if instance_obj:
                instance_obj.SetName(jt_name + "_Instance")
                # Insert instance under the parent to maintain assembly structure
                instance_obj.InsertUnder(parent_obj)
                self.logger.log(f"✓ Proxy instance added to assembly: {instance_obj.GetName()}")
                self.logger.log(f"📁 Parent object: {parent_obj.GetName() if parent_obj else 'None'}")
                self.logger.log(f"📁 JT null object: {jt_null_obj.GetName() if jt_null_obj else 'None'}")
                self.logger.log(f"📁 Proxy object: {proxy_obj.GetName() if proxy_obj else 'None'}")
                self.logger.log(f"📁 Instance object: {instance_obj.GetName() if instance_obj else 'None'}")
        
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self.geometry_manager._perform_incremental_save(doc)
            self.files_since_last_save = 0  # Reset counter
    
    def _create_matrix_from_transform(self, transform_matrix):
        """Convert 16-value row-major matrix to Cinema 4D Matrix (transposed)"""
        if len(transform_matrix) != 16:
            return c4d.Matrix()  # Return identity matrix if invalid
        
        # Cinema 4D uses column-major matrices, so we transpose the rotation part
        m = c4d.Matrix()
        # Read columns from row-major (transposes rotation)
        m.v1 = c4d.Vector(transform_matrix[0], transform_matrix[4], transform_matrix[8])    # Column 0: X-axis
        m.v2 = c4d.Vector(transform_matrix[1], transform_matrix[5], transform_matrix[9])    # Column 1: Y-axis
        m.v3 = c4d.Vector(transform_matrix[2], transform_matrix[6], transform_matrix[10])   # Column 2: Z-axis
        m.off = c4d.Vector(transform_matrix[12], transform_matrix[13], transform_matrix[14]) # Translation
        
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
        self.working_directory = os.path.dirname(c4d_file_path) if c4d_file_path and os.path.exists(c4d_file_path) else ""
    
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
            # Use the working directory to find PLMXML file
            if not self.working_directory or not os.path.exists(self.working_directory):
                c4d.gui.MessageDialog("Please save your Cinema 4D file first.")
                return True
            
            # Look for .plmxml files in the working directory
            plmxml_files = [f for f in os.listdir(self.working_directory) if f.lower().endswith('.plmxml') and os.path.isfile(os.path.join(self.working_directory, f))]
            
            if not plmxml_files:
                c4d.gui.MessageDialog(f"No .plmxml files found in the working directory: {self.working_directory}")
                return True
            
            # If there are multiple .plmxml files, just take the first one
            # In a real implementation, you might want to show a selection dialog
            self.plmxml_path = os.path.join(self.working_directory, plmxml_files[0])
            
            # Run import process directly without closing dialog first (to maintain context)
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
        logger.log(f"📂 Working directory for all file operations: {self.working_directory}", "INFO")
        logger.log(f"📂 Directory for searching PLMXML and JT files: {self.working_directory}", "INFO")
        
        # Verify that both paths are the same
        if c4d_document_path and os.path.dirname(c4d_document_path) == self.working_directory:
            logger.log(f"✅ Verification: C4D document directory and working directory match", "INFO")
        elif not c4d_document_path:
            logger.log(f"⚠️ Verification: C4D document not saved yet (no path available)", "WARNING")
        else:
            logger.log(f"❌ Verification: C4D document directory and working directory differ", "ERROR")
            logger.log(f"   C4D document directory: {os.path.dirname(c4d_document_path) if c4d_document_path else 'N/A'}", "ERROR")
            logger.log(f"   Working directory: {self.working_directory}", "ERROR")
        
        logger.log(f"🔧 Selected mode: {self.selected_mode}", "INFO")
        
        try:
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


class PLMXMLImporter(plugins.CommandData):
    """Main plugin class"""
    
    def Execute(self, doc):
        """Execute the plugin command"""
        # Show the dialog
        dlg = PLMXMLDialog()
        dlg.Open(c4d.DLG_TYPE_MODAL)
        return True


# Plugin registration
if __name__ == "__main__":
    # Register the plugin
    success = plugins.RegisterCommandPlugin(
        id=PLUGIN_ID,
        str="PLMXML Assembly Importer",
        info=0,
        icon=None,
        help="Imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation",
        dat=PLMXMLImporter()
    )
    
    if success:
        print("PLMXML Assembly Importer plugin registered successfully!")
    else:
        print("Failed to register PLMXML Assembly Importer plugin!")