import argparse
import glob
import json
import os
import re
import string
import sys
import xml.etree.cElementTree as ET
from collections import defaultdict
from itertools import takewhile

import arm_helpers

def readDiagramBox(reg):
    size = reg.attrib['form']

    fields = []

    for box in reg.findall('box'):
        width = int(box.attrib.get('width','1'))
        hibit = int(box.attrib['hibit'])
        offset = hibit - width + 1
        name = ""
        try:
            name = box.attrib['name']
        except:
            name = ""

        if len(name): 
            fields.append({
                    "name": box.attrib['name'],
                    "offset": offset, 
                    "width": width
                })

    return {
            "box_size": size, 
            "fields": fields
        }

def readDecodeBox(dec, columns):
    values = {}

    for box in dec.findall('box'):
        width = int(box.attrib.get('width','1'))
        hibit = int(box.attrib['hibit'])
        offset = hibit - width + 1
        values[offset] = arm_helpers.normalizeCondition(box.find('c').text) 
        values[offset]["name"] = box.attrib['name']
       
    result = []
    for item in columns:
        value = values.get(item["offset"])
        if value != None:     
            result.append(value)
            #if value["mask"].find('!') != -1:
                
                #for box in dec.findall('box'):
                #    width = int(box.attrib.get('width','1'))
                #    hibit = int(box.attrib['hibit'])
                #    offset = hibit - width + 1
                #    values[offset] = normalizeCondition(box.find('c').text)

    return result

def readIClass(iclass):
    label = iclass.attrib['iclass']
    allocated = iclass.attrib.get("unallocated", "0") == "0"
    predictable = iclass.attrib.get("unpredictable", "0") == "0"
    assert allocated or predictable

    return {
        "class_name": label, 
        "allocated": allocated, 
        "predictable": predictable
    }

def readGroup(groupname, group):
    
    diagram = readDiagramBox(group.find("regdiagram"))

    used_group_ops = []
   
    children = []

    for node in group.findall('node'):
        dec = readDecodeBox(node.find('decode'), diagram["fields"])
        
        for op in dec:
            used_group_ops.append((op["name"], arm_helpers.maskToLength(op["mask"])))
            
        if 'iclass' in node.attrib:
            
            new_iclass = readIClass(node)
            
            children.append({
                    "decode": dec, 
                    "is_group": False, 
                    "iclass": new_iclass
                })
            
        elif 'groupname' in node.attrib:
            new_groupname = node.attrib['groupname']
            (new_group, list_ops) = readGroup(new_groupname, node)
            
            used_group_ops += list_ops

            children.append({
                    "decode": dec, 
                    "is_group": True, 
                    "group": new_group
                })
            
        else:
            assert False

    return ({
            "groupname": groupname, 
            "regdiagram": diagram, 
            "children": children
        }, used_group_ops)


def readInstrName(dir, filename, encname):

    filename = dir+"/"+filename
    xml = ET.parse(filename)

    for ic in xml.findall(".//iclass"):
        decode = ic.find("regdiagram").attrib['psname']

        for enc in ic.findall("encoding"):
            if not encname or enc.attrib['name'] == encname:
                decode = decode.replace(".txt","")
                decode = decode.replace("/instrs","")
                decode = decode.replace("-","_")
                decode = decode.replace("/","_")
                return decode
            
    assert False

def readIClassTables(root):
    classes = {}
    decoders = []
    used_iclass_ops = []

    for child in root.iter():
        
        if child.tag == 'iclass_sect':

            fields = [ {
                            "name": box.attrib['name'], 
                            "offset": int(box.attrib['hibit']) - int(box.attrib.get('width', 1)) + 1, 
                            "width": int(box.attrib.get('width', 1))
                        } for box in child.findall('regdiagram/box') if 'name' in box.attrib ]
            
            for op in fields:
                used_iclass_ops.append((op["name"], op["width"]))
            
            tables = []
            for inst in child.findall('instructiontable'):

                iclass = inst.attrib['iclass']
                headers = [ r.text for r in inst.findall('thead/tr/th') if r.attrib['class'] == 'bitfields' ]
                headers = [ nm for nm in headers ] # workaround
                
                rows = []
                for r in inst.findall('tbody/tr'):
                    patterns = [ arm_helpers.normalizeCondition(d.text) for d in r.findall('td') if d.attrib['class'] == 'bitfield' ]
                    undef    = r.get('undef', '0') == '1'
                    unpred   = r.get('unpred', '0') == '1'
                    nop      = r.get('reserved_nop_hint', '0') == '1'
                    encname  = r.get('encname')
                    iformfile = "_" if undef or unpred or nop else r.attrib['iformfile'][:-4]

                    if iformfile not in decoders and iformfile != "_":
                        decoders.append(iformfile)

                    rows.append({
                            "patterns": patterns, 
                            "iformfile": iformfile, 
                            "encname": encname, 
                            "undef": undef, 
                            "unpred": unpred, 
                            "nop": nop
                        })

                tables.append({
                        "iclass": iclass, 
                        "headers": headers, 
                        "rows": rows
                    })
        
            assert len(tables) == 1
        
           # fields = [ (nm, hi, wd) for (nm, hi, wd) in fields ] # workaround
            classes[child.attrib['id']] = {
                "fields": fields, 
                "tables": tables[0]
            }
    
    return (classes, used_iclass_ops, decoders)

def readEncodingIndexFile(file):
    
    root = ET.parse(file)

    instuction_set = root.getroot().attrib['instructionset']

    (groups, group_list_ops) = readGroup(instuction_set, root.find('hierarchy')) 
    (classes, class_list_ops, decoders) = readIClassTables(root)

    group_list_ops_clean = {}
    class_list_ops_clean = {}

    for op in group_list_ops:
        if op[0] not in group_list_ops_clean:
            group_list_ops_clean[op[0]] = op[1]
        else:
            if group_list_ops_clean[op[0]] < op[1]:
                 group_list_ops_clean[op[0]] = op[1]

    for op in class_list_ops:
        if op[0] not in class_list_ops_clean:
            class_list_ops_clean[op[0]] = op[1]
        else:
            if class_list_ops_clean[op[0]] < op[1]:
                 class_list_ops_clean[op[0]] = op[1]

    return {
            "groups_op_list": group_list_ops_clean, 
            "groups" : groups, 
            "classes_op_list": class_list_ops_clean, 
            "classes": classes,
            "decoders": decoders
        }
