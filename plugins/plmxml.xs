<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema" elementFormDefault="qualified">

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_CompoundRepTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Transform" minOccurs="1" maxOccurs="1"/>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}TableAttribute" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
    <xs:attribute name="format" type="xs:string" use="required"/>
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="location" type="xs:string" use="required"/>
    <xs:attribute name="name" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}CompoundRep" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_CompoundRepTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_InstanceTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Transform" minOccurs="1" maxOccurs="1"/>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="partRef" type="xs:string" use="required"/>
    <xs:attribute name="quantity" type="xs:integer" use="optional"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Instance" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_InstanceTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_InstanceGraphTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Instance" minOccurs="4308" maxOccurs="4308"/>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Part" minOccurs="3168" maxOccurs="3168"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}GeneralObject" minOccurs="138" maxOccurs="138"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Relation" minOccurs="2449" maxOccurs="2449"/>
    </xs:sequence>
    <xs:attribute name="rootRefs" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}InstanceGraph" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_InstanceGraphTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_PLMXMLTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}ProductDef" minOccurs="1" maxOccurs="1"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Header" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
    <xs:attribute name="author" type="xs:string" use="required"/>
    <xs:attribute name="date" type="xs:dateTime" use="required"/>
    <xs:attribute name="schemaVersion" type="xs:decimal" use="required"/>
    <xs:attribute name="time" type="xs:string" use="required"/>
    <xs:attribute name="{http://www.w3.org/2001/XMLSchema-instance}schemaLocation" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}PLMXML" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_PLMXMLTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_PartTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Representation" minOccurs="1" maxOccurs="1"/>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}TableAttribute" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="instanceRefs" type="xs:string" use="optional"/>
    <xs:attribute name="name" type="xs:string" use="required"/>
    <xs:attribute name="representationRefs" type="xs:string" use="optional"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Part" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_PartTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_ProductDefTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}InstanceGraph" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}ProductDef" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_ProductDefTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_RepresentationTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}CompoundRep" minOccurs="1" maxOccurs="89"/>
    </xs:sequence>
    <xs:attribute name="format" type="xs:string" use="required"/>
    <xs:attribute name="id" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Representation" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_RepresentationTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_TransformTypeType">
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:simpleContent>
      <xs:extension base="xs:string">
      </xs:extension>
    </xs:simpleContent>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}Transform" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_TransformTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_UserDataTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserValue" minOccurs="2" maxOccurs="32"/>
    </xs:sequence>
    <xs:attribute name="type" type="xs:string" use="optional"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_UserDataTypeType"/>

  <xs:complexType name="_http___www_plmxml_org_Schemas_PLMXMLSchema_UserValueTypeType">
    <xs:attribute name="title" type="xs:string" use="required"/>
    <xs:attribute name="value" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserValue" type="_http___www_plmxml_org_Schemas_PLMXMLSchema_UserValueTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_ColumnTypeType">
    <xs:attribute name="col" type="xs:integer" use="required"/>
    <xs:attribute name="value" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Column" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_ColumnTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_ContextTypeType">
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="refConfig" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Context" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_ContextTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_ContextsTypeType">
    <xs:sequence>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Context" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Contexts" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_ContextsTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_DefinitionsTypeType">
    <xs:sequence>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}TableAttributeDefinition" minOccurs="3" maxOccurs="3"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Definitions" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_DefinitionsTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_GeneralObjectTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
    </xs:sequence>
    <xs:attribute name="class" type="xs:string" use="required"/>
    <xs:attribute name="id" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}GeneralObject" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_GeneralObjectTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_HeaderTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Contexts" minOccurs="1" maxOccurs="1"/>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Definitions" minOccurs="1" maxOccurs="1"/>
    </xs:sequence>
    <xs:attribute name="author" type="xs:string" use="required"/>
    <xs:attribute name="creationDate" type="xs:dateTime" use="required"/>
    <xs:attribute name="definition" type="xs:string" use="required"/>
    <xs:attribute name="extensionVersion" type="xs:string" use="required"/>
    <xs:attribute name="smaragdVersion" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Header" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_HeaderTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_RelationTypeType">
    <xs:sequence>
      <xs:element name="{http://www.plmxml.org/Schemas/PLMXMLSchema}UserData" minOccurs="1" maxOccurs="2"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
    <xs:attribute name="relatedRefs" type="xs:string" use="required"/>
    <xs:attribute name="subType" type="xs:string" use="optional"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Relation" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_RelationTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_RowTypeType">
    <xs:sequence>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Column" minOccurs="2" maxOccurs="19"/>
    </xs:sequence>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Row" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_RowTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_TableAttributeTypeType">
    <xs:sequence>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Row" minOccurs="1" maxOccurs="48"/>
    </xs:sequence>
    <xs:attribute name="definitionRef" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}TableAttribute" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_TableAttributeTypeType"/>

  <xs:complexType name="_http___www_smaragd_dcx_com_Schemas_Smaragd_TableAttributeDefinitionTypeType">
    <xs:sequence>
      <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}Column" minOccurs="2" maxOccurs="19"/>
    </xs:sequence>
    <xs:attribute name="id" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:element name="{http://www.smaragd.dcx.com/Schemas/Smaragd}TableAttributeDefinition" type="_http___www_smaragd_dcx_com_Schemas_Smaragd_TableAttributeDefinitionTypeType"/>

</xs:schema>
