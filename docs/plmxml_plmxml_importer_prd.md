# PLMXML Assembly Importer Plugin - Product Requirements Document (PRD)

## 1. Executive Summary

**Product Name:** PLMXML Assembly Importer Plugin for Cinema 4D 2025
**Version:** 3.0
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

**Story 1: Full Assembly Import**
- As a Technical Artist, I want to import a complete PLMXML assembly file with full hierarchy preservation so that I can work with the complete Mercedes-Benz assembly in Cinema 4D.

**Story 2: Material Extraction**
- As a 3D Artist, I want to extract all materials from referenced JT files without importing geometry so that I can build a complete material library for my project.

**Story 3: Redshift Proxy Creation**
- As a Technical Artist, I want to create Redshift proxy files from my JT files so that I can efficiently work with large assemblies in Redshift.

**Story 4: Redshift Assembly Compilation**
- As a Technical Artist, I want to compile an assembly using Redshift proxies with preserved hierarchy so that I can achieve optimal performance with large assemblies.

### 3.3 Functional Requirements

#### 3.3.1 Import Modes
- **FR-001**: Plugin shall support three distinct operation modes: Material Extraction, Redshift Proxy Creation, and Assembly Compilation
- **FR-002**: Plugin shall present a radio button dialog at startup to select the operation mode
- **FR-003**: Plugin shall maintain separate execution paths for each mode

#### 3.3.2 Material System
- **FR-004**: Plugin shall infer material properties from keywords in material data
- **FR-005**: Plugin shall create PBR-compatible materials based on detected material types
- **FR-006**: Plugin shall implement material deduplication with tolerance-based matching
- **FR-007**: Plugin shall support Metal, Plastic, Rubber, Wood, Glass, and Sealant material types

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

### 8.2 Logging and Output
- The plugin creates separate log files for each mode: `importPlmxml_{Step}_log.txt`
  - Mode 1 (Material Extraction): `importPlmxml_1_log.txt`
  - Mode 2 (Create Redshift Proxies): `importPlmxml_2_log.txt`
  - Mode 3 (Compile Redshift Proxies): `importPlmxml_3_log.txt`
  - Mode 4 (Full Assembly): `importPlmxml_4_log.txt`
- All logs are created in the same directory as the selected PLMXML file
- Logs provide dual output to both console (Cinema 4D Command Line) and file for debugging