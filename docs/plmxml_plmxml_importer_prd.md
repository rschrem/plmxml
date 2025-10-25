# PLMXML Assembly Importer Plugin - Product Requirements Document (PRD)

## 1. Executive Summary

**Product Name:** PLMXML Assembly Importer Plugin for Cinema 4D 2025
**Version:** 3.11
**Project ID:** 1054321
**Project Owner:** [Your Name]
**Date:** [Current Date]

### 1.1 Product Overview
The PLMXML Assembly Importer is a Cinema 4D 2025 Python plugin that imports Mercedes-Benz PLMXML assembly files with full hierarchy preservation, intelligent material creation, geometry instancing optimization, and robust error handling.

### 1.2 Vision Statement
Create a robust, efficient, and reliable solution for importing complex PLMXML assembly files into Cinema 4D, supporting Mercedes-Benz's 3D visualization workflow with advanced material handling, memory optimization, and error resilience.

### 1.3 Success Criteria
- ✅ Successfully import complex Mercedes-Benz PLMXML assembly files
- ✅ Maintain full hierarchy structure during import
- ✅ Create intelligent materials based on keyword detection
- ✅ Optimize memory usage through geometry instancing
- ✅ Provide robust error handling with fallback mechanisms
- ✅ Support for three distinct operation modes

## 2. Product Goals and Objectives

### 2.1 Primary Goals
1. **Hierarchy Preservation**: Import full assembly hierarchy with proper parent-child relationships
2. **Material System**: Automatically create and assign appropriate materials based on PLMXML data
3. **Memory Optimization**: Use instancing to minimize memory usage for repeated parts
4. **Error Resilience**: Continue processing when files are missing or corrupted

### 2.2 Secondary Goals
1. **Performance**: Process large assemblies efficiently with minimal memory footprint
2. **User Experience**: Provide clear progress feedback and meaningful error messages
3. **Compatibility**: Support Cinema 4D 2025 and maintain compatibility with existing workflows
4. **Extensibility**: Design architecture that allows for future enhancements

## 3. User Stories and Requirements

### 3.1 User Roles
- **Technical Artist**: Uses the plugin to import Mercedes-Benz assemblies for visualization
- **3D Artist**: Works with imported assemblies for scenes and renders
- **Pipeline Developer**: May need to integrate or customize the plugin

### 3.2 User Stories

**Story 1: Material Extraction Only (Step 1)**
- As a 3D Artist, I want to extract all materials from referenced JT files without importing geometry so that I can build a complete material library for my project.

**Story 2: Create Redshift Proxies Only (Step 2)**
- As a Technical Artist, I want to create Redshift proxy files from my JT files so that I can efficiently work with large assemblies in Redshift.

**Story 3: Build Assembly Tree Only (Step 3)**
- As a Technical Artist, I want to compile an assembly using existing Redshift proxies with preserved hierarchy so that I can achieve optimal performance with large assemblies.

### 3.3 Functional Requirements

#### 3.3.1 Import Modes
- **FR-001**: Plugin shall support three distinct operation modes: Material Extraction (Step 1), Redshift Proxy Creation (Step 2), and Build Assembly Tree Only (Step 3)
- **FR-002**: Plugin shall present a radio button dialog at startup to select the operation mode
- **FR-003**: Plugin shall maintain separate execution paths for each mode with specific functionality

#### 3.3.2 Material System
- **FR-004**: Plugin shall infer material properties from keywords in material data
- **FR-005**: Plugin shall create PBR-compatible materials based on detected material types
- **FR-006**: Plugin shall implement material deduplication with tolerance-based matching
- **FR-007**: Plugin shall support Metal, Plastic, Rubber, Wood, Glass, and Sealant material types

#### 3.3.3 Redshift Proxy Compilation (Step 3)
- **FR-008**: Plugin shall create a hidden container named `_PLMXML_Geometries` to hold all geometry references
- **FR-009**: Plugin shall create null objects named after each JT file directly under `_PLMXML_Geometries`
- **FR-010**: Plugin shall check for existence of `.rs` proxy files in the same directory as the PLMXML file
- **FR-011**: Plugin shall create Redshift Proxy objects as children of JT null objects when `.rs` files exist
- **FR-012**: Plugin shall use only the filename (no path) in Redshift Proxy object `REDSHIFT_PROXY_PATH` parameter
- **FR-013**: Plugin shall create 5×5×5 meter placeholder cubes as children when `.rs` files don't exist
- **FR-014**: Plugin shall recreate the original PLMXML hierarchy in the Assembly root
- **FR-015**: Plugin shall use instance references to the appropriate Null Object nodes in `_PLMXML_Geometries` tree
- **FR-016**: Plugin shall maintain parent-child relationships from the original PLMXML structure
- **FR-017**: Plugin uses global working directory for all file operations, eliminating need for complex path resolution

#### 3.3.3 Geometry Handling
- **FR-008**: Plugin shall implement geometry instancing to optimize memory usage
- **FR-009**: Plugin shall preserve original hierarchy structure in the Cinema 4D scene
- **FR-010**: Plugin shall handle both single-object and multi-object JT files

#### 3.3.4 Transform System
- **FR-011**: Plugin shall correctly convert PLMXML's row-major matrices to Cinema 4D's column-major matrices
- **FR-012**: Plugin shall apply transforms at both instance and geometry levels

#### 3.3.5 Error Handling
- **FR-013**: Plugin shall check for JT file existence before attempting to load
- **FR-014**: Plugin shall create 10m cube placeholders for missing files
- **FR-015**: Plugin shall continue processing when individual files fail to load

#### 3.3.6 Logging and Statistics
- **FR-016**: Plugin shall maintain a detailed log file with comprehensive statistics
- **FR-017**: Plugin shall provide real-time progress feedback to the user
- **FR-018**: Plugin shall track polygon count, material count, and processing statistics

### 3.4 Non-Functional Requirements

#### 3.4.1 Performance
- **NFR-001**: Plugin shall process 500+ parts efficiently with optimized memory usage
- **NFR-002**: Plugin shall use incremental saving to prevent data loss during long processing

#### 3.4.2 Compatibility
- **NFR-003**: Plugin shall be compatible with Cinema 4D 2025
- **NFR-004**: Plugin shall handle different Cinema 4D material system APIs gracefully

#### 3.4.3 Reliability
- **NFR-005**: Plugin shall never crash and always complete execution
- **NFR-006**: Plugin shall implement fallback strategies for all critical operations

## 4. Technical Architecture Overview

### 4.1 Core Components
1. **MaterialPropertyInference**: Static methods for inferring PBR properties based on keywords
2. **Cinema4DMaterialManager**: Material creation, caching, and deduplication system
3. **PLMXMLParser**: XML parsing with namespace handling and hierarchy extraction
4. **GeometryInstanceManager**: Geometry caching and instance creation system
5. **Cinema4DImporter**: Hierarchy building and user data management
6. **Logger**: Dual output logging system

### 4.2 Data Flow
1. Parse PLMXML file to extract hierarchy and material definitions
2. Process each mode-specific workflow requirement
3. Load and process referenced JT files
4. Create materials based on extracted properties
5. Build geometry hierarchy with proper transforms
6. Apply instancing for memory optimization

## 5. Success Metrics

### 5.1 Product Metrics
- Processing time for large assemblies (target: < 30 minutes for 500+ parts)
- Memory usage optimization (target: 75% reduction through instancing)
- Material accuracy (target: > 95% correct material type detection)
- Success rate (target: 100% completion without crashes)

### 5.2 User Experience Metrics
- Time to first successful import (target: < 5 minutes)
- Learning curve (target: < 1 hour to understand all features)
- Error recovery rate (target: 100% for missing files)

## 6. Constraints and Assumptions

### 6.1 Technical Constraints
- Must be implemented in Python as a Cinema 4D plugin
- Must support Cinema 4D 2025 specifically
- Must use Cinema 4D's native JT import functionality
- Must not exceed 8GB memory usage for large assemblies

### 6.2 Business Constraints
- Deadline: To be determined based on project schedule
- Budget: Internal development resource allocation
- Dependencies: Cinema 4D installation, Redshift (for proxy mode)

### 6.3 Risk Assessment
- **High Risk**: JT file format compatibility issues
- **Medium Risk**: Large assembly performance optimization
- **Low Risk**: Cinema 4D API changes in future versions

## 7. Development Approach

### 7.1 Project Level
Based on the complexity of the requirements, this is a Level 3-4 project requiring:
- Complete architecture planning
- Comprehensive technical specifications
- Iterative development with validation

### 7.2 Implementation Strategy
1. Core parsing and hierarchy building
2. Material system implementation
3. Instance optimization system
4. User interface and workflow implementation
5. Comprehensive testing and validation

## 8. Technical Implementation Notes

### 8.1 Cinema 4D 2025 Specifics
- Redshift proxy export: In Cinema 4D 2025 (needs to be checked in future versions of Cinema 4D as this might change), command ID `1038650` saves the currently active document as a Redshift proxy: `c4d.CallCommand(1038650) # RS Proxy (*.rs)`
- This command must be called with the document containing only the object to be exported as the active document
- The command saves the file to the user's default location, so the proxy path needs to be set separately
- Redshift Proxy Object plugin ID: `1038649` (com.redshift3d.redshift4c4d.proxyloader)
- Redshift plugin ID: `1036223` (common Redshift plugin ID)
- RS Proxy (*.rs) export command: `1038650` in Cinema 4D 2025

### 8.2 Logging and Output
- The plugin creates separate log files for each mode: `importPlmxml_{Step}_log.txt`
  - Mode 1 (Material Extraction): `importPlmxml_1_log.txt`
  - Mode 2 (Create Redshift Proxies): `importPlmxml_2_log.txt`
  - Mode 3 (Build Assembly Tree Only): `importPlmxml_3_log.txt`
- All logs are created in the same directory as the selected PLMXML file
- Logs provide dual output to both console (Cinema 4D Command Line) and file for debugging

### 8.3 Material System Enhancements
- **Material Reuse**: Check if materials with matching names already exist in the active document before creating new ones
- **Property-Based Matching**: Compare material properties (base color, roughness, metalness) to identify similar materials for reuse
- **Material Verification**: Confirm that created materials are properly inserted into the document
- **Deduplication**: Enhanced material deduplication with tolerance-based matching system
- **Keyword Detection**: Dynamic detection of new material keywords not in predefined lists
- **Keyword Logging**: Log new material keywords as they are detected and report all new keywords in final statistics

### 8.4 API Compatibility Improvements
- **User Data API**: Proper handling of user data using AddUserData() instead of invalid GetUserDatDescription() method
- **Animation Parameter**: Use numeric value 0 instead of invalid c4d.DESC_ANIM_OFF constant
- **Reflection Layers**: Proper setup of reflection layers without attempting to clear existing ones using invalid MATERIAL_REFLECTION_LAYER constant
- **Cinema 4D API**: Compatibility with Cinema 4D 2025 API requirements

### 8.5 Dialog and UI Enhancements
- **Standard Dialog IDs**: Use c4d.DLG_OK and c4d.DLG_CANCEL for proper button handling
- **Modal Dialog Behavior**: Correct handling of modal dialogs with proper context
- **UI Refresh**: Call c4d.EventAdd() after import completion to refresh Cinema 4D interface
- **Button Management**: Proper ID management to prevent conflicts between buttons and other controls
- **Step-by-Step Workflow**: Three mutually exclusive radio buttons for Step 1 (Extract materials), Step 2 (Create Redshift Proxies), Step 3 (Build assembly)
- **Auto-Detection**: PLMXML file auto-detected from same directory as current C4D document (no manual file selection)
- **Directory Resolution**: Plugin uses a global working directory initialized to the C4D file directory; all file operations (PLMXML, JT, RS proxies, logs) occur in this single working directory
- **Button Order**: OK on the right, Cancel on the left (swapped from default to follow common UI patterns)
- **No File Input Field**: Removed PLMXML file input field and browse button from the dialog
- **Dialog Closure**: Dialog closes immediately when OK is pressed using threading to ensure proper closure before import process starts, preventing GUI blocking

### 8.6 Error Handling and Robustness
- **API Error Prevention**: Handle Cinema 4D API incompatibilities gracefully
- **Material Verification**: Verify that materials are properly added to the document
- **Fallback Strategies**: Multiple strategies for material reuse and creation
- **Comprehensive Logging**: Detailed logging for troubleshooting and debugging

### 8.8 Redshift Proxy Compilation Workflow (Step 3: Build Assembly Tree Only Implementation)
- **Working Directory Approach**: All files (.plmxml, .stpx, .c4d, .jt, .rs, logs) are in the working directory using global working directory variable
- **Hidden Geometry Container**: Create `_PLMXML_Geometries` null object to contain all geometry references
- **Per-JT File Nodes**: Create null objects named after each JT file directly under `_PLMXML_Geometries`
- **Conditional Proxy Creation**: Check if `.rs` proxy files exist in working directory
- **Redshift Proxy Objects**: Create Redshift Proxy objects using proper plugin ID (1038649) with just filename (no path)
- **Placeholder Cubes**: Create 5×5×5 meter cubes as fallback when `.rs` files are missing
- **Assembly Recreation**: Recreate original hierarchy using instance references to `_PLMXML_Geometries` nodes
- **Simplified File Operations**: No complex path resolution needed due to global working directory implementation
- **Instance Management**: Maintain transforms and relationships through instance references
- **Document Structure**: Preserve parent-child relationships from original PLMXML structure
- **Proper Redshift API**: Use `c4d.REDSHIFT_PROXY_FILE` parameter for proper proxy file assignment
- **Redshift Plugin ID**: Use 1038649 (com.redshift3d.redshift4c4d.proxyloader) for proper plugin identification

### 8.9 Redshift Proxy Creation Workflow (Step 2: Create Redshift Proxies Implementation)
- **No Temporary Documents**: In Step 2, use the currently active document instead of creating temporary documents for JT loading and proxy export
- **JT File Processing**: Load JT files directly into the active document, clearing any existing objects first
- **Material Replacement**: Replace materials with closest matching materials from the active Cinema 4D document
- **Proxy Output**: Create .rs proxy files using the known working format ID 1038650
- **Simplified Export**: Remove all fallback methods and use only the proven working format for Redshift proxy export
- **Assembly-Free Processing**: Step 2 focuses solely on creating proxy files without building any assembly object tree
- **Memory Management**: No temporary documents to clean up since using active document directly

### 8.10 Enhanced Material Handling Improvements
- **Advanced Material Property Inference**: Improved keyword matching algorithms for both German and English material terms with better accuracy
- **Enhanced PBR Workflow Setup**: Proper GGX distribution configuration and correct fresnel mode handling (conductor vs. dielectric)
- **Better Material Creation**: Robust material creation with proper reflection layer setup and parameter configuration
- **Intelligent Material Grouping**: Advanced material deduplication with lenient tolerance matching to reduce material proliferation
- **Improved Material Properties**: More accurate base colors, roughness values, and other PBR properties based on material type
- **Material Reuse**: Check for existing materials with the same name in the Cinema 4D document and reuse them instead of creating duplicates
### 8.11 Step 1 and Step 2 Implementation Improvements
- **Step 1 Assembly-Free Processing**: Step 1 (Material Extraction Only) now processes all JT files directly without building any assembly tree structure
- **Step 2 Assembly-Free Processing**: Step 2 (Create Redshift Proxies Only) now processes all JT files directly without building any assembly tree structure
- **Active Document Usage**: Both Steps 1 and 2 work exclusively with the currently active Cinema 4D document
- **No Temporary Documents**: Eliminated all temporary document creation in Steps 1 and 2 to improve memory usage
- **Direct File Processing**: Both steps iterate through all JT files directly and process them without hierarchy traversal
- **Assembly Building Isolation**: Assembly structures are only built in Step 3 (Compile Assembly Tree Only mode) as intended

### 8.10 Version Information
- **Current Version**: 3.1 (updated from initial 3.0)
- **Major Improvements**: Material verification and reuse, keyword detection, API compatibility fixes, dialog improvements, Redshift proxy compilation workflow
- **Version 3.2 Updates**: Step-by-step workflow with 3 modes (Material Extraction Only, Create Redshift Proxies Only, Build Assembly Tree Only), auto-detection of PLMXML file from C4D document directory, updated UI with swapped OK/Cancel buttons, immediate dialog closure on OK press
- **Version 3.3 Updates**: Fixed path resolution to correctly check directory containing C4D file for .plmxml files (not parent directory)
- **Version 3.4 Updates**: Removed PLMXML file input field and browse button from dialog, swapped OK and Cancel button positions to follow standard UI patterns, auto-detection of PLMXML file from current C4D file directory
- **Version 3.5 Updates**: Renamed UI options to Step 1: Extract materials, Step 2: Create Redshift Proxies, Step 3: Build assembly for clarity; removed Full Assembly Import option
- **Version 3.6 Updates**: Implemented global working directory variable for simplified file operations; all files (PLMXML, JT, RS proxies, logs) now use single directory approach eliminating complex path arithmetic
- **Version 3.7 Updates**: Enhanced dialog closure using threading to ensure proper closure before import process starts; simplified Redshift proxy export to use only working format ID 1038650; ensure temporary documents are empty before loading JT files in Step 2 to prevent conflicts
- **Version 3.8 Updates**: Step 2 no longer builds assembly tree - focuses solely on creating Redshift proxy files; removes all temporary document usage in Step 2, using active document instead; implements material replacement using active document materials
- **Version 3.9 Updates**: Improved material property inference algorithms with better German/English keyword matching; enhanced material creation with proper PBR workflow setup; better material grouping and deduplication with lenient tolerance matching; updated Cinema 4D standard material creation with GGX distribution and proper fresnel modes; added material reuse functionality to check for existing materials with same name in document
- **Version 3.10 Updates**: Enhanced Step 1 material extraction to check for existing materials with same name in Cinema 4D document and reuse them instead of creating duplicates; improved material deduplication to reduce material proliferation in complex assemblies; updated both Steps 1 and 2 to work exclusively with active document and avoid assembly tree creation entirely; Steps 1 and 2 now process all JT files directly without building any assembly hierarchy; assembly structures are only built in Step 3 (compile_redshift_proxies mode)
- **Version 3.11 Updates**: Fixed Step 2 to implement missing _process_all_jt_files_for_proxy_creation method that was causing AttributeError; enhanced progress tracking in Steps 1 and 2 with detailed file processing information; improved error handling with graceful fallbacks; fixed method signature inconsistencies; added missing method implementation for Redshift proxy creation workflow; ensured proper material reuse tracking in Cinema 4D document