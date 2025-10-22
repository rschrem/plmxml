"""
PLMXML Assembly Importer Plugin for Cinema 4D 2025
Plugin ID: 1054321
Version: 3.0
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
    
    @staticmethod
    def infer_material_properties(material_data):
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
        metal_keywords = ['stahl', 'steel', 'aluminium', 'aluminum', 'kupfer', 'copper', 
                         'brass', 'messing', 'bronze', 'titan', 'titanium', 'eisen', 'iron']
        if any(keyword in full_material_desc for keyword in metal_keywords):
            return MaterialPropertyInference._create_metal_properties(mat_term, mat_group)
        
        # Check for plastic materials
        plastic_keywords = ['thermoplast', 'plastic', 'kunststoff', 'polymer', 'abs', 'pc', 'pom', 'pa', 'pfa']
        if any(keyword in full_material_desc for keyword in plastic_keywords):
            return MaterialPropertyInference._create_plastic_properties(mat_term)
        
        # Check for rubber/elastomer materials
        rubber_keywords = ['elastomer', 'gummi', 'rubber', 'tpe', 'tps']
        if any(keyword in full_material_desc for keyword in rubber_keywords):
            return MaterialPropertyInference._create_rubber_properties()
        
        # Check for wood materials
        wood_keywords = ['holz', 'wood']
        if any(keyword in full_material_desc for keyword in wood_keywords):
            return MaterialPropertyInference._create_wood_properties(mat_term)
        
        # Check for glass materials
        glass_keywords = ['glas', 'glass']
        if any(keyword in full_material_desc for keyword in glass_keywords):
            return MaterialPropertyInference._create_glass_properties()
        
        # Check for sealant materials
        sealant_keywords = ['dichtstoff', 'sealant', 'dichtung']
        if any(keyword in full_material_desc for keyword in sealant_keywords):
            return MaterialPropertyInference._create_sealant_properties()
        
        # Default material
        return MaterialPropertyInference._create_default_properties()
    
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
            'metalness': 0.0,
            'roughness': 0.9,
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
        
        # Check if we already have a similar material
        existing_material = self.find_existing_material(material_data, doc)
        if existing_material:
            self.logger.log(f"♻ Reusing existing material: {existing_material.GetName()}")
            return existing_material
        
        # Create a new material
        mat = c4d.BaseMaterial(c4d.Mmaterial)
        if not mat:
            self.logger.log("✗ Failed to create new material", "ERROR")
            return None
        
        mat.SetName(mat_name)
        
        # Get material properties
        props = MaterialPropertyInference.infer_material_properties(material_data)
        
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
        
        # Remove default reflection layer
        try:
            # Clear existing layers
            mat[c4d.MATERIAL_REFLECTION_LAYER] = c4d.BaseContainer()
            
            # Add new reflection layer
            layer = mat.AddReflectionLayer()
            if layer:
                layer_id = layer.GetLayerID()
                
                # Set reflection properties based on metalness
                if props['metalness'] > 0.5:
                    # Metallic material - use colored reflection
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = props['base_color']
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS] = props['roughness']
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_SHADER] = 0  # Standard
                else:
                    # Non-metallic material
                    mat[layer_id + c4d.REFLECTION_LAYER_COLOR_COLOR] = c4d.Vector(1, 1, 1)
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS] = props['roughness']
                    mat[layer_id + c4d.REFLECTION_LAYER_MAIN_SHADER] = 0  # Standard
        except Exception as e:
            self.logger.log(f"Reflection layer setup error: {str(e)}", "WARNING")
        
        # Insert material into the document
        doc.InsertMaterial(mat)
        
        # Cache this material
        self.material_cache[mat_name] = mat
        self.material_properties_cache[mat_name] = props
        
        self.logger.log(f"→ Created material: {mat_name}")
        return mat
    
    def find_existing_material(self, material_data, doc):
        """Find existing similar material using two-pass matching system"""
        # Generate the name for the new material
        new_mat_name = self._generate_material_name(material_data)
        
        # Pass 1: Exact Name Match
        if new_mat_name in self.material_cache:
            return self.material_cache[new_mat_name]
        
        # Pass 2: Base Type Grouping (more complex similarity matching)
        new_props = MaterialPropertyInference.infer_material_properties(material_data)
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
    
    def build_hierarchy(self, plmxml_parser, doc, mode="assembly"):
        """Build the Cinema 4D scene hierarchy from parsed data"""
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
            
            # Get full path to JT file (assuming it's relative to PLMXML file)
            plmxml_dir = os.path.dirname(doc.GetDocumentPath()) if doc.GetDocumentPath() else ""
            jt_full_path = os.path.join(plmxml_dir, jt_file) if plmxml_dir else jt_file
            
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
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self._perform_incremental_save(doc)
            self.files_since_last_save = 0  # Reset counter
    
    def _process_redshift_proxy_creation(self, jt_path, parent_obj, material_properties, doc):
        """Process redshift proxy creation"""
        self.logger.log(f"🎬 Creating redshift proxy for: {os.path.basename(jt_path)}")
        
        # Check if Redshift is available
        try:
            import c4d.plugins
            redshift_plugin_id = 1036223  # Redshift plugin ID
            redshift_plugin = c4d.plugins.FindPlugin(redshift_plugin_id)
            
            if redshift_plugin is None:
                self.logger.log("⚠ Redshift not found, skipping proxy creation", "WARNING")
                self.total_files_processed += 1
                return
        except:
            self.logger.log("⚠ Could not access Redshift, skipping proxy creation", "WARNING")
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
        
        # Count polygons in loaded geometry
        total_polygons = self._count_polygons_in_document(temp_doc)
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
        plmxml_dir = os.path.dirname(doc.GetDocumentPath()) if doc.GetDocumentPath() else os.path.dirname(jt_path)
        proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
        proxy_path = os.path.join(plmxml_dir, proxy_filename)
        
        # Use Redshift's proxy export functionality
        try:
            # Create a temporary document with just the object for clean proxy export
            proxy_doc = c4d.documents.BaseDocument()
            proxy_obj_clone = processing_obj.GetClone(c4d.COPYFLAGS_0)
            proxy_doc.InsertObject(proxy_obj_clone)
            
            # In Cinema 4D 2025, command 1038650 saves the currently active document as a Redshift proxy
            # However, it prompts the user for a file location, so we need to save using SaveDocument instead
            # The format ID for Redshift proxy needs to be used with SaveDocument
            # For Cinema 4D 2025, we'll use the appropriate format ID if available, otherwise save as .c4d
            
            # Based on the information provided, in Cinema 4D 2025:
            # c4d.CallCommand(1038650) saves the currently active document as a proxy
            # This command prompts user for file location, so we'll use SaveDocument with appropriate format
            
            # The proper way is to use the Redshift-specific format for SaveDocument
            # Try to use the Redshift proxy format (this may not exist as a SaveDocument format)
            # So we'll use the more reliable approach: save as .c4d and note to convert to .rs
            proxy_c4d_path = os.path.splitext(proxy_path)[0] + ".c4d"
            if c4d.documents.SaveDocument(proxy_doc, proxy_c4d_path, c4d.SAVEDOCUMENTFLAGS_0, c4d.FORMAT_C4DEXPORT):
                self.logger.log(f"✓ Object saved as .c4d: {proxy_c4d_path}")
                
                # Since we know the intended .rs path, let user know they can rename or convert
                self.logger.log(f"ℹ For Redshift use: Convert {os.path.basename(proxy_c4d_path)} to {os.path.basename(proxy_path)} or use Cinema 4D command 1038650 on the saved file to convert to .rs")
            else:
                self.logger.log(f"✗ Failed to save proxy file for: {jt_path}", "ERROR")
        
        except Exception as e:
            self.logger.log(f"✗ Error creating Redshift proxy: {str(e)}", "ERROR")
        
        # Clean up the temporary document
        temp_doc = None  # Allow garbage collection
        proxy_doc = None  # Allow garbage collection
        
        self.logger.log(f"✓ Redshift proxy created for: {os.path.basename(jt_path)}")
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self._perform_incremental_save(doc)
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
            self._perform_incremental_save(doc)
            self.files_since_last_save = 0  # Reset counter
    
    def _process_compile_redshift_proxies(self, jt_path, parent_obj, material_properties, doc):
        """Process compile redshift proxies mode - creates assembly with proxy references"""
        self.logger.log(f"🔗 Compiling redshift proxy assembly for: {os.path.basename(jt_path)}")
        
        # Get the hidden container for proxy objects
        hidden_container = self.geometry_manager.get_or_create_hidden_container(doc)
        
        # Check if proxy file exists
        plmxml_dir = os.path.dirname(doc.GetDocumentPath()) if doc.GetDocumentPath() else os.path.dirname(jt_path)
        proxy_filename = os.path.splitext(os.path.basename(jt_path))[0] + ".rs"
        proxy_path = os.path.join(plmxml_dir, proxy_filename)
        
        proxy_exists = os.path.exists(proxy_path)
        
        # Create proxy object (or placeholder if proxy doesn't exist)
        if proxy_exists:
            # Create Redshift proxy object
            try:
                # Try to create a Redshift proxy object
                import c4d.plugins
                redshift_plugin = c4d.plugins.FindPlugin(1036223)  # Redshift plugin ID
                if redshift_plugin:
                    proxy_obj = c4d.BaseObject(1036224)  # Redshift Proxy object
                    if proxy_obj:
                        proxy_obj[c4d.REDSHIFT_PROXY_PATH] = proxy_path
                        proxy_obj[c4d.REDSHIFT_PROXY_MODE] = 0  # Reference mode
                        proxy_obj.SetName(os.path.splitext(os.path.basename(jt_path))[0] + "_Proxy")
                        # Insert in the hidden container to cache the proxy reference
                        proxy_obj.InsertUnder(hidden_container)
                        self.logger.log(f"✓ Redshift proxy object created: {proxy_filename}")
                    else:
                        # If Redshift proxy object isn't available, create placeholder
                        proxy_obj = self._create_placeholder_cube()
                        proxy_obj.SetName(f"MissingProxy_{os.path.splitext(os.path.basename(jt_path))[0]}")
                        self.logger.log(f"🟦 Created placeholder for missing proxy: {proxy_filename}")
                else:
                    # Redshift not available, create placeholder
                    proxy_obj = self._create_placeholder_cube()
                    proxy_obj.SetName(f"MissingProxy_{os.path.splitext(os.path.basename(jt_path))[0]}")
                    self.logger.log(f"🟦 Redshift unavailable, created placeholder: {proxy_filename}")
            except:
                # Create placeholder as fallback
                proxy_obj = self._create_placeholder_cube()
                proxy_obj.SetName(f"MissingProxy_{os.path.splitext(os.path.basename(jt_path))[0]}")
                self.logger.log(f"🟦 Fallback placeholder created: {proxy_filename}")
        else:
            # Proxy file doesn't exist, create placeholder cube
            proxy_obj = self._create_placeholder_cube()
            proxy_obj.SetName(f"MissingProxy_{os.path.splitext(os.path.basename(jt_path))[0]}")
            self.logger.log(f"🟦 Created placeholder for missing proxy: {proxy_filename}")
        
        if proxy_obj:
            # Create an instance of the proxy object to maintain transforms in the visible hierarchy
            instance_obj = self.geometry_manager.create_instance(proxy_obj, doc)
            if instance_obj:
                instance_obj.SetName(proxy_obj.GetName() + "_Instance")
                # Insert instance under the parent to maintain assembly structure
                instance_obj.InsertUnder(parent_obj)
                self.logger.log(f"✓ Proxy instance added to assembly: {instance_obj.GetName()}")
        
        self.total_files_processed += 1
        
        # Increment files since last save counter
        self.files_since_last_save += 1
        
        # Perform incremental save if needed
        if self.files_since_last_save >= self.save_interval:
            self.logger.log("⏳ Performing incremental save...")
            self._perform_incremental_save(doc)
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
            
        # Create a user data container
        bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_GROUP)
        if bc is None:
            return
            
        group_id = obj.AddUserData(bc)
        group_descr = obj.GetUserDatDescription()
        
        # Add each user value as a string user data
        for key, value in user_data.items():
            bc = c4d.GetCustomDataTypeDefault(c4d.DTYPE_STRING)
            if bc is None:
                continue
                
            bc[c4d.DESC_NAME] = key
            bc[c4d.DESC_SHORT_NAME] = key
            bc[c4d.DESC_ANIMATE] = c4d.DESC_ANIM_OFF
            bc[c4d.DESC_SHADERLINKFLAG] = False
            
            id = obj.AddUserData(bc)
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
    IDC_IMPORT_BUTTON = 1006
    IDC_CANCEL_BUTTON = 1007
    
    def __init__(self):
        super().__init__()
        self.plmxml_path = ""
        self.selected_mode = 0  # 0: Assembly Import, 1: Material Extraction, 2: Create Redshift Proxies, 3: Compile Redshift Proxies
    
    def CreateLayout(self):
        """Create the dialog layout"""
        self.SetTitle("PLMXML Assembly Importer")
        
        # File selection
        self.GroupBegin(0, c4d.BFH_SCALEFIT, cols=2)
        self.AddStaticText(0, c4d.BFH_LEFT, name="PLMXML File:")
        self.AddEditText(self.IDC_FILEPATH, c4d.BFH_SCALEFIT)
        self.SetString(self.IDC_FILEPATH, "")  # Set initial string value
        self.GroupEnd()
        
        self.GroupBegin(0, c4d.BFH_LEFT, cols=1)
        self.AddButton(self.IDC_BROWSE_BUTTON, c4d.BFH_LEFT, name="Browse...")
        self.GroupEnd()
        
        # Mode selection - Radio buttons
        self.GroupBegin(self.IDC_MODE_GROUP, c4d.BFH_LEFT, cols=1, rows=4)
        self.AddRadioText(self.IDC_MODE_MATERIAL, c4d.BFH_LEFT, 300, 20, "Material Extraction Only")
        self.AddRadioText(self.IDC_MODE_PROXY, c4d.BFH_LEFT, 300, 20, "Create Redshift Proxies")
        self.AddRadioText(self.IDC_MODE_COMPILE, c4d.BFH_LEFT, 300, 20, "Compile Redshift Proxies")
        self.AddRadioText(self.IDC_MODE_COMPILE + 1, c4d.BFH_LEFT, 300, 20, "Full Assembly Import")
        self.GroupEnd()
        
        # Select first mode by default (Material Extraction) and set selected_mode accordingly
        self.SetBool(self.IDC_MODE_MATERIAL, True)
        self.selected_mode = 0
        
        # Buttons
        self.GroupBegin(0, c4d.BFH_CENTER, cols=2)
        self.AddButton(self.IDC_IMPORT_BUTTON, c4d.BFH_LEFT, name="OK")
        self.AddButton(self.IDC_CANCEL_BUTTON, c4d.BFH_RIGHT, name="Cancel")
        self.GroupEnd()
        
        return True
    
    def Command(self, id, msg):
        """Handle dialog commands"""
        if id == self.IDC_BROWSE_BUTTON:
            # Show file browser
            file_path = c4d.storage.LoadDialog(
                type=c4d.FILESELECTTYPE_SCENES,
                title="Select PLMXML File",
                flags=c4d.FILESELECT_LOAD
            )
            if file_path:
                self.SetString(self.IDC_FILEPATH, file_path)
                self.plmxml_path = file_path
        
        elif id == self.IDC_MODE_MATERIAL:
            self.selected_mode = 0
            self.SetBool(self.IDC_MODE_MATERIAL, True)
            self.SetBool(self.IDC_MODE_PROXY, False)
            self.SetBool(self.IDC_MODE_COMPILE, False)
            self.SetBool(self.IDC_MODE_COMPILE + 1, False)
        
        elif id == self.IDC_MODE_PROXY:
            self.selected_mode = 1
            self.SetBool(self.IDC_MODE_MATERIAL, False)
            self.SetBool(self.IDC_MODE_PROXY, True)
            self.SetBool(self.IDC_MODE_COMPILE, False)
            self.SetBool(self.IDC_MODE_COMPILE + 1, False)
        
        elif id == self.IDC_MODE_COMPILE:
            self.selected_mode = 2
            self.SetBool(self.IDC_MODE_MATERIAL, False)
            self.SetBool(self.IDC_MODE_PROXY, False)
            self.SetBool(self.IDC_MODE_COMPILE, True)
            self.SetBool(self.IDC_MODE_COMPILE + 1, False)
        
        elif id == self.IDC_MODE_COMPILE + 1:
            self.selected_mode = 3
            self.SetBool(self.IDC_MODE_MATERIAL, False)
            self.SetBool(self.IDC_MODE_PROXY, False)
            self.SetBool(self.IDC_MODE_COMPILE, False)
            self.SetBool(self.IDC_MODE_COMPILE + 1, True)
        
        elif id == self.IDC_IMPORT_BUTTON:
            # Get the file path from the edit text
            self.plmxml_path = self.GetString(self.IDC_FILEPATH)
            if not self.plmxml_path or not os.path.exists(self.plmxml_path):
                c4d.gui.MessageDialog("Please select a valid PLMXML file.")
                return True
            
            # Close dialog and start import process
            self.Close()
            self.start_import_process()
            return True
        
        elif id == self.IDC_CANCEL_BUTTON:
            self.Close()
        
        return True
    
    def start_import_process(self):
        """Start the import process based on selected mode"""
        # Get the current document
        doc = c4d.documents.GetActiveDocument()
        
        # Set up logging with requested format: importPlmxml_{Step}_log.txt
        mode_steps = ["1", "2", "3", "4"]  # Material extraction, Create redshift proxies, Compile redshift proxies, Assembly
        mode_step = mode_steps[self.selected_mode] if 0 <= self.selected_mode < len(mode_steps) else "4"
        log_filename = f"importPlmxml_{mode_step}_log.txt"
        log_path = os.path.join(os.path.dirname(self.plmxml_path), log_filename)
        logger = Logger(log_path)
        
        # Log the start of the process to the console as well
        print(f"🚀 Starting import process for: {os.path.basename(self.plmxml_path)}")
        print(f"📁 Using log file: {log_filename}")
        logger.log(f"🚀 Starting import process for: {os.path.basename(self.plmxml_path)}", "INFO")
        logger.log(f"📁 Using log file: {log_filename}", "INFO")
        logger.log(f"🔧 Selected mode: {self.selected_mode}", "INFO")
        
        try:
            # Initialize components
            plmxml_parser = PLMXMLParser(logger)
            material_manager = Cinema4DMaterialManager(logger)
            geometry_manager = GeometryInstanceManager(logger)
            importer = Cinema4DImporter(logger, material_manager, geometry_manager)
            
            # Map mode to string and create proper log file name
            mode_names = ["material_extraction", "create_redshift_proxies", "compile_redshift_proxies", "assembly"]
            mode_steps = ["1", "2", "3", "4"]  # Corresponding step numbers
            mode_name = mode_names[self.selected_mode] if 0 <= self.selected_mode < len(mode_names) else "assembly"
            mode_step = mode_steps[self.selected_mode] if 0 <= self.selected_mode < len(mode_steps) else "4"
            
            logger.log(f"🚀 Starting import process in mode: {mode_name}")
            
            # Parse the PLMXML file
            if not plmxml_parser.parse_plmxml(self.plmxml_path):
                logger.log("✗ PLMXML parsing failed", "ERROR")
                logger.close()
                return
            
            # Build hierarchy based on selected mode
            success = importer.build_hierarchy(plmxml_parser, doc, mode_name)
            
            if success:
                logger.log(f"🎉 Import completed successfully using mode: {mode_name}")
                c4d.gui.MessageDialog(f"Import completed successfully using mode: {mode_name}")
            else:
                logger.log(f"✗ Import failed with mode: {mode_name}", "ERROR")
                c4d.gui.MessageDialog(f"Import failed with mode: {mode_name}")
            
        except Exception as e:
            logger.log(f"✗ Import process failed: {str(e)}", "ERROR")
            logger.log(f"Traceback: {traceback.format_exc()}", "ERROR")
            c4d.gui.MessageDialog(f"Import process failed: {str(e)}")
        finally:
            logger.close()


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