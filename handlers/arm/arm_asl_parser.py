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

from lark import Lark, Transformer, v_args

import lark

import arm_helpers

test_string = """
CheckFPAdvSIMDEnabled64();
bits(datasize) operand1 = V[n, datasize];
bits(datasize) operand2 = V[m, datasize];
bits(datasize) result;

result = V[d, datasize];
for e = 0 to elements-1
    integer res = 0;
    integer element1, element2;
    for i = 0 to 3
        if signed then
            element1 = SInt(Elem[operand1, 4*e+i, esize DIV 4]);
            element2 = SInt(Elem[operand2, 4*e+i, esize DIV 4]);
        else
            element1 = UInt(Elem[operand1, 4*e+i, esize DIV 4]);
            element2 = UInt(Elem[operand2, 4*e+i, esize DIV 4]);
        res = res + element1 * element2;
    Elem[result, e, esize] = Elem[result, e, esize] + res;
V[d, datasize] = result;
integer d = UInt(Rd);
integer n = UInt(Rn);

if immh == '0000' then SEE(asimdimm);
if immh IN {'000x'} || (immh IN {'001x'} && !IsFeatureImplemented(FEAT_FP16)) then UNDEFINED;
if immh<3>:Q == '10' then UNDEFINED;
constant integer esize = if immh IN {'1xxx'} then 64 else if immh IN {'01xx'} then 32 else 16;
constant integer datasize = 64 << UInt(Q);
integer elements = datasize DIV esize;

integer fracbits = (esize * 2) - UInt(immh:immb);
boolean unsigned = (U == '1');
FPRounding rounding = FPRounding_ZERO;

integer d = UInt(Rd);
integer n = UInt(Rn);

if immh == '0000' then SEE(asimdimm);
if immh<3> == '1' then UNDEFINED;
constant integer esize = 8 << HighestSetBit(immh);
constant integer datasize = 64;
integer part = UInt(Q);
integer elements = datasize DIV esize;

integer shift = (2 * esize) - UInt(immh:immb);
boolean round = (op == '1');
boolean unsigned = (U == '1');

CheckStreamingSVEEnabled();
constant integer VL = CurrentVL;
constant integer elements = VL DIV 16;
array [0..3] of bits(VL) results;

for r = 0 to nreg-1
    bits(VL) operand1 = Z[dn+r, VL];
    bits(VL) operand2 = Z[m, VL];
    for e = 0 to elements-1
        bits(16) element1 = Elem[operand1, e, 16];
        bits(16) element2 = Elem[operand2, e, 16];
        Elem[results[r], e, 16] = BFMinNum(element1, element2, FPCR);

for r = 0 to nreg-1
    Z[dn+r, VL] = results[r];

if Rm == '1101' then SEE "encoding T1";
d = 13;  m = UInt(Rm);  setflags = FALSE;
(shift_t, shift_n) = (SRType_LSL, 0);

TestFunction(arg1, awcd, 43)
if !HaveSVE() && !HaveSME() then UNDEFINED;
constant integer esize = 8 << UInt(size);
integer g = UInt(Pg);
integer dn = UInt(Rdn);
integer m = UInt(Zm);
constant integer csize = if esize < 1 then 32 else 64;
boolean isBefore = FALSE;
if !HaveSVE2() && !HaveSME() then UNDEFINED;
if size IN {'0x'} then UNDEFINED;
constant integer esize = 8 << UInt(size);
integer n = UInt(Zn);
integer m = UInt(Zm);
integer da = UInt(Zda);
integer sel_a = UInt(rot<0>);
integer sel_b = UInt(NOT(rot<0>));
boolean sub_i = (rot<0> == rot<1>);

SystemHintOp op;

if CRm:op2 == '0100 xx0' then
    op = SystemHintOp_BTI;
    // Check branch target compatibility between BTI instruction and PSTATE.BTYPE
    SetBTypeCompatible(BTypeCompatible_BTI(op2<2:1>));
else
    EndOfInstruction();
case CRm:op2 of
    when '0011 100'    // AUTIAZ
        d = 30;
        n = 31;
    when '0011 101'    // AUTIASP
        d = 30;
        source_is_sp = TRUE;
    when '0001 100'    // AUTIA1716
        d = 17;
        n = 16;
    when '0001 000' SEE "PACIA";
    when '0001 010' SEE "PACIB";
    when '0001 110' SEE "AUTIB";
    when '0011 00x' SEE "PACIA";
    when '0011 01x' SEE "PACIB";
    when '0011 11x' SEE "AUTIB";
    when '0000 111' SEE "XPACLRI";
    otherwise SEE "HINT";
(imm, -) = DecodeBitMasks(N, imms, immr, TRUE, datasize);

SEE "PACIA";
bits(32) vbase = X[v, 32];
while SInt(stagecpysize) != 0 do
    // IMP DEF selection of the block size that is worked on. While many
    // implementations might make this constant, that is not assumed.
    constant integer B = CPYSizeChoice(toaddress, fromaddress, cpysize);
    assert B <= -1 * SInt(stagecpysize);

    readdata<B*8-1:0> = Mem[fromaddress+cpysize, B, raccdesc];
    Mem[toaddress+cpysize, B, waccdesc] = readdata<B*8-1:0>;

    cpysize = cpysize + B;
    stagecpysize = stagecpysize + B;

    if stage != MOPSStage_Prologue then
        X[n, 64] = cpysize;

CheckStreamingSVEAndZAEnabled();
constant integer VL = CurrentVL;
constant integer elements = VL DIV esize;
integer vectors = VL DIV 8;
integer vstride = vectors DIV nreg;
bits(32) vbase = X[v, 32];
integer vec = (UInt(vbase) + offset) MOD vstride;
bits(VL) result;

for r = 0 to nreg-1
    bits(VL) operand1 = Z[n+r, VL];
    bits(VL) operand2 = Z[m+r, VL];
    bits(VL) operand3 = ZAvector[vec, VL];
    for e = 0 to elements-1
        bits(esize) sum = Elem[operand3, e, esize];
        for i = 0 to 3
            integer element1 = UInt(Elem[operand1, 4 * e + i, esize DIV 4]);
            integer element2 = SInt(Elem[operand2, 4 * e + i, esize DIV 4]);
            sum = sum + element1 * element2;
        Elem[result, e, esize] = sum;
    ZAvector[vec, VL] = result;
    vec = vec + vstride;
if !HaveSME2() then UNDEFINED;
integer v = UInt('010':Rv);
constant integer esize = 32;
integer n = UInt(Zn:'00');
integer m = UInt(Zm:'00');
integer offset = UInt(off3);
constant integer nreg = 4;
constant bits(datasize) integer d = UInt(Rd);
integer n = UInt(Rn);
integer datasize = if sf == '1' then 64 else 32;
constant bits(datasize) imm;
case sh of
    when '0' imm = ZeroExtend(imm12, datasize);
    when '1' imm = ZeroExtend(imm12:Zeros(12), datasize);
for e = 0 to elements-1
    integer shift = UInt(tsize:imm3) - esize;
if neg then
    element = -element;
else
    element = 1
constant bits(4) tsize = tszh:tszl;
integer shift = UInt(tsize:imm3) - esize;
case cmode:op of
    when '0xx01' operation = ImmediateOp_MVNI;
    when '0xx11' operation = ImmediateOp_BIC;
    when '10x01' operation = ImmediateOp_MVNI;
    when '10x11' operation = ImmediateOp_BIC;
    when '110x1' operation = ImmediateOp_MVNI;
    when '1110x' operation = ImmediateOp_MOVI;
    when '11111'
        // FMOV Dn,#imm is in main FP instruction set
        if Q == '0' then UNDEFINED;
        operation = ImmediateOp_MOVI;
if Z == '0' then
    if n == 31 then source_is_sp = TRUE;
    integer n = UInt(Rn);
else
    if n != 31 then UNDEFINED;
    integer n = UInt(Rn);
    integer n = UInt(Rn);
    integer n = UInt(Rn);
if size != '11' then UNDEFINED;
integer n = UInt(Rn);
integer datasize = 32 << UInt(sf);
integer n = 1;
integer n = x;
integer n = FPRounding_TIEAWAY;
testcall(1, 2, 3);
testcallwithnoarg();
integer datasize = if Q == '1' then 128 else 64;
integer datasize = if Q == '1' then 128;
R[d]<msbit:lsbit> = 1;
AArch32.CheckITEnabled(mask);
PSTATE.IT<7:0> = firstcond:mask;
R[d]<31:16> = imm16;
// R[d]<15:0> unchanged

constant integer VL = CurrentVL;
bits(VL) operand1 = Z[n, VL];
bits(VL) operand2 = Z[m, VL];

Z[d, VL] = operand1 AND (NOT operand2);
"""

class ASLTreeGenerator:

    def __init__(self):
        return
    
    def startParse(self, tree):

        if isinstance(tree, lark.Tree):
            return self.handleTreeType(tree)
        elif isinstance(tree, lark.Token):
            return self.handleNodeType(tree)
        else:
            assert False, tree
        
        return
    
    def handleTreeType(self, item):

        node_type = item.data.value
        node_value = {}

        if node_type in ["start"]:
            nodes = []
            for child in item.children:
                nodes.append(self.startParse(child))
            return nodes
        elif node_type in ["simple_statement", "complex_statement"]:
            for child in item.children:
                return self.handleTreeType(child)
        elif node_type in ["statement_block"]:
            result = []
            
            for child in item.children:
                if child.data.value == "ident_up" or child.data.value == "ident_down":
                    continue
                result.append(self.handleTreeType(child))

            return result
        elif node_type in ['if_statement']:
            
            result = {
                "type": "if",
                "statements": [{
                    "type": "if",
                    "condition": self.startParse(item.children[1]),
                    "statements": self.startParse(item.children[3])
                }]
            }

            items = item.children[4:]
            idx = 0
            while idx < len(items):
                if items[idx] == None:
                    idx += 4
                elif (items[idx].value == "elsif" or items[idx].value == "elif"):
                    result["statements"].append(
                        {
                            "type": "elif",
                            "condition": self.startParse(items[idx + 1]),
                            "statements": self.startParse(items[idx + 3])
                        }
                    )
                    idx += 4
                elif items[idx].value == "else":
                    result["statements"].append(
                        {
                            "type": "else",
                            "statements": self.startParse(items[idx + 1])
                        }
                    )
                    idx += 2
                else:
                    breakpoint()

            return result
        elif node_type in ['for_statement']:
            return {
                "type": "for",
                "direction": item.children[2].value,
                "from": self.startParse(item.children[1]),
                "to": self.startParse(item.children[3]),
                "statements": self.startParse(item.children[4])
            }
        elif node_type in ['case_statement']:
            result = {
                "type": "switch",
                "variable": self.startParse(item.children[1]),
                "cases": []
            }

            for child in item.children[3:]:
                if child.data.value == "ident_up" or child.data.value == "ident_down":
                    continue
                if child.data.value == "when_statement":
                    result["cases"].append(
                        {
                            "type": "case",
                            "case": self.startParse(item.children[1]),
                            "statements": self.startParse(item.children[2])
                        }
                    )
                elif child.data.value == "otherwise_statement":
                    result["cases"].append(
                        {
                            "type": "default",
                            "statements": self.startParse(item.children[1])
                        }
                    )

            return result
        
        elif node_type in ['while_do_statement']:
            return {
                "type": "while",
                "condition": self.startParse(item.children[1]),
                "statements": self.startParse(item.children[3])
            }
        elif node_type in ['see_statement']:
            return {
                "type": "see", 
                "value": self.startParse(item.children[1])
            }
        elif node_type in ['assert_statement']:
            return {
                "type": "assert", 
                "condition": self.startParse(item.children[1])
            }   
        elif node_type in ['assigment_statement']:
            return {
                "type": "assign",
                "variable": self.startParse(item.children[0]),
                "value": self.startParse(item.children[2])
            }
        elif node_type in ['function_statement']:    
            return {
                "type": "call",
                "function": item.children[0].value,
                "parameters": self.startParse(item.children[1])
            }
        elif node_type in ['function_parameters']:

            result = []

            for child in item.children:
                if child == None:
                    continue
                result.append(self.startParse(child))

            return result
        
        elif node_type in ['builtin_statement']:
            return {
                "type": "builtin",
                "name": item.children[0].value
            }    
        elif node_type in ['inline_if_statement']:
            
            result = {
                "type": "inline_if",
                "condition": self.startParse(item.children[1]),
                "statement": self.startParse(item.children[3])
            }

            if item.children[5] != None: # hasn't else statement
                result["else_statement"] = self.startParse(item.children[6])

            return result
        
        elif node_type in ['variable_class_member_call']:
            return {
                "type": "call_member",
                "function": self.startParse(item.children[0]),
                "parameters": self.startParse(item.children[1])
            }
        elif node_type in ['variable_class_member']:
            return {
                "type": "class_member",
                "class": self.startParse(item.children[0]),
                "member": self.startParse(item.children[2])
            }
        elif node_type in ['variable_proto']:

            if item.children[0] != None\
                or item.children[1] != None\
                or item.children[2] != None:
                
                result = {
                    "type": "variable_declaration",
                    "constant": False,
                    "name": item.children[3].children[0].value
                }

                if item.children[0] != None:
                    result["constant"] = True
                if item.children[1] != None:
                    result["size"] = self.startParse(item.children[1].children[2]) 
                if item.children[2] != None:
                    result["type"] = item.children[2].data.value

                return result
            else:
                return self.startParse(item.children[3])
            
        elif node_type in ['variable_name']:
            return {
                "type": "variable",
                "name": item.children[0].value
            }
        elif node_type in ['buildin_types']:
            return {
                "type": "variable_buildin",
                "name": item.children[0].value
            }
        elif node_type in ['slice_sized_variable', 'slice_variable']:
            result = {
                "type": "variable_slice",
                "variable": self.startParse(item.children[0]),
                "slice": []
            }

            for slice_item in item.children[1].children[1:-1]:
                result["slice"].append(self.startParse(slice_item))

            return result

        elif node_type in ['variable_miltiple_proto']:
                
            result = {
                    "type": "variable_declaration_multi",
                    "constant": False,
                    "names": []
                }

            if item.children[0] != None\
                or item.children[1] != None\
                or item.children[2] != None:

                if item.children[0] != None:
                    result["constant"] = True
                if item.children[1] != None:
                    result["size"] = self.startParse(item.children[1].children[2]) 
                if item.children[2] != None:
                    result["type"] = item.children[2].data.value

             
            items = item.children[3:]
            idx = 0
            while idx < len(items):
                result["names"].append(items[idx].children[0].value)
                idx += 2
            
            return result
        
        elif node_type in ['variable_array_proto']:
            return {
                    "type": "array_declaration",
                    "bounds":  item.children[1].value,
                    "variable": self.startParse(item.children[3])
                }
        elif node_type in ['class_members_list']:
            result = {
                "type": "class_tuple",
                "list": []
            }

            items = item.children[1:-1]
            idx = 0
            while idx < len(items):
                if items[idx].data.value == 'variable_name':
                    result["list"].append(item.children[1:-1][0].children[0].value)

                idx += 2

            return result
        elif node_type in ['variable_tuple']:
            result = {
                "type": "tuple",
                "list": []
            }

            items = item.children[1:-1]
            idx = 0
            while idx < len(items):
                if items[idx].data.value == 'variable_tuple_value':
                    result["list"].append(self.startParse(items[idx].children[0]))

                idx += 2

            return result
        elif node_type in ['variable_list']:
            result = {
                "type": "variable_list",
                "list": []
            }

            for child in item.children[1:-1]:
                if child == None:
                    continue
                result["list"].append(self.startParse(child))

            return result
        
        elif node_type in ['check_in_list', 'or_test', 'and_test', 'compare_test', \
                            'or_expr', 'xor_expr', 'and_expr', 'shift_expr', 'arith_expr', \
                            'coeff_expr', 'unary_expr', 'power_expr', 'value_expr']:
            result = {
                "type": "binary_operation" if node_type != "unary_expr" else "unary_operation"
            }

            if node_type == "unary_expr":
                result["operation"] = item.children[0].value
                result["right"] = self.startParse(item.children[1])
            elif node_type == "check_in_list":
                result["left"] = self.startParse(item.children[0])
                result["operation"] = "in"
                result["right"] = self.startParse(item.children[1])
            else:
                result["left"] = self.startParse(item.children[0])
                result["operation"] = item.children[1].value
                result["right"] = self.startParse(item.children[2])
    
            return result
        elif node_type in ['number']:

            result = {
                "type": "value",
                "value": item.children[0].value
            }

            if item.children[0].type == "DEC_NUMBER":
                result["format"] = "dec"
            elif item.children[0].type == "HEX_NUMBER":
                result["format"] = "hex"
            elif item.children[0].type == "BIN_NUMBER":
                result["format"] = "bin"
            elif item.children[0].type == "OCT_NUMBER":
                result["format"] = "oct"
            elif item.children[0].type == "FLOAT_NUMBER":
                result["format"] = "float"
            elif item.children[0].type == "IMAG_NUMBER":
                result["format"] = "imag"
                
            return result
        elif node_type in ['bits_string']:
            return {
                "type": "bitstring",
                "value": item.children[0].value
            }
        elif node_type in ['bits_extract']:
            result = {
                "type": "extractbits",
                "variable": self.startParse(item.children[0]),
                "offset": 0,
                "width": 0,
            }

            offsets = item.children[1].children[1:-1]

            if offsets[2] == None:
                result["offset"] = self.startParse(offsets[0])
            else:
                result["offset"] = self.startParse(offsets[0])
                result["width"] = self.startParse(offsets[2])

            return result
        elif node_type in ['concat_variable']:
            result = {
                "type": "concat",
                "list": []
            }

            idx = 0
            while idx < len(item.children):
                result["list"].append(self.startParse(item.children[idx]))
                idx += 2

            return result
        else:
            assert False, item

        return {
                "type": node_type, 
                "value": node_value
            }

    def handleNodeType(self, item):

        node_type = item.value
        node_value = str(item)

        return {
                "type": node_type, 
                "value": node_value
            }

def main():
    asl_parser = Lark(arm_helpers.arm_grammar_string, parser="earley", postlex=arm_helpers.PythonIndenter())

    fixup_code = test_string
    fixup_code = arm_helpers.escapeSpec(fixup_code, ["AND","EOR","OR","DIV","REM","MOD","&&","||",">>","<<","*","+","-","^","&","|","%"])
    fixup_code = fixup_code + "\r\n"
    
    ast_tree = asl_parser.parse(fixup_code)

    generator = ASLTreeGenerator()
    result_json = generator.startParse(ast_tree)

    print(json.dumps(result_json))

if __name__ == "__main__":
    sys.exit(main())