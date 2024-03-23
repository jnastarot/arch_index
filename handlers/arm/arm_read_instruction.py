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

alt_slice_syntax = False
demangle_instr = False

def readASL(ps):
    name = ps.attrib["name"]
    name = name.replace(".txt","")
    name = name.replace("/instrs","")
    name = name.replace("/Op_","/")
    chunk = ps.find("pstext")

    # list of things defined in this chunk
    defs = { x.attrib['link'] for x in chunk.findall('anchor') }

    # extract dependencies from hyperlinks in the XML
    deps = { x.attrib['link'] for x in chunk.findall('a') if not x.text.startswith("SEE") }

    # drop impl- prefixes in links
    deps = { re.sub('(impl-\w+\.)','',x) for x in deps }
    defs = { re.sub('(impl-\w+\.)','',x) for x in defs }

    # drop file references in links
    deps = { re.sub('([^#]+#)','',x) for x in deps }

    code = ET.tostring(chunk, method="text").decode().rstrip()+"\n"

    return {
            "name": name, 
            "code": code
        }

def readShared(shared_root):
    asl = {}
    names = set()

    for ps in shared_root.findall('.//ps_section/ps'):
        r = readASL(ps)

        # workaround: collect type definitions
        for m in re.finditer('''(?m)^(enumeration|type)\s+(\S+)''',r["code"]):
            names |= {m.group(2)}
        # workaround: collect variable definitions
        for m in re.finditer('''(?m)^(\S+)\s+([a-zA-Z_]\w+);''',r["code"]):
            if m.group(1) != "type":
                names |= {m.group(2)}
        # workaround: collect array definitions
        for m in re.finditer('''(?m)^array\s+(\S+)\s+([a-zA-Z_]\w+)''',r["code"]):
            v = m.group(2)+"["
            names |= {v}
        # workaround: collect variable accessors
        for m in re.finditer('''(?m)^(\w\S+)\s+([a-zA-Z_]\w+)\s*$''',r["code"]):
            names |= {m.group(2)}
        # workaround: collect array accessors
        for m in re.finditer('''(?m)^(\w\S+)\s+([a-zA-Z_]\w+)\[''',r["code"]):
            v = m.group(2)+"["
            names |= {v}

        asl[r["name"]] = r

    return (asl, names)

def sanitize(name):
    new_name = ""
    for c in name:
        if c not in string.ascii_letters and c not in string.digits:
            new_name += "_"
        else:
            new_name += c
    return new_name

# remove one level of indentation from code
def indent(code):
    return [ "    " + l for l in code ]

# remove one level of indentation from code
def unindent(code):
    cs = []
    for l in code:
        if l != "" and l[0:4] != "    ":
            print("Malformed conditional code '" + l[0:4] +"'")
            assert False
        cs.append(l[4:])
    return cs

def demangleExecuteASL(code):
    tops = None
    conditional = False
    decode = None
    if code[0].startswith("enumeration ") and code[1] == "":
        tops = code[0]
        code = code[2:]
    if code[0].startswith("if CurrentInstrSet() == InstrSet_A32 then"):
        first = code[0]
        code = code[1:]
        mid = code.index("else")
        code1 = unindent(code[:mid])
        code2= unindent(code[mid+1:])
        (tops1, conditional1, decode1, code1) = demangleExecuteASL(code1)
        (tops2, conditional2, decode2, code2) = demangleExecuteASL(code2)
        assert tops1 == None and tops2 == None
        assert conditional1 == conditional2
        code = [first] + indent(code1) + ["else"] + indent(code2)
        ([], conditional1, "\n".join([decode1 or "", decode2 or ""]), code)

    if code[0] == "if ConditionPassed() then":
        conditional = True
        code = code[1:] # delete first line
        code = unindent(code)

    if code[0] == "bits(128) result;":
        tmp = code[0]
        code[0] = code[1]
        code[1] = tmp
    elif len(code) >= 2 and code[1] == "EncodingSpecificOperations();":
        decode = code[0]
        code = code[1:]
    
    if code[0].startswith("EncodingSpecificOperations();"):    
        rest = code[0][29:].strip()
        if rest == "":
            code = code[1:]
        else:
            code[0] = rest

    return (tops, conditional, decode, code)

def readInstructionDecodeBox(box, fields, ignore_usename):

    width_field = box.attrib.get('width', None)
    width = 0

    if width_field == None or width_field == '':
        for c in box.findall('.//c'):
            width += int(c.attrib.get('colspan', '1'))
    else:
        width = int(box.attrib.get('width', None))

    hibit = int(box.attrib['hibit'])
    offset = hibit - width + 1
    name  = box.attrib.get('name', '_') if (ignore_usename or box.attrib.get('usename', '0') == '1') else '_'

    ignore = 'psbits' in box.attrib and box.attrib['psbits'] == 'x' * width
    consts = ''.join([ 'x'*int(c.attrib.get('colspan','1')) if c.text is None or ignore else c.text for c in box.findall('c') ])

    # if adjacent entries are two parts of same field, join them
    # e.g., imm8<7:1> and imm8<0> or opcode[5:2] and opcode[1:0]
    match = re.match('^(\w+)[<[]', name)
    if match:
        match_name = match.group(1)
        split = True
        if fields[-1]["split"] and fields[-1]["name"] == match_name:
            (hi1, lo1, _, _, c1) = fields.pop()
            assert(lo1 == hibit+1) # must be adjacent
            hibit = hi1
            consts = c1 + consts
    else:
        split = False

    if consts.startswith('!='): consts = 'x' * width

    fields.append({
            "width": width,
            "offset": offset,
            "name": name,
            "split": split,
            "consts": consts
        })


all_ops = []

def readInstructionAsmTemplate(template):

    print_defination = []

    for element in template:
        
        if element.tag == "text":
            print_defination.append(
                {
                    "type": "text",
                    "value": ET.tostring(element, method="text").decode().rstrip()    
                }
            )
        elif element.tag == "a":
            
            fields = []

            if "link" in element.attrib and element.attrib["link"] not in all_ops:
                all_ops.append(element.attrib["link"])

            if "hover" in element.attrib:
                fields = re.findall("field \"(.*)\"", element.attrib["hover"])            

            print_defination.append(
                {
                    "type": "element",
                    "value": ET.tostring(element, method="text").decode().rstrip(),
                    "category": element.attrib["link"] if "link" in element.attrib else "",
                    "description": element.attrib["hover"] if "hover" in element.attrib else "",
                    "fields": fields
                }
            )
        else:
            breakpoint()

    return print_defination

def readInstruction(xml):

    execs = xml.findall(".//pstext[@section='Execute']/..")
    posts = xml.findall(".//pstext[@section='Postdecode']/..")
    
    assert(len(posts) <= 1)
    assert(len(execs) <= 1)
    
    is_alias = True if not execs else False

    postdecode_asl = readASL(posts[0]) if posts else None

    if not is_alias:
        execute_asl = readASL(execs[0])
        # demangle execute code
        code = execute_asl["code"].splitlines()
        (top, conditional, decode, execute) = demangleExecuteASL(code)
        execute_asl["code"] = '\n'.join(execute)
    else:
        execute_asl = None

    classes = []
    for iclass in xml.findall('.//classes/iclass'):
        
        regdiagram = iclass.find('regdiagram')
        encodings = []

        for encoding in iclass.findall('.//encoding'):

            encoding_name = encoding.attrib["name"]

            if encoding_name == '': # mistake in the file
                continue

            mnemonic = encoding.find(".//docvars/docvar[@key='mnemonic']").attrib["value"]

            inst_class_doc = encoding.find(".//docvars/docvar[@key='instr-class']")
            

            fields = []
            for box in encoding.findall('box'):
                readInstructionDecodeBox(box, fields, True)

            inst_class = None
            if inst_class_doc != None:
                inst_class = inst_class_doc.attrib["value"]

            asmtemplate = encoding.find("asmtemplate")
            

            if is_alias:
                equivalent_to = encoding.find("equivalent_to")
                encodings.append(
                    {
                        "fields": fields,
                        "asm_template": readInstructionAsmTemplate(asmtemplate),
                        "alias_asmtemplate": readInstructionAsmTemplate(equivalent_to.find("asmtemplate")),
                        "aliascond": ET.tostring(equivalent_to.find("aliascond"), method="text").decode().rstrip(),
                        "encoding_name": encoding_name,
                        "mnemonic": mnemonic,
                        "inst_class": inst_class 
                    }
                )
            else:
                encodings.append(
                    {
                        "fields": fields,
                        "asm_template": readInstructionAsmTemplate(asmtemplate),
                        "encoding_name": encoding_name,
                        "mnemonic": mnemonic,
                        "inst_class": inst_class 
                    }
                )

        insn_set = "T16" if regdiagram.attrib['form'] == "16" else iclass.attrib['isa']

        fields = []
        for box in regdiagram.findall('box'):
            readInstructionDecodeBox(box, fields, False)

        if not is_alias:
            decode_asl = readASL(iclass.find('ps_section/ps'))
            if decode: decode_asl["code"] = decode +"\n"+ decode_asl["code"]
            name = decode_asl["name"] if insn_set in ["T16","T32","A32"] else regdiagram.attrib['psname']
        else:
            decode_asl = None
            name = regdiagram.attrib['psname']

        classes.append({
                "name": name, 
                "encodings": encodings,
                "insn_set": insn_set, 
                "fields": fields, 
                "decode_asl": decode_asl
            })

    return {
        "name": name,
        "type": xml.attrib["type"],
        "classes": classes,
        "postdecode_asl": postdecode_asl,
        "execute_asl": execute_asl
    }

def readFeatureFunctions(shared):

    feature_list = {}

    for elem in shared:
        matches = re.findall(r"boolean (.*)\(\)\n(.*)return IsFeatureImplemented\((.*)\)", shared[elem]["code"])

        if len(matches) == 0:
            continue
        
        for match in matches:
            feature_list[match[0]] = match[2] 

    return feature_list
