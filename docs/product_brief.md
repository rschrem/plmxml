# Product Brief
**Version:** 3.13
**Git Commit:** $Format:%H$

## Project Overview
Create a Cinema 4D 2025 Python plugin that imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation, intelligent material creation, geometry instancing optimization, and robust error handling. redshift is in cienma 4d 2025 not a plugin anymore. We never have to check wheter redshift is available. I provode examples on how to interacti with redshift.

## PLUGIN BASICS
Installation & Registration
* File Location: plugins/PLMXMLImporter/PLMXMLImporter.pyp
* Plugin ID: 1054321
* Plugin Name: "PLMXML Assembly Importer"
* Menu Location: Extensions → User Scripts → PLMXML Assembly Importer
* Version: 3.11
Dependencies
* Cinema 4D 2025 or later
* Python 3.9+ (built into Cinema 4D)
* Standard Cinema 4D Python API modules (c4d, xml.etree.ElementTree, os)

## FUNCTIONAL REQUIREMENTS

Initial step after user clicks ok in dialog: PLMXML Parsing
* Auto-detect PLMXML file from working directory (initialized to C4D document directory)
* Parse PLMXML files with full namespace handling (plm, dcx)
* Parse parts with JT file references and material properties
* Handle TableAttribute data with column-based material property extraction
* Support for multiple root references and complex hierarchies
* Process transform matrices with proper row-major to column-major conversion
* Extract user data from PLMXML and apply to Cinema 4D objects
* Extract instance graph with parent-child relationships

## Tree Modes of Operation

### Step 1: Extract materials Only
   * Parse PLMXML and extract all materials
   * Create redshift standard materials in Cinema 4D document
   * Infer PBR material properties from keywords in material data using enhanced algorithms
   * Support Metal, Plastic, Rubber, Wood, Glass, Leather and Sealant material types with improved accuracy
   * Create PBR-compatible materials with proper base color, metalness, roughness using enhanced PBR workflow setup
   * Enhanced German/English keyword matching for better material recognition
   * Remove all geometry after material extraction
   * Create complete material library with NO geometry
   * Ignore parent-child relationships from original PLMXML file
   * Reuse existing materials with same name in Cinema 4D document to avoid duplication

#### This is how in Cinema 2025 redshift material should eb created - needed for Step 1: Extract materials Only

def _create_redshift_openpbr_material(self, mat_name, props, doc):
    """Create a Redshift Standard Material (simplified version)"""
    
    # Create material
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat.SetName(mat_name)
    
    # Get node material and create graph
    nodeMaterial = mat.GetNodeMaterialReference()
    REDSHIFT_NODESPACE_ID = maxon.Id("com.redshift3d.redshift4c4d.class.nodespace")
    graph = nodeMaterial.CreateEmptyGraph(REDSHIFT_NODESPACE_ID)
    
    if graph.IsNullValue():
        raise RuntimeError(f"Failed to create Redshift graph")
    
    # Insert material first
    doc.InsertMaterial(mat)
    
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
        
        # Apply basic properties if provided
        if props and 'base_color' in props:
            colorPort = materialNode.GetInputs().FindChild(
                "com.redshift3d.redshift4c4d.nodes.core.standardmaterial.base_color")
            if colorPort:
                color = props['base_color']
                if isinstance(color, (list, tuple)) and len(color) >= 3:
                    colorPort.SetPortValue(maxon.Color(color[0], color[1], color[2]))
        
        transaction.Commit()
    
    c4d.EventAdd()
    return mat

### Step 2: Create Redshift Proxies Only
   * Focus only on creating proxy files, no assembly tree building, no creation of new materials
   * Ignore parent-child relationships from original PLMXML file
   * Provide tracking with detailed statistics: how many jt files were processed and how many we have in total
   * Parse PLMXML and iterate over each JT file and do the following 4 steos:
   1. Enure the object tree is empty
   2. Merge jt file onto current cinema4d document
   3. Replace materials of loaded geometry with materials with closest fitting material present in open Cinema 4D file
   4. Export loaded geometry as Redshift proxy (.rs file) using active document

#### This is how a redshict proxy is exported - needed for Step 2: Create Redshift Proxies Only

import c4d
import os

def export_redshift_proxy(objects, filename, doc):
    """Export selected objects as Redshift proxy"""
    
    if not objects:
        raise ValueError("No objects provided for export")
    
    # Select the objects for export
    doc.SetActiveObject(objects[0], c4d.SELECTION_NEW)
    for obj in objects[1:]:
        doc.SetActiveObject(obj, c4d.SELECTION_ADD)
    
    # Set up export settings
    export_settings = c4d.BaseContainer()
    
    # Export settings IDs (these may vary, check the SDK)
    export_settings[c4d.REDSHIFT_PROXY_EXPORT_OBJECTS] = 1  # 0=All, 1=Selected
    export_settings[c4d.REDSHIFT_PROXY_EXPORT_ORIGIN] = 0   # 0=World Origin
    export_settings[c4d.REDSHIFT_PROXY_EXPORT_ANIMATION] = 0  # 0=Current Frame
    export_settings[c4d.REDSHIFT_PROXY_EXPORT_COMPRESSION] = 1  # Enable compression
    export_settings[c4d.REDSHIFT_PROXY_EXPORT_ADD_TO_SCENE] = 1  # Add proxy to scene
    
    # Use SaveDocument to export the proxy
    # Format ID for Redshift Proxy is typically 1038655
    if not c4d.documents.SaveDocument(
        doc, 
        filename, 
        c4d.SAVEDOCUMENTFLAGS_NONE, 
        1038655  # Redshift Proxy format ID
    ):
        raise RuntimeError(f"Failed to export proxy to {filename}")
    
    print(f"Proxy exported successfully to: {filename}")
    return True

doc = c4d.documents.GetActiveDocument()
selected = doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_CHILDREN)
if selected:
    proxy_path = "/path/to/your/proxy.rs"
    export_redshift_proxy(selected, proxy_path, doc)

### Step 3: Build Assembly Tree Only
   * Create root node in the cinema 4d object with the name of the PLMXML file
   * Create a child nor to this root node named "Proxies". Viewport Visibility and Render Visibility is switched false for this node
      * For each JT file referenced in the PLMXML file:
      1. Create null object with same name directly under the just created "Proxies" node
      2. Check if .rs proxy file exists in working directory:
         * If .rs file exists: Create Redshift Proxy object as child with just filename (no path)
         * If .rs file doesn't exist: Create 5×5×5 meter cube as child
   * Create a child nor to this root node named "Instances". Viewport Visibility and Render Visibility is switched true for this node     * 
      * For each JT file referenced in the PLMXML file receate the original hierarchy using instance references to the redshift nodes created above below the Proxies node
      * Apply to the instance to  transformation that was found in the PLMXML file

#### This is how a node to load a redshift proxy is creates - needed for Step 3: Build assembly

import c4d

def create_redshift_proxy_object(doc, rs_file_path, name="RS_Proxy"):
    """Create a Redshift Proxy object and load a .rs file"""
    
    # Create Redshift Proxy object
    # The ID for Redshift Proxy object (check exact ID in your version)
    REDSHIFT_PROXY_OBJECT_ID = 1038649  # This ID may vary
    
    proxy_obj = c4d.BaseObject(REDSHIFT_PROXY_OBJECT_ID)
    if not proxy_obj:
        # Alternative: try using the constant if available
        proxy_obj = c4d.BaseObject(c4d.Orsproxyenvironment)
        if not proxy_obj:
            raise RuntimeError("Could not create Redshift Proxy object")
    
    proxy_obj.SetName(name)
    
    # Set the proxy file path
    # The parameter ID for the file path (check exact ID in your version)
    PROXY_FILE_PARAM_ID = 2001  # This may be something like c4d.REDSHIFT_PROXY_FILE
    proxy_obj[PROXY_FILE_PARAM_ID] = rs_file_path
    
    # Optional: Set display mode
    # 0 = Off, 1 = Bounding Box, 2 = Preview, etc.
    PROXY_DISPLAY_MODE_ID = 2002  # Check exact ID
    proxy_obj[PROXY_DISPLAY_MODE_ID] = 1  # Bounding Box
    
    # Optional: Set other parameters
    # proxy_obj[c4d.REDSHIFT_PROXY_DISPLAY_PERCENTAGE] = 10.0  # Display 10% of points
    
    # Insert into document
    doc.InsertObject(proxy_obj)
    
    # Update the scene
    c4d.EventAdd()
    
    return proxy_obj

doc = c4d.documents.GetActiveDocument()
doc.StartUndo()
proxy_path = "/path/to/your/model.rs"
proxy_obj = create_redshift_proxy_object(doc, proxy_path)
doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, proxy_obj)
doc.EndUndo()



### 3. NON-FUNCTIONAL REQUIREMENTS
Usability
* Provide clear progress feedback and meaningful error messages
* Support intuitive mode selection with three step-by-step radio buttons (Step 1: Extract materials, Step 2: Create Redshift Proxies, Step 3: Build assembly)
* Maintain familiar Cinema 4D UI conventions with OK button on right, Cancel button on left
* Auto-detect PLMXML file from working directory (initialized to C4D document directory using doc.GetDocumentPath() directly)
* No manual PLMXML file input field or browse button in UI - auto-detection only
* Dialog closes immediately when OK is pressed using threading to ensure proper closure before import process starts, preventing GUI blocking
* Enhanced threading implementation for improved UI responsiveness during import operations

Compatibility
* Full compatibility with Cinema 4D 2025 with Redshift plugin integration always available
* If no redshift is available: just notofy with an error message an terminate. There is no meaningful fallback possible,

## 4. TECHNICAL SPECIFICATIONS
Cinema 4D Integration
* Plugin ID: 1054321
* Registered as CommandData plugin
* Accessible through Extensions → User Scripts menu
* Uses standard Cinema 4D dialog interface
* Integrates with Cinema 4D's native JT import functionality

Redshift Integration
* Check for Redshift plugin availability (ID: 1036223)
* Create Redshift Proxy objects using proper plugin ID (1038649)
* Set proxy file paths using c4d.REDSHIFT_PROXY_FILE parameter
* Handle RS Proxy (*.rs) export command (ID: 1038650) for Cinema 4D 2025

File Handling
* All JT FIles are in the same folder as the cinema 4d file
* The PLMXML File is in the same folder as the cinema 4d file
* Simplified path handling using global working directory variable
* Check file existence before attempting to load

Logging and Debugging
* Create separate log files for each mode (importPlmxml_{Step}_log.txt) in the working directory
* Dual output to both console and file for debugging
* Immediate disk write for crash recovery
* UTF-8 encoding with proper formatting
* Comprehensive statistics tracking with polygon counts

## 5. ARCHITECTURE OVERVIEW
Component Structure
* PLMXMLParser: XML parsing with namespace handling and hierarchy extraction
* MaterialPropertyInference: Static methods for inferring PBR properties based on keywords
* Cinema4DMaterialManager: Material creation, caching, and deduplication system
* GeometryInstanceManager: Geometry caching and instance creation system
* Cinema4DImporter: Hierarchy building and user data management
* PLMXMLDialog: User interface with mode selection and file browsing
* Logger: Dual output logging system with immediate flush capability

Data Flow
1. User selects import mode through dialog (PLMXML file auto-detected from working directory, initialized to current C4D document directory)
2. Plugin parses PLMXML file to extract hierarchy and material data
3. Based on selected mode, process JT files accordingly:
   * Step 1: Extract materials Only: Extract materials only, process JT files directly without building hierarchy
   * Step 2: Create Redshift Proxies Only: Merge JT file with current document, replace materials with closest match of the already existing materials, export as .rs, process JT files directly without building hierarchy
   * Step 3: Build assembly: Create null hierarchy, check for .rs files, assembly structures only built in Step 3
4. Log detailed statistics and progress information

## 6. DEPLOYMENT
Installation
* Copy PLMXMLImporter.pyp to Cinema 4D plugins directory
* Plugin automatically registers with ID 1054321
* Access through Extensions → User Scripts → PLMXML Assembly Importer
* No additional installation steps required

## 7. MAINTENANCE
* Update Redshift plugin IDs as needed for new versions
* Maintain backward compatibility with existing workflows
* Document API changes and migration paths

Support
* Comprehensive logging for troubleshooting
* Clear error messages and recovery suggestions
* GitHub issue tracking for bug reports
* Documentation updates for new features
