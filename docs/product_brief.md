# Product Brief
**Version:** 3.11
**Git Commit:** $Format:%H$

Complete Specification for PLMXML Assembly Importer Plugin for Cinema 4D 2025
Project Overview
Create a Cinema 4D 2025 Python plugin that imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation, intelligent material creation, geometry instancing optimization, and robust error handling.

## 1. PLUGIN BASICS
Installation & Registration
* File Location: plugins/PLMXMLImporter/PLMXMLImporter.pyp
* Plugin ID: 1054321
* Plugin Name: "PLMXML Assembly Importer"
* Menu Location: Extensions → User Scripts → PLMXML Assembly Importer
* Version: 3.11
Dependencies
* Cinema 4D 2025 or later
* Redshift for Cinema 4D (optional, for proxy modes)
* Python 3.9+ (built into Cinema 4D)
* Standard Cinema 4D Python API modules (c4d, xml.etree.ElementTree, os)
* Optional Redshift Python API modules (c4d.plugins, c4d.redshift)

## 2. FUNCTIONAL REQUIREMENTS
Core Import Capabilities
* Parse PLMXML files with full namespace handling (plm, dcx)
* Extract instance graph with parent-child relationships
* Parse parts with JT file references and material properties
* Handle TableAttribute data with column-based material property extraction
* Support for multiple root references and complex hierarchies
* Process transform matrices with proper row-major to column-major conversion
* Extract user data from PLMXML and apply to Cinema 4D objects

Material System
* Infer PBR material properties from keywords in material data using enhanced algorithms
* Support Metal, Plastic, Rubber, Wood, Glass, and Sealant material types with improved accuracy
* Create PBR-compatible materials with proper base color, metalness, roughness using enhanced PBR workflow setup
* Implement material deduplication with tolerance-based matching and intelligent grouping
* Apply materials to geometry objects, not null containers
* Support for user-defined material properties with fallback defaults
* Enhanced German/English keyword matching for better material recognition
* Advanced material property calculation with proper GGX distribution and fresnel modes
* Reuse existing materials with same name in Cinema 4D document to avoid duplication

Geometry Handling
* Load JT files using Cinema 4D's native JT import functionality
* Support for both single-object and multi-object JT files
* Implement geometry instancing to optimize memory usage
* Create 10m cube placeholders for missing or corrupted JT files
* Maintain proper parent-child relationships from original hierarchy
* Apply instance transforms correctly using SetMg() method

Import Modes
1. Step 1: Extract materials
   * Parse PLMXML and extract all materials
   * Create materials in Cinema 4D document
   * Remove all geometry after material extraction
   * Save document after each file processing
   * Create complete material library with NO geometry

2. Step 2: Create Redshift Proxies
   * Parse PLMXML and load each JT file into the active document (no temporary documents)
   * Replace loaded materials with closest fitting material in open Cinema 4D file using enhanced material inference
   * Export loaded geometry as Redshift proxy (.rs file) using active document
   * Focus only on creating proxy files, no assembly tree building
   * Progress tracking with detailed statistics
   * Enhanced material property inference with better German/English keyword matching
   * Improved PBR workflow setup with proper GGX distribution and fresnel modes
   * Advanced material grouping and deduplication to reduce material proliferation

3. Step 3: Build Assembly Tree Only
   * Auto-detect PLMXML file from working directory (initialized to C4D document directory)
   * Parse PLMXML and create null object hierarchy in _PLMXML_Geometries container
   * For each JT file, create null object with same name directly under _PLMXML_Geometries
   * Check if .rs proxy file exists in working directory
   * If .rs file exists: Create Redshift Proxy object as child with just filename (no path)
   * If .rs file doesn't exist: Create 5×5×5 meter cube as child
   * Recreate original hierarchy in Assembly root using instance references

## 3. NON-FUNCTIONAL REQUIREMENTS
Performance
* Efficient memory usage through geometry instancing
* Process 500+ parts efficiently with optimized performance
* Use incremental saving to prevent data loss during long processing
* Maintain low CPU usage during import operations

Reliability
* Never crash and always complete execution
* Continue processing when individual files fail to load
* Provide robust error handling with graceful fallbacks
* Implement comprehensive logging for troubleshooting

Usability
* Provide clear progress feedback and meaningful error messages
* Support intuitive mode selection with three step-by-step radio buttons (Step 1: Extract materials, Step 2: Create Redshift Proxies, Step 3: Build assembly)
* Maintain familiar Cinema 4D UI conventions with OK button on right, Cancel button on left
* Auto-detect PLMXML file from working directory (initialized to C4D document directory using doc.GetDocumentPath() directly)
* No manual PLMXML file input field or browse button in UI - auto-detection only
* Dialog closes immediately when OK is pressed using threading to ensure proper closure before import process starts, preventing GUI blocking

Compatibility
* Full compatibility with Cinema 4D 2025
* Support for Redshift plugin integration (when available)
* Handle different Cinema 4D material system APIs gracefully
* Maintain backward compatibility with existing workflows

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
* Gracefully fallback to placeholder cubes when Redshift unavailable

File Handling
* Support for JT file paths (all files accessed through working directory)
* Simplified path handling using global working directory variable
* Check file existence before attempting to load
* Create 10m cube placeholders for missing files
* Export Redshift proxies with proper .rs extensions

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
   * Step 1: Extract materials: Extract materials only, remove geometry, process JT files directly without building hierarchy
   * Step 2: Create Redshift Proxies: Load JT, replace materials, export as .rs, process JT files directly without building hierarchy
   * Step 3: Build assembly: Create null hierarchy, check for .rs files, assembly structures only built in Step 3
4. Log detailed statistics and progress information
5. Save document incrementally to prevent data loss

Error Handling
* Pre-flight checks for file existence and validity
* Exception handling for JT file loading operations
* Fallback strategies for missing files and failed operations
* Graceful degradation with placeholder cubes
* Comprehensive logging for troubleshooting and debugging

## 6. DEPLOYMENT
Installation
* Copy PLMXMLImporter.pyp to Cinema 4D plugins directory
* Plugin automatically registers with ID 1054321
* Access through Extensions → User Scripts → PLMXML Assembly Importer
* No additional installation steps required

Updates
* Replace PLMXMLImporter.pyp with updated version
* Restart Cinema 4D to pick up changes
* Maintain backward compatibility with existing documents
* Preserve user preferences and settings

## 7. MAINTENANCE
Compatibility
* Regular testing with new Cinema 4D versions
* Update Redshift plugin IDs as needed for new versions
* Maintain backward compatibility with existing workflows
* Document API changes and migration paths

Support
* Comprehensive logging for troubleshooting
* Clear error messages and recovery suggestions
* GitHub issue tracking for bug reports
* Documentation updates for new features