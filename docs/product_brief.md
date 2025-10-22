# Product Brief
**Version:** 3.1
**Git Commit:** $Format:%H$

Complete Specification for PLMXML Assembly Importer Plugin for Cinema 4D 2025
Project Overview
Create a Cinema 4D 2025 Python plugin that imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation, intelligent material creation, geometry instancing optimization, and robust error handling.

1. PLUGIN BASICS
Installation & Registration
* File Location: plugins/PLMXMLImporter/PLMXMLImporter.pyp
* Plugin ID: 1054321
* Plugin Name: "PLMXML Assembly Importer"
* Menu Location: Extensions → User Scripts → PLMXML Assembly Importer
* Version: 3.1
Dependencies
import c4d
from c4d import plugins, gui
import xml.etree.ElementTree as ET
import os
from collections import defaultdict

2. IMPORT MODES
The plugin offers THREE distinct work modes that are chosen from at plugin startup via dialog with a radio button  dialog on startup:
Step 1: Material Extraction Only
* Dialog option: "Material Extraction" → Selected
* Behavior:
    * Scans ALL JT files referenced in PLMXML
    * Loads each JT file temporarily
    * Extracts and creates materials
    * Immediately deletes geometry after material extraction
    * Saves document after each file
    * Creates complete material library with NO geometry
    * Progress tracking with detailed statistics
Step 2: Create redshift proxies
* Dialog option: "Create redshift proxies" → Selected
* Behavior:
    * Scans ALL JT files referenced in PLMXML
    * Loads each JT file temporarily
    * The loaded jt materials are replaced by the closes fitting material in the open cinema4d file. Close fit means: if material name is idetical always use this material. If not: ignores the material name and only checks which of the already existing material has the best matching material parameters overall to achieve the most similar look - to evaluate this compare the required material with all materials available.
    * Export the loaded geometry as a redshift proxy. The filename of the redshift proxy is the same as the JT file name but with .rs extension in same folder as the plmxml file
    * Immediately deletes geometry after redshift proxy export
    * Progress tracking with detailed statistics
Step 3: Compile redshift proxies
* Dialog option: "Compile redshift proxies" → Selected
* Behavior:
    * In a hidden subtree all redshift proxies nodes are created in a flat non-hirarcical list without any transformation and referencing the on disk .rs file  in the folder the plmxml file was loaded from - each required proxy is loaded only once to safe memory. If a required redshift proxy file with file ending .rs is missing in the folder the plmxml file was loaded from a cube with 500x500x500 cm is created instead with the object name in this case is the file name of the missing rs proxy file.
    * In the main subtree (not hidden) is creates null objects to mimic the original assembly structure. Instances referencing to the hidden redshift proxy objects that load the .rs files are used and the required transforms are applied on the instance object to maintain correct positioning

3. PLMXML FILE STRUCTURE
XML Namespaces
namespaces = {
    'plm': 'http://www.plmxml.org/Schemas/PLMXMLSchema',
    'dcx': 'http://www.smaragd.dcx.com/Schemas/Smaragd'
}
Key Elements to Parse
Instance Graph
<InstanceGraph rootRefs="topID10028">
  <Instance id="ID10044" partRef="ID10025" quantity="1">
    <Transform>matrix values (16 floats)</Transform>
    <UserValue title="key" value="value"/>
  </Instance>
</InstanceGraph>
Parts with JT References
<Part id="ID10025" name="Part Name" instanceRefs="child_ids">
  <Representation format="JT">
    <CompoundRep location="filename.jt">
      <Transform>matrix values (16 floats)</Transform>
      <dcx:TableAttribute definitionRef="j0MaterialDetailMatrix">
        <dcx:Row>
          <dcx:Column col="0" value="STAHL/STAHLGUSS"/>  <!-- mat_group -->
          <dcx:Column col="1" value="EN 10269"/>         <!-- mat_standard -->
          <dcx:Column col="2" value="1.5525"/>           <!-- mat_number -->
          <dcx:Column col="3" value="+QT"/>              <!-- treatment -->
          <dcx:Column col="7" value="20MnB4"/>           <!-- mat_term -->
          <dcx:Column col="10" value="BODY_NAME"/>       <!-- body_name -->
        </dcx:Row>
      </dcx:TableAttribute>
    </CompoundRep>
  </Representation>
</Part>

4. MATERIAL SYSTEM
Material Property Inference
Automatically detect material type from keywords and apply appropriate PBR properties:
Metal Materials (metalness > 0.5)
Keywords: stahl, steel, aluminium, aluminum, kupfer, copper, brass, messing, bronze, titan, titanium, eisen, iron
Properties:
* Base Color: Varies by metal type
    * Steel: RGB(0.72, 0.72, 0.75)
    * Aluminum: RGB(0.87, 0.88, 0.89)
    * Copper: RGB(0.95, 0.64, 0.54)
    * Gold: RGB(1.0, 0.85, 0.57)
* Metalness: 1.0
* Roughness: 0.15 (polished) or 0.3 (standard)
* Fresnel: Conductor mode
* Reflection Color: Uses base color
Plastic Materials
Keywords: thermoplast, plastic, kunststoff, polymer, abs, pc, pom, pa, pfa
Properties:
* Base Color: Varies by color descriptors
    * Black: RGB(0.08, 0.08, 0.08)
    * White: RGB(0.95, 0.95, 0.95)
    * Gray: RGB(0.5, 0.5, 0.5)
    * Default: RGB(0.25, 0.25, 0.30)
* Metalness: 0.0
* Roughness: 0.3 (glossy) or 0.5 (standard)
* IOR: 1.49
* Fresnel: Dielectric mode
Rubber/Elastomer Materials
Keywords: elastomer, gummi, rubber, tpe, tps
Properties:
* Base Color: RGB(0.10, 0.10, 0.10)
* Metalness: 0.0
* Roughness: 0.9
* IOR: 1.52
Wood Materials
Keywords: holz, wood
Properties:
* Base Color: Varies by wood type
    * Oak: RGB(0.65, 0.50, 0.35)
    * Beech: RGB(0.75, 0.60, 0.45)
    * Default: RGB(0.55, 0.35, 0.22)
* Metalness: 0.0
* Roughness: 0.75
* IOR: 1.53
Glass Materials
Keywords: glas, glass
Properties:
* Base Color: RGB(0.95, 0.95, 0.95)
* Metalness: 0.0
* Roughness: 0.05
* IOR: 1.52
* Transparency: 0.95
Sealant Materials
Keywords: dichtstoff, sealant, dichtung
Properties:
* Base Color: RGB(0.15, 0.15, 0.15)
* Metalness: 0.0
* Roughness: 0.8
* IOR: 1.5
Cinema 4D Material Creation
Use standard Cinema 4D materials (c4d.Mmaterial), NOT Redshift.
Material Setup Process:
1. Create standard material: c4d.BaseMaterial(c4d.Mmaterial)
2. Set base color: mat[c4d.MATERIAL_COLOR_COLOR] = base_color
3. Enable reflection: mat[c4d.MATERIAL_USE_REFLECTION] = True
4. Remove default reflection layers
5. Add GGX reflection layer: mat.AddReflectionLayer()
6. Configure layer based on metalness:
    * Metals: Black base color, colored reflection, conductor fresnel
    * Dielectrics: Colored base, white reflection, dielectric fresnel with IOR
7. Set roughness: mat[layer_id + c4d.REFLECTION_LAYER_MAIN_VALUE_ROUGHNESS]
8. Wrap all layer parameter setting in try-except blocks (Cinema 4D 2025 compatibility)
Material Naming Convention
Format: {mat_group}_{mat_term}_{mat_number} Example: STAHL_20MnB4_1.5525
Material Deduplication
Two-Pass Matching System:
Pass 1: Exact Name Match
* Look for materials with identical names
* Compare properties with lenient tolerances
Pass 2: Base Type Grouping
* Extract base type (first part before underscore)
* Example: "STAHL_20MnB4" and "STAHL_Steel" both group as "STAHL"
* Compare only if base types match
Tolerance Values:
* Color tolerance: 0.1 (10% difference allowed)
* Property tolerance: 0.15 (15% difference in roughness allowed)
* This groups visually similar materials to reduce material count
Console Feedback:
* ♻ Reusing existing material: STAHL_20MnB4_1.5525
* → Grouping 'STAHL_X' with existing 'STAHL_Y'

5. GEOMETRY HANDLING
JT File Loading
Import Settings:
* Flags: c4d.SCENEFILTER_OBJECTS (geometry only, NO materials)
* Load into temporary document
* Remove all existing material tags from imported geometry
Multi-Object Handling:
* If JT contains multiple root objects: Create container Null
* If JT contains single object: Use directly
* Clone with c4d.COPYFLAGS_NONE for complete geometry copy
Instance System (Memory Optimization)
Architecture:
Scene:
├── _PLMXML_Geometries (hidden container)
│   ├── [Original] part1.jt  ← Actual geometry (stored once)
│   └── [Original] part2.jt
└── Assembly (hierarchy)
    ├── Component_A
    │   └── part1.jt (Instance) ← References original
    └── Component_B
        └── part1.jt (Instance) ← References same original
Implementation:
1. First occurrence of JT file:
    * Load geometry
    * Store in hidden _PLMXML_Geometries container
    * Cache reference in dictionary
    * Create Instance object that references it
    * Apply transform to instance
2. Subsequent occurrences:
    * Retrieve cached original geometry
    * Create new Instance object
    * Link to original: instance[c4d.INSTANCEOBJECT_LINK] = original
    * Apply unique transform to this instance
    * Set multi-instance mode: instance[c4d.INSTANCEOBJECT_RENDERINSTANCE_MODE] = 1
Key Point: Each instance can have different transforms while sharing geometry
Material Application
Target: Apply materials to actual geometry, NOT to Null containers
Process:
1. Recursively find all geometry objects (skip c4d.Onull)
2. Create texture tag for each geometry object
3. Assign material to tag
4. Insert tag on geometry object
def collect_geometry(obj):
    if obj.GetType() != c4d.Onull:
        geometry_objects.append(obj)
    # Recurse through children

6. TRANSFORM SYSTEM
Transform Matrix Format
PLMXML uses 16-value row-major 4×4 matrices:
[0  1  2  3 ]   [Xx  Xy  Xz  0 ]
[4  5  6  7 ]   [Yx  Yy  Yz  0 ]
[8  9  10 11]   [Zx  Zy  Zz  0 ]
[12 13 14 15]   [Tx  Ty  Tz  1 ]
Cinema 4D Conversion
Cinema 4D uses column-major matrices. Must transpose rotation part:
m = c4d.Matrix()
# Read columns from row-major (transposes rotation)
m.v1 = c4d.Vector(matrix[0], matrix[4], matrix[8])    # Column 0: X-axis
m.v2 = c4d.Vector(matrix[1], matrix[5], matrix[9])    # Column 1: Y-axis
m.v3 = c4d.Vector(matrix[2], matrix[6], matrix[10])   # Column 2: Z-axis
m.off = c4d.Vector(matrix[12], matrix[13], matrix[14]) # Translation
obj.SetMg(m)
Transform Hierarchy
Two Transform Levels:
1. Instance Transform: From <Instance> element → Applied to Null object
2. JT Transform: From <CompoundRep> element → Applied to Instance object
Hierarchy:
Null Object (Assembly node)
├─ Transform: Instance transform
└─ Instance Object (Geometry reference)
   └─ Transform: JT transform
Final position = Parent transform × Instance transform

7. ERROR HANDLING & ROBUSTNESS
Pre-Flight Checks
Before attempting to load each JT file:
1. Check file exists: os.path.exists(jt_path)
2. Log full path before load attempt
3. If missing: Create 10m cube placeholder
Exception Handling
Wrap JT file loading in try-except:
try:
    load_success = c4d.documents.MergeDocument(temp_doc, jt_path, c4d.SCENEFILTER_OBJECTS)
except Exception as e:
    logger.log(f"  ✗ EXCEPTION during load: {e}")
    load_success = False
Fallback Strategy
If file missing OR load fails:
1. Create 10m × 10m × 10m cube placeholder
2. Name: Placeholder_{jt_file}
3. Size: c4d.Vector(10000, 10000, 10000) (10m in Cinema 4D units)
4. Still process materials for this file
5. Continue to next file (never stop processing)
Logging System
Logger Class:
* Writes to BOTH console and file simultaneously
* File location: Same folder as PLMXML, named plugin.log
* Flush after each write (immediate disk write)
* UTF-8 encoding
Log Format:
──────────────────────────────────────────────────────────────────────
[23/150] (15.3%) Processing: A2237304410_31.jt
──────────────────────────────────────────────────────────────────────
  📂 File found on disk: /full/path/to/A2237304410_31.jt
  ⏳ Loading JT file...
  ✓ Geometry loaded successfully
  📊 Polygons in this file: 156,780
  🎨 Processing 5 material definition(s)...
  ✓ Created 2 new material(s)
  ♻ Reused 3 existing material(s)
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 Total Materials: 45
  🔺 Total Polygons: 2,345,678
  📈 Progress: 15.3% complete
  💾 Saving incremental...
  ✓ Document saved incrementally
Error Log Format:
  ✗ File not found on disk: /path/to/missing.jt
  🟦 Using 10m cube placeholder instead
  📊 Polygons in placeholder: 12
Incremental Saving
Method: Use Cinema 4D's built-in "Save Incremental" command
* Command ID: 12098
* Call: c4d.CallCommand(12098)
* Automatic file naming: file_0001.c4d, file_0002.c4d, etc.
* Save after EVERY JT file is processed
* Final save at completion
Requirements: User must save document manually once before starting plugin

8. STATISTICS TRACKING
Polygon Counting
def count_polygons_in_document(doc):
    total = 0
    # Recursively count c4d.Opolygon objects
    # Use obj.GetPolygonCount() for each
    return total
Statistics to Track:
* Per File: Polygon count, materials created/reused
* Cumulative: Total polygons, total materials, progress percentage
* Final Summary: Files processed, unique materials, polygons, averages
Display Format:
* Use comma formatting: 1,234,567
* Show percentages: 15.3%
* Unicode icons: 📁 📦 🔺 📊 📈 ♻ ✓ ✗ ⚠ 💾 🟦 📂 ⏳ 🎨

9. USER INTERFACE FLOW
Startup Dialog Sequence:
1. File Selection: "Select PLMXML File"
2. Radio buttons to select the Step 1, 2 or 3
Completion Dialog:
Full Assembly Mode:
Import completed successfully!

Mode: Real JT files
Unique geometries: 150
Instances: 450
Materials: 45
Memory saved: 75.0%
Material Extraction Mode:
JT files scanned: 150
Unique materials: 45
Materials reused: 105
Total polygons processed: 12,456,789

All geometry has been removed.
Only materials remain in the document.

Log file: /path/to/plugin.log

10. HIERARCHY BUILDING
Node Structure:
Each hierarchy node contains:
node = {
    'id': instance_id,
    'name': part_name,
    'part_ref': part_ref,
    'quantity': int,
    'transform': [16 floats] or None,
    'jt_files': [{'file': str, 'transform': [16 floats]}],
    'user_data': {key: value},
    'children': [child_nodes]
}
User Data Preservation:
Extract all <UserValue> elements from instances:
for user_value in instance.findall('.//plm:UserValue', namespaces):
    title = user_value.get('title')
    value = user_value.get('value')
    # Add as Cinema 4D user data (DTYPE_STRING)
Recursive Building:
1. Create Null object with part name
2. Apply instance transform
3. Add user data
4. For each JT file: Create geometry/instance
5. Recursively process children
6. Insert under parent

11. CODE STRUCTURE
Main Classes:
MaterialPropertyInference:
* Static methods for inferring PBR properties
* Separate methods per material type
* Keyword-based detection
Cinema4DMaterialManager:
* Material creation and caching
* Deduplication with tolerance
* Two-pass matching system
PLMXMLParser:
* XML parsing with ElementTree
* Namespace handling
* Lookup table building (instances_by_id, parts_by_id)
* Material extraction
* Hierarchy extraction
GeometryInstanceManager:
* Geometry caching
* Instance creation
* Transform application
* Material application to geometry
* Statistics tracking
Cinema4DImporter:
* Hierarchy building
* User data addition
* JT geometry import
* Recursive structure creation
Logger:
* Dual output (console + file)
* Immediate flush
* Exception safe
Main Functions:
main():
* Initial dialogs
* Mode routing
import_full_assembly():
* Full geometry import workflow
extract_materials_only():
* Material extraction workflow
* Per-file processing loop
* Statistics and logging
count_polygons_in_document():
* Recursive polygon counting

12. PERFORMANCE OPTIMIZATIONS
1. Instance Reuse: Same JT file loaded once, referenced many times
2. Material Deduplication: Lenient tolerance reduces material count
3. Incremental Saving: Crash recovery without reprocessing
4. Lazy Loading: Only load what's needed
5. Memory Cleanup: Delete temp_doc after each file
6. Periodic UI Updates: c4d.EventAdd() every 5 files

13. COMPATIBILITY NOTES
Cinema 4D 2025 Specific:
* Some reflection layer constants changed
* Wrap all material property setting in try-except
* Use getattr(c4d, 'CONSTANT_NAME', None) for optional constants
* Node material system (if present) may differ
JT File Support:
* Relies on Cinema 4D's native JT import
* Uses MergeDocument() API
* Filters: c4d.SCENEFILTER_OBJECTS (no materials)

14. TESTING SCENARIOS
Test Cases:
1. Normal Import: All files present and valid
2. Missing Files: Some JT files don't exist
3. Corrupted Files: Invalid JT file format
4. Large Assembly: 500+ parts, memory handling
5. Repeated Geometry: Same part 100+ times (instance system)
6. Material Variations: Similar materials (deduplication)
7. Complex Hierarchy: 10+ nesting levels
8. Empty Materials: Parts with no material definitions
9. Crash Recovery: Resume from incremental save
10. Material Extraction: Full library creation without geometry

15. FINAL VALIDATION
Plugin is complete when:
* ✅ Both import modes work correctly
* ✅ Materials are created with proper PBR properties
* ✅ Materials are deduplicated effectively
* ✅ Geometry instances reference originals correctly
* ✅ Each instance can have unique transforms
* ✅ Transforms are correctly converted (row-major → column-major)
* ✅ Materials applied to geometry, not Nulls
* ✅ Missing/corrupted files use 10m cube placeholders
* ✅ Plugin never crashes, always completes
* ✅ Detailed logging to plugin.log
* ✅ Incremental saving works after each file
* ✅ Statistics are accurate (polygons, materials, progress)
* ✅ Console output is clear and informative
* ✅ User data preserved from PLMXML
* ✅ Memory usage optimized via instancing

16. EXAMPLE PLMXML SNIPPET
For testing, expect this structure:
<?xml version="1.0" encoding="ISO-8859-1"?>
<PLMXML xmlns="http://www.plmxml.org/Schemas/PLMXMLSchema"
        xmlns:dcx="http://www.smaragd.dcx.com/Schemas/Smaragd">
  <ProductDef>
    <InstanceGraph rootRefs="topID10028">
      <Instance id="ID10044" partRef="ID10025" quantity="1">
        <Transform>-1.0 0.00000013 -0.00000001 0 0.00000014 0.208 -0.978 0 -0.00000001 -0.978 -0.208 0 2.100 0.763 0.487 1</Transform>
      </Instance>
      <Part id="ID10025" name="A0009904738, 0002.003, SCREW">
        <Representation format="JT">
          <CompoundRep location="A0009904738_1.jt">
            <Transform>1.0 0.0 0.0 0.0 0.0 1.0 0.0 0.0 0.0 0.0 1.0 0.0 0 0 0 1.0</Transform>
            <dcx:TableAttribute definitionRef="j0MaterialDetailMatrix">
              <dcx:Row>
                <dcx:Column col="0" value="STAHL/STAHLGUSS"/>
                <dcx:Column col="1" value="EN 10269"/>
                <dcx:Column col="2" value="1.5525"/>
                <dcx:Column col="7" value="20MnB4"/>
              </dcx:Row>
            </dcx:TableAttribute>
          </CompoundRep>
        </Representation>
      </Part>
    </InstanceGraph>
  </ProductDef>
</PLMXML>

This specification completely defines the PLMXML Assembly Importer plugin in its current state (v2.7) and would allow full recreation from scratch.
