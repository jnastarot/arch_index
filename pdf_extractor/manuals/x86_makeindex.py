import os
import sys
import json

from makeindex import *

# Opcode | Instruction | Op/ En | 64-Bit Mode | Compat/ Leg Mode | Description
# Opcode/ Instruction | Op / En | 64/32 bit Mode Support | CPUID Feature Flag | Description

def handleEncodingTable(data_json):

    encoding_table = data_json["elements"][0]["elements"][0]

    if encoding_table["type"] != "table":
        breakpoint()

    operations = []

    opcode_column_idx = -1
    instruction_column_idx = -1
    cpuid_idx = -1
    description_idx = -1

    for column_idx in range(0, len(encoding_table["rows"][0]["columns"])):

        column = encoding_table["rows"][0]["columns"][column_idx]

        column_title = elementsToText(column, True).strip().lower()

        if opcode_column_idx == -1:
            if column_title.find("opcode") != -1:
                opcode_column_idx = column_idx

        if instruction_column_idx == -1:
            if column_title.find("instruction") != -1:
                instruction_column_idx = column_idx

        if cpuid_idx == -1:
            if column_title.find("cpuid") != -1:
                cpuid_idx = column_idx

        if description_idx == -1:
            if column_title.find("description") != -1:
                description_idx = column_idx

    for instruction_row in encoding_table["rows"][1:]:

        instruction_def = {
                "opcode": "",
                "mnemonic": "",
                "description": "",
                "cpuid": "",
            }

        if opcode_column_idx == -1 \
                or instruction_column_idx == -1\
                or  description_idx == -1:
            breakpoint()

        if opcode_column_idx == instruction_column_idx:

            if len(instruction_row["columns"][opcode_column_idx]["elements"]) == 2:
                instruction_def["opcode"] = elementToText(instruction_row["columns"][opcode_column_idx]["elements"][0])
                instruction_def["mnemonic"] = elementToText(instruction_row["columns"][opcode_column_idx]["elements"][1])
            else:
                text = elementsToText(instruction_row["columns"][opcode_column_idx], True).strip()

                if text.find("\n") != -1:
                    instruction_def["opcode"] = text[:text.find("\n")]
                    instruction_def["mnemonic"] = text[text.find("\n") + 1:]
                else:
                    if text.find("/r") != -1:
                        instruction_def["opcode"] = text[:text.find("/r") + 2]
                        instruction_def["mnemonic"] = text[text.find("/r") + 2:]
                    else:
                        breakpoint()

            instruction_row["columns"][opcode_column_idx]

        else:
            instruction_def["opcode"] = elementsToText(instruction_row["columns"][opcode_column_idx], True).strip()
            instruction_def["mnemonic"] = elementsToText(instruction_row["columns"][instruction_column_idx], True).strip()
            
        if cpuid_idx != -1:
            instruction_def["cpuid"] = elementsToText(instruction_row["columns"][cpuid_idx], True).strip()

        instruction_def["opcode"].replace('*', '')

        instruction_def["description"] = elementsToText(instruction_row["columns"][description_idx]).strip()

        operations.append(instruction_def)

    return operations

def handleOperations(data_json):

    operations = []

    for element_idx in range(0, len(data_json["elements"])):
        element = data_json["elements"][element_idx]
        text = element["text"].strip()

        if text.lower() in ["operation", "operations", "operation in a uni-processor platform"]:
            
            operations.append({
                    "title": "",
                    "operation": element["elements"]
                })
            
            for sub_element_idx in range(element_idx + 1, len(data_json["elements"])):
                sub_element = data_json["elements"][element_idx]

                if "level" not in sub_element or sub_element["level"] >= element["level"]:
                    return operations
                
                operations.append({
                        "title": sub_element["text"],
                        "operation": sub_element["elements"]
                    })

    return operations

def createIndexDocX86(path, path_out, title, index_name, pdf_version):

    #  Mnemonic Opcode Features Description
    indexed_table = {
        "pdf_version": pdf_version,
        "title": title,
        "path": path,
        "index": []
    }

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                with open(path + "/" + file, "r") as f:
                    data_json = json.load(f)

                    createFileDoc(path + "/" + file, path_out + "/" + file[:-5] + ".html", index_name)

                    indexed_table["index"].append( {
                                "filename": path_out + "/" + file,
                                "encodings": handleEncodingTable(data_json),
                                "operations": handleOperations(data_json)
                            })

    return [indexed_table]
    
def makeX86Indexes():

    indexes = []
    indexes += createIndexDocX86("gen/x86/main", "html/x86/main", "Intel x86 ISA Reference", "x86_index", "325383-080US June 2023")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("Intel ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › x86")
    text.append(CloseTag("div"))

    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))

        ins_table.append(OpenTag("th", attributes={"width": "400"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th", attributes={"width": "30"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for op_element in element["encodings"]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/x86/"):-5] + ".html"}))
                ins_table.append(op_element["mnemonic"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(op_element["opcode"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(op_element["cpuid"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(op_element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/x86/x86_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/x86/x86_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)


def makeAllFullDocs():
    createFullDoc("Intel x86 ISA Reference", "gen/x86/main", "html/x86/x86_full.html", "x86_index.html")
def makeAllIndexes():
    makeX86Indexes()

#makeAllFullDocs()
#makeAllIndexes()
