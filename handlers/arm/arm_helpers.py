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

from lark.indenter import Indenter

import arm_asl_parser

def normalizeCondition(f):
    if f:
        return {
                "mask": f[3:], 
                "equal": False
            } if f.startswith('!= ') else {
                "mask": f, 
                "equal": True
            }
    else:
        return {
                "mask": "_",
                "equal": False
            }

def maskToLength(mask):
    return len(mask)

def fieldNameEscape(name):
    return name.replace('<', '_', -1).replace('>', '_', -1).replace('[', '_', -1).replace(']', '_', -1).replace(':', '_', -1)


def createMaskComperand(mask):
    return (
                int(mask.replace('0', '1', -1).replace('x', '0', -1), 2), 
                int(mask.replace('x', '0', -1), 2)
            )
    
def convertInstructionBox(value, match):

    has_z_mask = value.find('Z') != -1 or value.find('z') != -1
    has_n_mask = value.find('N') != -1 or value.find('n') != -1
     
    if has_z_mask:
        value = value.replace('z', '0', -1).replace('Z', '0', -1)

    if has_n_mask:
        value = value.replace('n', '1', -1).replace('N', '1', -1)

    return {"mask": value, "equal": False if has_n_mask else True}


def createMaskCondition(tmp_name, value, match):
    
    if value.find('=') != -1:
        return value

    if value == '_':
        return ""
    
    if value.find('x') != -1:
        comperand = hex(int(value.replace('0', '1', -1).replace('x', '0', -1), 2))
        comp_value = hex(int(value.replace('x', '0', -1), 2))

        if int(comp_value, 16) == 0:
            if match:
                return "!(" + tmp_name + " & " + comperand + ")"
            else:
                return "(" + tmp_name + " & " + comperand + ")"
        else:
            if match:
                return "(" + tmp_name + " & " + comperand + ") == " + comp_value
            else:
                return "(" + tmp_name + " & " + comperand + ") != " + comp_value

    else:
        comperand = hex(int(value, 2))
        comp_value = comperand

        if int(value, 2) == 0:
            if match:
                return "!" + tmp_name + ""
            else:
                return "" + tmp_name + ""
        elif int(value, 2) == 1:
            if match:
                return "(" + tmp_name + " & " + comperand + ")"
            else:
                return "!(" + tmp_name + " & " + comperand + ")"
        else:
            if match:
                return "(" + tmp_name + " & " + comperand + ") == " + comp_value
            else:
                return "(" + tmp_name + " & " + comperand + ") != " + comp_value
            

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return list(obj)
        return json.JSONEncoder.default(self, obj)
    
class PythonIndenter(Indenter):
    NL_type = '_NEWLINE'
    OPEN_PAREN_types = ['LPAR', 'LSQB', 'LBRACE']
    CLOSE_PAREN_types = ['RPAR', 'RSQB', 'RBRACE']
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 4

with open("handlers/arm/pcode.lark", 'r') as grammar: 
    arm_grammar_string = grammar.read()
     
def escapeSpec(string_, list):
    esc_string = string_

    for el in list:
        esc_string = re.sub("(" + re.escape(el) + "([\r?\n]+[\t ]+)+)", el + " ", esc_string)

    return esc_string

def parseASLScript(parser, script):

    if "code" not in script:
        return {}

    try:
        # fixup_code - fix problems of the lexer ;) 
        fixup_code = script["code"]
        fixup_code = escapeSpec(fixup_code, ["AND","EOR","OR","DIV","REM","MOD","&&","||",">>","<<","*","+","-","^","&","|","%"])
        fixup_code = fixup_code + "\r\n"

        tree = parser.parse(fixup_code)
        generator = arm_asl_parser.ASLTreeGenerator()
        return generator.startParse(tree)
    except Exception as e:
        print(e, script["code"])

    return {}