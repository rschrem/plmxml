# PLMXML Assembly Importer Plugin - Technical Architecture Document
**Version:** 3.1
**Git Commit:** $Format:%H$

## 1. System Overview

### 1.1 Purpose
The PLMXML Assembly Importer is a Cinema 4D 2025 Python plugin that enables the import of Mercedes-Benz PLMXML assembly files with full hierarchy preservation, intelligent material creation, and optimized performance through geometry instancing.

### 1.2 Architecture Goals
- **Modularity**: Maintainable architecture with well-defined components
- **Performance**: Efficient memory usage through geometry instancing
- **Robustness**: Reliable operation with comprehensive error handling
- **Extensibility**: Support for future enhancements and features
- **Compatibility**: Full compatibility with Cinema 4D 2025

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PLMXML Importer Plugin                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   UI Layer      │  │ Business Logic  │  │  Data Access    │  │
│  │                 │  │                 │  │                 │  │
│  │ - Main Dialog   │  │ - PLMXMLParser  │  │ - XML Parser    │  │
│  │ - Mode Selector │  │ - Cinema4DImporter │ │ - JT Loader   │  │
│  │ - Progress UI   │  │ - MaterialManager │ │ - File System │  │
│  └─────────────────┘  │ - GeometryManager │ │                 │  │
│                       │ - Logger         │ └─────────────────┘  │
│                       └─────────────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Component Architecture

### 3.1 Plugin Registration Component
**File:** `PLMXMLImporter.pyp`

**Responsibilities:**
- Register the plugin with Cinema 4D
- Provide the main entry point for the plugin
- Handle plugin initialization and cleanup

**Class:** `PLMXMLImporter(plugins.CommandData)`

**Methods:**
- `Execute()` - Main plugin execution method
- `ShowDialog()` - Show the main user interface

### 3.2 User Interface Component
**Class:** `PLMXMLDialog(gui.GeDialog)`

**Responsibilities:**  
- Display mode selection (Step 1: Material Extraction Only, Step 2: Create Redshift Proxies Only, Step 3: Build Assembly Tree Only)
- Auto-detect PLMXML file from same directory as current C4D document (using doc.GetDocumentPath() directly)
- Button management with Cancel on left, OK on right
- Dialog closes immediately on OK press
- Progress feedback display
- Results summary

### 3.3 PLMXML Parser Component
**Class:** `PLMXMLParser`

**Responsibilities:**
- Parse PLMXML files using ElementTree
- Extract hierarchy information from InstanceGraph
- Extract part definitions and JT file references
- Extract material properties and user data
- Build lookup tables for ID resolution

**Methods:**
- `parse_plmxml(file_path)` - Parse the main PLMXML file
- `extract_hierarchy()` - Extract the assembly hierarchy
- `extract_material_definitions()` - Extract material properties
- `get_jt_files()` - Get list of referenced JT files
- `build_lookup_tables()` - Build ID to object mappings

### 3.4 Material Management Component
**Class:** `MaterialPropertyInference`

**Responsibilities:**
- Infer material properties from keywords
- Create PBR parameters based on material type
- Support for Metal, Plastic, Rubber, Wood, Glass, and Sealant types

**Methods:**
- `infer_material_properties(material_data)` - Infer properties from material data
- `create_metal_properties(keyword)` - Create properties for metal materials
- `create_plastic_properties(keyword)` - Create properties for plastic materials
- `create_rubber_properties(keyword)` - Create properties for rubber materials
- `create_wood_properties(keyword)` - Create properties for wood materials
- `create_glass_properties(keyword)` - Create properties for glass materials
- `create_sealant_properties(keyword)` - Create properties for sealant materials

**Class:** `Cinema4DMaterialManager`

**Responsibilities:**
- Create Cinema 4D materials with PBR properties
- Implement material deduplication with tolerance matching
- Handle two-pass material matching system
- Create and manage reflection layers

**Methods:**
- `create_material(material_data)` - Create a Cinema 4D material
- `find_existing_material(material_data)` - Find existing similar material
- `materials_match(mat1, mat2)` - Check if two materials are similar
- `apply_material_to_geometry(material, obj)` - Apply material to geometry
- `get_material_key(material_data)` - Create unique key for material

### 3.5 Geometry Management Component
**Class:** `GeometryInstanceManager`

**Responsibilities:**
- Manage geometry caching to prevent multiple loads
- Create instance objects for repeated geometries
- Apply transforms to instances and geometry
- Handle JT file loading and cleanup

**Methods:**
- `load_jt_geometry(jt_path)` - Load JT file into temporary document
- `create_instance(original_obj, transform)` - Create instance with transform
- `get_cached_geometry(jt_path)` - Get cached geometry for JT file
- `apply_transforms(obj, transform_matrix)` - Apply 4x4 matrix transform
- `cleanup_temp_document()` - Clean up temporary document memory

### 3.6 Import Logic Component
**Class:** `Cinema4DImporter`

**Responsibilities:**
- Build Cinema 4D scene hierarchy from parsed data
- Apply user data from PLMXML to objects
- Manage mode-specific import behaviors
- Handle material assignment to geometry objects

**Methods:**
- `build_hierarchy(parsed_data)` - Build scene hierarchy
- `create_null_object(instance_data)` - Create null object for assembly nodes
- `apply_user_data(obj, user_data)` - Apply user data to object
- `collect_geometry(obj)` - Recursively find geometry objects
- `apply_materials_to_geometry()` - Apply materials to geometry only

### 3.7 Logging Component
**Class:** `Logger`

**Responsibilities:**
- Dual output logging (console and file)
- Immediate flush to disk for crash recovery
- UTF-8 encoding with proper formatting
- Statistics tracking during processing

**Methods:**
- `log(message, level='INFO')` - Log a message
- `log_progress(file_index, total_files)` - Log progress percentage
- `log_statistics()` - Log current statistics
- `start_timer()` - Start timing an operation
- `end_timer()` - End timing an operation

## 4. Data Flow Architecture

### 4.1 Full Assembly Import Mode
```
1. User selects PLMXML file and "Full Assembly" mode
2. PLMXMLParser parses the XML file
3. MaterialPropertyInference processes material definitions
4. Cinema4DMaterialManager creates materials and handles deduplication
5. GeometryInstanceManager processes JT files with caching
6. Cinema4DImporter builds hierarchy with transforms
7. Instance objects reference shared geometry
8. Progress updates and statistics tracked
```

### 4.2 Material Extraction Mode
```
1. User selects PLMXML file and "Material Extraction" mode
2. PLMXMLParser identifies all referenced JT files
3. For each JT file:
   a. Load temporarily
   b. Extract material properties
   c. Create materials in main document
   d. Delete geometry
4. MaterialManager handles deduplication
5. Progress tracking and statistics
```

### 4.3 Redshift Proxy Mode
```
1. User selects PLMXML file and "Create Redshift Proxies" mode
2. For each JT file:
   a. Load temporarily
   b. Replace materials with closest available in scene
   c. Export as Redshift proxy (.rs)
   d. Delete geometry
3. Progress tracking and statistics
```

### 4.4 Build Assembly Tree Only Mode (Step 3)
```
1. User selects \"Build Assembly Tree Only\" mode (auto-detects PLMXML file from C4D document directory)
2. PLMXMLParser extracts hierarchy data
3. Create hidden container (_PLMXML_Geometries) for proxy objects
4. For each JT file:
   a. Create null object with same name as JT file directly under _PLMXML_Geometries
   b. Check if .rs proxy file exists in same directory as PLMXML file
   c. If .rs file exists: Create Redshift Proxy object as child with just filename (no path)
   d. If .rs file missing: Create 5×5×5 meter cube as child
5. Recreate original hierarchy in Assembly root using instance references
6. Use instance references to Null objects in _PLMXML_Geometries tree for proper linking
7. Handle missing proxy files with cube placeholders
```

## 5. Memory Management Architecture

### 5.1 Instancing System
```
Scene Structure:
├── _PLMXML_Geometries (hidden container)
│   ├── A0009904738_1 (null object)
│   │   └── A0009904738_1_RS_Proxy or Placeholder_Cube  ← Either RS Proxy or 5×5×5m cube
│   ├── A2237304410_31 (null object)
│   │   └── A2237304410_31_RS_Proxy or Placeholder_Cube
│   ├── A2237308001_30 (null object)
│   │   └── A2237308001_30_RS_Proxy or Placeholder_Cube
│   └── A2237308001_13 (null object)
│       └── A2237308001_13_RS_Proxy or Placeholder_Cube
└── Assembly (visible hierarchy)
    ├── Component_A
    │   └── A0009904738_1_Instance  ← Instance references Null object in _PLMXML_Geometries
    └── Component_B
        └── A0009904738_1_Instance  ← References same Null object with different transform
```

### 5.2 Caching Strategy
- Cache geometry objects in dictionary with JT file path as key
- Use weak references where possible to prevent memory leaks
- Clean up temporary documents after each file processing
- Implement object pooling for frequently created objects

## 6. Error Handling Architecture

### 6.1 Pre-flight Checks
- File existence verification before loading
- Log full paths for debugging
- Validate XML structure before processing

### 6.2 Exception Handling
- Wrap JT loading operations in try-catch blocks
- Provide detailed error messages with context
- Implement fallback strategies for missing files

### 6.3 Fallback Strategy
- Create 10m cube placeholders for missing JT files
- Continue processing instead of aborting
- Log all errors with severity levels

## 7. Performance Optimizations

### 7.1 Memory Optimizations
- Geometry instancing to reduce memory usage
- Incremental saving to prevent data loss
- Temporary document cleanup after processing
- Material deduplication with tolerance matching

### 7.2 Processing Optimizations
- Parallel processing where possible (with thread safety)
- Progress tracking to maintain UI responsiveness
- Batch operations where appropriate

## 8. Integration Points

### 8.1 Cinema 4D Integration
- Uses standard Cinema 4D Python API
- Compatible with Cinema 4D 2025 (specifically tested with command ID 1038650 for RS Proxy export)
- Leverages native JT import functionality
- Properly handles Redshift plugin integration (plugin ID: 1036223)
- Uses correct Redshift Proxy Object plugin ID (1038649) for proxy creation
- Implements proper dialog integration with c4d.DLG_OK and c4d.DLG_CANCEL
- Follows Cinema 4D 2025 UI conventions and best practices
- Handles object insertion order correctly (InsertObject first, then InsertUnder)
- Uses proper Redshift parameter IDs (c4d.REDSHIFT_PROXY_FILE, c4d.REDSHIFT_PROXY_MODE)

### 8.2 Redshift Integration
- Creates .rs proxy files for Redshift using proper Cinema 4D 2025 command (1038650)
- Implements proxy referencing system with proper RS Proxy objects (plugin ID: 1038649)
- Maintains compatibility with Redshift rendering pipeline
- Uses c4d.REDSHIFT_PROXY_FILE parameter for proxy file assignment
- Handles Redshift plugin detection with fallback to placeholder cubes (plugin ID: 1036223)
- Creates 5×5×5 meter placeholder cubes when .rs files are missing
- Properly sets proxy file paths with just filename (no full path)
- Uses proper Redshift plugin IDs for compatibility with Cinema 4D 2025

### 8.3 File System Integration
- Cross-platform file path handling
- UTF-8 encoding support
- Incremental save functionality

## 9. Security Considerations
- Validate PLMXML input files to prevent malicious content
- Sanitize file paths to prevent directory traversal
- Implement safe XML parsing to prevent XXE attacks
- Validate JT file content before loading