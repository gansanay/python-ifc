# -*- coding: UTF-8 -*-

import re, copy
import time

class IfcSchema:
    SIMPLETYPES = ["INTEGER", "REAL", "STRING", "NUMBER", "LOGICAL", "BOOLEAN"]
    NO_ATTR = ["WHERE", "INVERSE", "WR2", "WR3", "WR4", "WR5", "UNIQUE", "DERIVE"]

    def __init__(self, filename):
        self.filename = filename
        self.file = open(self.filename)
        self.data = self.file.read()
        self.types = {}
        
        self.simpletypes = self.readSimpleTypes()
        self.types.update( self.simpletypes )
        
        self.aggregatedsimpletypes = self.readAggregatedSimpleTypes()
        self.types.update( self.aggregatedsimpletypes )
        
        self.enumtypes = self.readEnumTypes()
        self.types.update( self.enumtypes )
        
        self.selecttypes = self.readSelectTypes()
        self.types.update( self.selecttypes )
        
        self.definedtypes = self.readDefinedTypes()
        self.types.update( self.definedtypes )
        
        self.othertypes = self.readOtherTypes()
        self.types.update( self.othertypes )
        
        self.entities = self.readEntities()
        
        print "Parsed from schema %s: %s entities and %s types" % \
(self.filename, len(self.entities), len(self.types))

        self.file.close()

    def readSimpleTypes(self):
        """
        Parse all the possible Simple Types from the schema, 
        returns a dictionary Type Name -> Simple Type
        """
        types = {}
        for m in re.finditer("TYPE (.*) = (.*);", self.data):
            typename, typetype = m.groups() 
            if typetype in self.SIMPLETYPES:
                types[typename] = typetype
                
        return types
        
    def readAggregatedSimpleTypes(self):
        """
        Parse all the possible Aggregated Simple Types from the schema, 
        returns a dictionary Type Name -> String for aggregated type
        """
        types = {}
        # SETs
        for m in re.finditer("TYPE (\w*) = SET (.*);", self.data):
            typename, typetype = m.groups() 
            types[typename] = 'SET ' + typetype
        
        # BAGs
        for m in re.finditer("TYPE (\w*) = BAG (.*);", self.data):
            typename, typetype = m.groups() 
            types[typename] = 'BAG ' + typetype
        
        # LISTs
        for m in re.finditer("TYPE (\w*) = LIST (.*);", self.data):
            typename, typetype = m.groups() 
            types[typename] = 'LIST ' + typetype
        
        # ARRAYs
        for m in re.finditer("TYPE (\w*) = ARRAY (.*);", self.data):
            typename, typetype = m.groups() 
            types[typename] = 'ARRAY ' + typetype
            
        # STRING vectors
        for m in re.finditer("TYPE (\w*) = STRING\((.*);", self.data):
            typename, typetype = m.groups() 
            types[typename] = 'STRING(' + typetype
                
        return types       
        
    def readDefinedTypes(self):
        """
        Parse all the possible Defined Types from the schema, 
        returns a dictionary Type Name -> Defined Type
        """
        types = {}
        for m in re.finditer("TYPE (.*) = (.*);", self.data):
            typename, typetype = m.groups() 
            if typetype in self.types.keys():
                types[typename] = typetype
                
        return types  
        
    def readEnumTypes(self):
        """
        Parse all the possible Enumeration Types from the schema, 
        returns a dictionary Type Name -> List of values
        """
        types = {}
        for m in re.finditer("TYPE (\w*) = ENUMERATION OF\s*\(([\,\w\_\s]*)\);\s*END_TYPE;", self.data, re.DOTALL):
            typename, types_enum_string = m.groups() 
            typestring = re.sub('\s', '', types_enum_string)
            types[typename] = typestring.split(',')
                
        return types       

    def readSelectTypes(self):
        """
        Parse all the possible Select Types from the schema, 
        returns a dictionary Select Type Name -> List of Type Names
        """
        types = {}
        for m in re.finditer("TYPE (\w*) = SELECT\s*\(([\,\w\_\s]*)\);\s*END_TYPE;", self.data, re.DOTALL):
            typename, types_select_string = m.groups() 
            typestring = re.sub('\s', '', types_select_string)
            types[typename] = typestring.split(',')
                
        return types         

    def readOtherTypes(self):
        """
        Parse all possible types from the schema and keep unrecognized ones, 
        returns a dictionary Type Name -> String
        """
        types = {}
        for m in re.finditer("TYPE (\w*) = (.*);", self.data):
            typename, type_string = m.groups() 
            if typename not in self.types.keys():
                types[typename] = type_string
                
        return types

    def readEntities(self):
        """
        Parse all the possible entities from the schema,
        returns a dictionary of the form:
        { name: { 
            "supertype": supertype, 
            "attributes": [{ key: value }, ..]
        }}  
        """
        entities = {}
        
        # Regexes must be greedy to prevent matching outer entity and end_entity strings
        # Regexes have re.DOTALL to match newlines
        for m in re.finditer("ENTITY (.*?)END_ENTITY;", self.data, re.DOTALL):
            entity = {}
            raw_entity_str = m.groups()[0]

            entity["name"] = re.search("(.*?)[;|\s]", raw_entity_str).groups()[0].upper()
            
            is_supertype = re.search("SUPERTYPE", raw_entity_str) != None
            if is_supertype:
                supertypeofmatch = re.search(".*SUPERTYPE OF \((.*?)\)", raw_entity_str)
                is_abstract_supertype = re.search("ABSTRACT SUPERTYPE", raw_entity_str) != None
            
            is_subtype = re.search("SUBTYPE", raw_entity_str) != None

            if is_supertype and is_subtype:
                if is_abstract_supertype:
                    # abstract supertype of ... subtype of ... ;
                    match = re.search(".*ABSTRACT SUPERTYPE OF\s+\((.*?)\)\s+SUBTYPE OF\s+\((.*?)\);", raw_entity_str, re.DOTALL)
                    entity["isabstract"] = True
                    supertypeof,subtypeof = match.groups()
                    entity["supertype"] = subtypeof.upper()
                    supertypeof = re.sub('\s', '', supertypeof)
                    supertypeofmatch = re.search(".*\((.*?)\)", supertypeof, re.DOTALL)
                    subtypes = supertypeofmatch.groups()[0].upper().split(',')
                    entity["subtypes"] = subtypes
                else:
                    # supertype of ... subtype of ... ;
                    match = re.search(".*SUPERTYPE OF\s+\((.*?)\)\s+SUBTYPE OF\s+\((.*?)\);", raw_entity_str, re.DOTALL)
                    entity["isabstract"] = False
                    supertypeof,subtypeof = match.groups()
                    entity["supertype"] = subtypeof.upper()
                    supertypeof = re.sub('\s', '', supertypeof)
                    supertypeofmatch = re.search(".*\((.*?)\)", supertypeof, re.DOTALL)
                    subtypes = supertypeofmatch.groups()[0].upper().split(',')
                    entity["subtypes"] = subtypes
            elif is_subtype:
                # subtype of ... ;
                subtypeofmatch = re.search(".*SUBTYPE OF \((.*?)\);", raw_entity_str)
                entity["supertype"] = subtypeofmatch.groups()[0].upper() if subtypeofmatch else None

            # find the shortest string matched from the end of the entity type header to the
            # first occurence of a NO_ATTR string (when it occurs on a new line)
            inner_str = re.search(";(.*?)$", raw_entity_str, re.DOTALL).groups()[0]

            attrs_str = min([inner_str.partition("\r\n "+a)[0] for a in self.NO_ATTR])
            attrs = []
            for am in re.finditer("(\S*?) : (.*?);", attrs_str, re.DOTALL):
                name, attr_type = [s.replace("\r\n\t","") for s in am.groups()]
                attrs.append((name, attr_type))
            
            entity["attributes"] = attrs
            entities[entity["name"]] = entity
        

        return entities

    def getAttributes(self, name):
        """
        Get all attributes of an entity, including supertypes
        """
        ent = self.entities[name]

        attrs = []
        while ent != None:
            this_ent_attrs = copy.copy(ent["attributes"])
            this_ent_attrs.reverse()
            attrs.extend(this_ent_attrs)
            if not 'supertype' in ent:
                break
            ent = self.entities.get(ent["supertype"], None)

        attrs.reverse()
        return attrs
        

if __name__ == "__main__":
    t1 = time.time()
    schema = IfcSchema("IFC2X3_TC1.exp")
    t2 = time.time()
    print "Loading IFC2x3 TC1 schema took: %s s" % ((t2-t1))
    print "Parsed from IFC2x3 TC1 schema: %s entities and %s types \
[%s Simple Types, %s Aggregated Simple Types, %s Enumeration Types, %s Select Types, %s Defined Types, %s Other unrecognized types]" % \
(len(schema.entities), len(schema.types), \
len(schema.simpletypes), len(schema.aggregatedsimpletypes), len(schema.enumtypes), len(schema.selecttypes), len(schema.definedtypes), len(schema.othertypes))
    print "buildingSMART groups simple types, aggregated simple types \
and defined types under Defined Types, which makes %s Entities, %s Defined Types, %s \
Enumerations and %s Selects. There should be 653 Entities, 117 Defined Types, 164 \
Enumeration Types and 46 Select Types in the IFC2x3 TC1 schema.\n" % \
    (len(schema.entities),len(schema.simpletypes)+len(schema.aggregatedsimpletypes)+ \
    len(schema.definedtypes),len(schema.enumtypes),len(schema.selecttypes))
    assert len(schema.simpletypes)+len(schema.aggregatedsimpletypes)+ \
    len(schema.definedtypes) == 117
    assert len(schema.enumtypes) == 164
    assert len(schema.selecttypes) == 46
    assert len(schema.entities) == 653
    
    t1 = time.time()
    schema = IfcSchema("IFC4.exp")
    t2 = time.time()
    print "Loading IFC4 schema took: %s s" % ((t2-t1))
    print "Parsed from IFC4 schema: %s entities and %s types \
[%s Simple Types, %s Aggregated Simple Types, %s Enumeration Types, %s Select Types, %s Defined Types, %s Other unrecognized types]" % \
(len(schema.entities), len(schema.types), \
len(schema.simpletypes), len(schema.aggregatedsimpletypes), len(schema.enumtypes), len(schema.selecttypes), len(schema.definedtypes), len(schema.othertypes))
    print "buildingSMART groups simple types, aggregated simple types \
and defined types under Defined Types, which makes %s Entities, %s Defined Types, %s \
Enumerations and %s Selects. There should be 126 Defined Types, 206 \
Enumeration Types and 59 Select Types in the IFC4 schema." % \
    (len(schema.entities),len(schema.simpletypes)+len(schema.aggregatedsimpletypes)+len(schema.definedtypes),len(schema.enumtypes),len(schema.selecttypes)) 
    assert len(schema.simpletypes)+len(schema.aggregatedsimpletypes)+ \
    len(schema.definedtypes) == 126
    assert len(schema.enumtypes) == 206
    assert len(schema.selecttypes) == 59
    assert len(schema.entities) == 766
