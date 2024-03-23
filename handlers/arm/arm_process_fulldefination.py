import json
import os
import re
import string
import xml.etree.cElementTree as ET
import threading

import random
import time
import multiprocessing as mp

from lark import Lark

from arm_read_encodeindex import *
from arm_read_instruction import *
from arm_helpers import *

def handleInstructionVariableDecode(source, dest):

    with open(source, "r") as src_file:   
        tasks = json.load(src_file)
        tasks = tasks["args"]
        
    asl_parser = Lark(arm_grammar_string, parser="earley", postlex=PythonIndenter())

    fields_association = {}
    task_idx = 1
    for instruction in tasks:
        section_name = instruction["section_name"]
        current_inst_idx = instruction["current_inst_idx"]
        inst_section =  instruction["instructions"]
        
        print(section_name + " [" + str(task_idx) + "/"+ str(len(tasks)) + "]")
        task_idx = task_idx + 1

        for class_ in inst_section["classes"]:
            if 'decode_asl' in class_ and class_['decode_asl'] != None:
                class_['decode_asl']["code"] = parseASLScript(asl_parser, class_['decode_asl'])

        if 'postdecode_asl' in inst_section and inst_section['postdecode_asl'] != None:
            inst_section['postdecode_asl']["code"] = parseASLScript(asl_parser, inst_section['postdecode_asl'])

        if 'execute_asl' in inst_section and inst_section['execute_asl'] != None:
            inst_section['execute_asl']["code"] = parseASLScript(asl_parser, inst_section['execute_asl'])

        with open(dest + "/" + section_name + ".json", "w") as section_file:      
            print(
                json.dumps({
                    "section_name": section_name, 
                    "section": inst_section
                }, cls=SetEncoder), 
                file=section_file
                )

    return fields_association

def executeProcessDecode(*args):

    config_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=15))

    with open(config_name, "w") as section_file:      
        print(json.dumps({"args": args[0]}, cls=SetEncoder), file=section_file)
    
    process = mp.Process(target=handleInstructionVariableDecode, args=(config_name, args[1]))
    process.start()

    while process.is_alive():
        time.sleep(1)

    os.remove(config_name)
    return

def processInstructionASL(instructions):

    decoded_sections = {}
    current_inst_idx = 0

    threads_list = []
    tasks = []

    for section_name in instructions:

        tasks.append({
                "section_name": section_name, 
                "current_inst_idx": current_inst_idx, 
                "instructions": instructions[section_name]
            })
        
        current_inst_idx += 1

    cpu_count = os.cpu_count() - 5

    thread_tasks = [[] for i in range(cpu_count)]
    
    current_idx = 0
    while current_idx != len(tasks):

        for cpu_idx in range(cpu_count):

            if current_idx == len(tasks):
                break

            thread_tasks[cpu_idx].append(tasks[current_idx])

            current_idx = current_idx + 1

    for cpu_idx in range(cpu_count):
        
        thread = threading.Thread(target=executeProcessDecode, args=(thread_tasks[cpu_idx], "gen"))
        threads_list.append(thread)
        thread.start()

    for thread in threads_list:
        thread.join()

    for decoded_name in os.listdir(os.path.join(os.getcwd(), "gen")):
        with open(os.path.join(os.getcwd(), "gen", decoded_name), "r") as src_file:   
            decoded_section = json.load(src_file)
            decoded_sections[decoded_section["section_name"]] = decoded_section["section"]

    return decoded_sections

def processArmFullDefination(onebig_filepath):
    root = ET.parse(onebig_filepath)
    instructionset = ""
    iform_set = []
    for index in root.findall('.//alphaindex'):
        instructionset = index.find('toptitle').attrib["instructionset"]
        iforms = index.find('iforms')
        for iform in iforms.findall('.//iform'):
            iform_set.append(iform.attrib["id"])

    shared_root = root.find(".//instructionsection[@id='shared_pseudocode']")

    #decoder_index = readEncodingIndexFile(encoding_index_path)
    (shared, names) = readShared(shared_root)
    features_list = readFeatureFunctions(shared)
    
    instructions = {}
    
    for iform in iform_set:
        section_root = root.find(".//instructionsection[@id='" + iform + "']")
        if section_root == None:
            breakpoint()
        instruction = readInstruction(section_root)
        if instruction is None: 
            breakpoint()
            continue
        instructions[iform] = instruction

    sections = processInstructionASL(instructions)

    return {
            "index": instructionset, 
            "sections": sections,
            "features_list": features_list
        }

def main():

    handleInstructionVariableDecode("12312323/4K266CGX41KAEZV", "gen")
    return

if __name__ == "__main__":
    sys.exit(main())