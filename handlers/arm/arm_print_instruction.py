import argparse
import glob
import json
import os
import re
import threading
import arm_helpers

def concatFieldsDicts(dict_1, dict_2):

    fields_association = dict_1

    for item in dict_2:
        if item in fields_association:
            if fields_association[item] < dict_2[item]:
                fields_association[item] = dict_2[item]
            else:
                fields_association[item] = dict_2[item]        
        else:
            fields_association[item] = dict_2[item]

    return fields_association

def printInstructionVariableDecode(ofile, instructions):

    fields_association = {}

    current_inst_idx = 0

    for section_name in instructions:
        inst_section = instructions[section_name]
        print(section_name + " " + str(current_inst_idx) + " of " + str(len(instructions)))

        current_inst_idx += 1
        print("static uint32_t decode_section_" + section_name + "(struct arm_decode_context* context) {", file=ofile)
        print("", file=ofile)
        
        for class_ in inst_section["classes"]:
            
            encodings = class_["encodings"]

            comperand = 0
            match_value = 0
            mask_string = ""
            for field in class_["fields"]:
                
                if len(mask_string):
                    mask_string += "|"

                if field["name"] != "_":
                    mask_string += field["name"] + "="
                mask_string += field["consts"]

                (fl_comperand, fl_match) = arm_helpers.createMaskComperand(field["consts"])

                comperand |= fl_comperand << field["offset"]
                match_value |= fl_match << field["offset"]

            print("    "*2 + "// " + mask_string, file=ofile)
            print("    "*2 + "if((context->instruction_word & " + hex(comperand) + " == " + hex(match_value) +") {", file=ofile)
            print("    "*3 + "decode_instruction_fields(context, ENC_" + encodings[0]["encoding_name"].lower() + ");", file=ofile)  
            
            fields_association = concatFieldsDicts(fields_association, interpretDecodeScript(ofile, class_['decode_asl']))
            
            for encoding in encodings:
                setup_encoding = "SetDecodedEncoding(" + "ENC_" + encoding["encoding_name"].lower() + ");"
                if len(encoding["fields"]):

                    condition_string = ""
                    for field in encoding["fields"]:

                        if len(condition_string):
                            condition_string += " && "

                        cond_box = arm_helpers.convertInstructionBox(field["consts"], True)
                        condition_string += arm_helpers.createMaskCondition(
                                        field["name"], 
                                        cond_box["mask"], 
                                        cond_box["equal"]
                                    )
                        if field["name"] != "_":
                            fields_association = concatFieldsDicts(fields_association, {arm_helpers.fieldNameEscape(field["name"]): arm_helpers.maskToLength(cond_box["mask"])})
                        
                    print("    "*3 + "if(" + condition_string + ") " + setup_encoding, file=ofile)
                else:
                    print("    "*3 + setup_encoding, file=ofile)
                    

            print("    "*2 + "}", file=ofile)

        if inst_section['postdecode_asl'] != None:
            print("    "*2 + "// post decode", file=ofile)
            fields_association = concatFieldsDicts(fields_association, interpretDecodeScript(ofile, inst_section['postdecode_asl']))
        if inst_section['execute_asl'] != None:
            interpretDecodeScript(ofile, inst_section['execute_asl'])
        print("}", file=ofile)
    
    return fields_association

def printInstructionFieldTableDecode(ofile, full_defination):

    fields_association = {}
    fields_decoding_association = {}

    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            
            if len(class_["fields"]) == 0:
                continue
            
            fields_mask = ""
            for field in class_["fields"]:
                
                if field["name"] == "_":
                    continue

                fields_mask += "|" + field["name"] + ":" + str(field["width"]) + ":" + str(field["offset"]) + ":" + field["consts"] 

            if len(fields_mask) == 0:
                continue

            for encoding in class_["encodings"]:
                if fields_mask not in fields_decoding_association:
                    fields_decoding_association[fields_mask] = {
                            "encodings": [encoding['encoding_name']],
                            "fields": class_["fields"]
                        }
                else:
                    fields_decoding_association[fields_mask]["encodings"].append(encoding['encoding_name'])

    print("static uint32_t decode_instruction_fields(struct arm_decode_context* context, uint32_t encoded_form) {", file=ofile)
    print("", file=ofile)
    print("    switch(encoded_form) {", file=ofile)

    for fields in fields_decoding_association:
        for encoding_name in fields_decoding_association[fields]["encodings"]:
            print("    case ENC_" + encoding_name.lower() + ":", file=ofile)

        for field in fields_decoding_association[fields]["fields"]:
            
            if field["name"] == "_":
                continue
                        
            fields_association = concatFieldsDicts(fields_association, {arm_helpers.fieldNameEscape(field["name"]): field["width"]})

            print("        context->" + field["name"] + " = EXTRACT_BITS(" +
               str(field["offset"]) + ", "+ 
               str(field["width"]) + ");", file=ofile)

        print("        break;", file=ofile)

    print("    }", file=ofile)
    print("}", file=ofile)
    return fields_association

def printInstructionClassDecode(ofile, full_defination):

    classes_association = {}
    classes_list = ["CLASS_none"]
    
    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            for encoding in class_["encodings"]:
                
                if encoding["inst_class"] != None:
                    if encoding["inst_class"] not in classes_association:
                        classes_association[encoding["inst_class"]] = [encoding["encoding_name"]]
                    else:
                        classes_association[encoding["inst_class"]].append(encoding["encoding_name"])


    print("static uint32_t decode_instruction_class(uint32_t encoding_form) {", file=ofile)
    print("", file=ofile)

    print("    switch(encoding_form) {", file=ofile)

    for assoc in classes_association:
        for encoding_name in classes_association[assoc]:
            print("    case ENC_" + encoding_name.lower() + ":", file=ofile)
        print("        return CLASS_" + assoc.lower() + ";", file=ofile)
        classes_list.append("CLASS_" + assoc.lower())

    print("    }", file=ofile)
    print("    return CLASS_none;", file=ofile)
    print("}", file=ofile)
    return classes_list

def printInstructionMnemonicDecode(ofile, full_defination):

    mnemonic_association = {}

    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            for encoding in class_["encodings"]:
                if encoding["mnemonic"] not in mnemonic_association:
                    mnemonic_association[encoding["mnemonic"]] = [encoding["encoding_name"]]
                else: 
                    mnemonic_association[encoding["mnemonic"]].append(encoding["encoding_name"]) 

    encode_list = []
    instruction_list = ["INS_invalid"]

    print("static uint32_t decode_instruction_mnemonic(uint32_t encoding_form) {", file=ofile)
    print("", file=ofile)

    print("    switch(encoding_form) {", file=ofile)

    for assoc in mnemonic_association:
        for encoding_name in mnemonic_association[assoc]:
            print("    case ENC_" + encoding_name.lower() + ":", file=ofile)
            encode_list.append("ENC_" + encoding_name.lower())
        print("        return INS_" + assoc.lower() + ";", file=ofile)
        instruction_list.append("INS_" + assoc.lower())
    
    print("    }", file=ofile)
    print("    return INS_invalid;", file=ofile)
    print("}", file=ofile)
    return (encode_list, instruction_list)

def printFeatureFunctions(ofile, full_defination):

    feature_list = full_defination["features_list"]

    print("#pragma once", file=ofile)
    print("", file=ofile)

    for feat in feature_list:
        print("#define " + feat + "() ( return context->checkFeat(" + feature_list[feat] + "); )", file=ofile)

    print("", file=ofile)

def printInstructionAsmTemplate(ofile, instructions):


    return

def printInstructionDecoderFields(ofile, fields_association_dec, fields_association_var):

    fields_decoding_association = concatFieldsDicts(fields_association_dec, fields_association_var)

    for field in fields_decoding_association:
        print("    " + field + "; // bits width " + str(fields_decoding_association[field]), file=ofile)

    return fields_decoding_association


def  printInstructionEncodingForms(ofile, full_defination):

    encode_list = []

    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            for encoding in class_["encodings"]:
                if "ENC_" + encoding["encoding_name"] not in encode_list:
                    encode_list.append("ENC_" + encoding["encoding_name"]) 

 
    print("#pragma once", file=ofile)
    print("", file=ofile)

    print("enum ArmInstEncoding {", file=ofile)

    for encoding in encode_list:
        print("    " + encoding + ",", file=ofile)

    print("};", file=ofile)
    print("", file=ofile)
    return

def printInstructionList(ofile, full_defination):

    classes_list = ["CLASS_none"]
    instruction_list = ["INS_invalid"]

    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            for encoding in class_["encodings"]:       
                if encoding["inst_class"] != None:
                    if "CLASS_" + encoding["inst_class"] not in classes_list:
                        classes_list.append("CLASS_" + encoding["inst_class"])

    for section_name in full_defination["sections"]:
        for class_ in full_defination["sections"][section_name]["classes"]:
            for encoding in class_["encodings"]:
                if "INS_" + encoding["mnemonic"] not in instruction_list:
                    instruction_list.append("INS_" + encoding["mnemonic"]) 


    print("#pragma once", file=ofile)
    print("", file=ofile)
    print("enum ArmInstMnemonic {", file=ofile)
    for inst in instruction_list:
        print("    " + inst + ",", file=ofile)
    print("};", file=ofile)
    print("", file=ofile)

    print("enum ArmInstClasses {", file=ofile)
    for class_ in classes_list:
        print("    " + class_ + ",", file=ofile)
    print("};", file=ofile)
    print("", file=ofile)

    feat_idx = 0
    for feat in full_defination:
        print("#define " + full_defination[feat] + " " + str(feat_idx), file=ofile)
        feat_idx += 1

    print("", file=ofile)

    return

