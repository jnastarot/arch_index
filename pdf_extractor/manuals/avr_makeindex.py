import os
import sys
import json

from makeindex import *

def handleSectionAVR8(data_json):

    format_index = {
            "9/16-bit pc": [1],
            "22-bit pc": [2],
            "i": [1],
            "cycles": [1, 2, 3, 4, 5],
            "(i)": [1],
            "ii": [2],
            "(ii)": [2],
            "iii": [3],
            "(iii)": [3],
            "iv": [4],
            "v": [5],
            "i-iii": [1, 2, 3],
            "iv-vi": [4, 5, 6],
            "i-iv": [1, 2, 3, 4],
            "v-viii": [5, 6, 7, 8]
    }

    operation_table = None
    operations = []

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "operations":
            operation_table = element["elements"][0]
            break

    for current_row in operation_table["rows"][1:]:
        operations.append(
                { 
                    "syntax": elementsToText(current_row["columns"][0]).strip(), 
                    "operation": current_row["columns"][1],
                    "operands": elementsToText(current_row["columns"][2]).strip(),
                    "program counter": elementsToText(current_row["columns"][3]).strip(),
                    "opcode": elementsToText(current_row["columns"][4]).strip(),
                    "comment": elementsToText(current_row["columns"][5]).strip(),
                    "stack": elementsToText(current_row["columns"][6]).strip(),
                    "isa": []
                }
            )

    
    cycles_table = None

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "table cycles":
            cycles_table = element["elements"][0]
            break

    for current_row in cycles_table["rows"][1:]:
        for op_idx in range(1, len(operations) + 1):

            column_idx = 1
            for column in cycles_table["rows"][0]["columns"][1:]:
                last_element_name = column["elements"][-1]["elements"][-1]["text"].strip().lower()

                has_isa = True
  
                if last_element_name in format_index:
                    if op_idx not in format_index[last_element_name]:
                        has_isa = False

                if has_isa:
                    if elementsToText(current_row["columns"][column_idx]).strip().lower() != "n/a":
                        operations[op_idx - 1]["isa"].append(elementsToText(current_row["columns"][0]).strip())
                
                column_idx += 1

    status_reg_info = []
    sreg_table = None
    
    for element in data_json["elements"]:
        text = element["text"].strip().lower()
        if text in ["status register (sreg) and boolean formula", "status register and boolean formula"]:
            sreg_table = element["elements"][0]
            break

    if sreg_table != None:
        for current_row in sreg_table["rows"]:
            flag_name = elementsToText(current_row["columns"][0]).strip().lower()

            flag_operation = ""
            if flag_name.find("(result)") != -1:
                flag_operation = elementsToText(current_row["columns"][1]).strip().lower()
            else:
                flag_operation = elementsToText(current_row["columns"][2]).strip().lower()
            
            status_reg_info.append({
                "flag": flag_name,
                "operation": flag_operation
            })

    return [operations, status_reg_info]

def createIndexDocAVR8(path, path_out, title, index_name, pdf_version):

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

                    indexed_table["index"].append({
                            "filename": path_out + "/" + file,
                            "filename_html": path_out + "/" + file,
                            
                            "description": data_json["rootname"][1].strip(),
                            "operations": handleSectionAVR8(data_json)
                        })   

    return [indexed_table]

def makeAVR8Indexes():

    # Syntax | Description | Features

    indexes = []

    indexes += createIndexDocAVR8("gen/avr8/main", "html/avr8/main", "AVR8 ISA Reference", "avr8_index", "DS40002198B")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("AVR8 ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › avr8")
    text.append(CloseTag("div"))

    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "300"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for op_element in element["operations"][0]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/avr8/"):-5] + ".html"}))
                ins_table.append(op_element["syntax"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(" ".join(op_element["isa"]))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))

                if len(op_element["comment"]) == 0:
                    ins_table.append(element["description"])
                else:
                    ins_table.append(element["description"] + " " + op_element["comment"])

                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/avr8/avr8_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/avr8/avr8_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)

def handleSectionAVR32(data_json):

    operation_table = None
    operations = []

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "operations":
            operation_table = element["elements"][0]
            break

    for current_row in operation_table["rows"][1:]:
        operation_def = { 
                    "syntax": elementsToText(current_row["columns"][1]).strip(), 
                    "operation": current_row["columns"][2],
                    "operands": elementsToText(current_row["columns"][3]).strip(),
                    "revision":  elementsToText(current_row["columns"][4]).strip(),
                    "opcode":  []
                }
        
        opcode_table = current_row["columns"][5]["elements"][0]

        for idx in range(0, len(opcode_table["rows"][0]["columns"])):
            column_text = elementsToText(opcode_table["rows"][0]["columns"][idx]).strip()
            column_size = int(elementsToText(opcode_table["rows"][1]["columns"][idx]).strip())

            operation_def["opcode"].append({
                "text": column_text,
                "size": column_size
            })
            
        operations.append(operation_def)
        

    status_reg_info = {
        "pragma": [],
        "flags": []
    }

    sreg_table = None
    
    for element in data_json["elements"]:
        text = element["text"].strip().lower()
        if text in ["status flags", "status flags:", "status flag:"]:
            sreg_table = element["elements"][0]
            break

    for current_row in sreg_table["rows"]:
        flag_name = elementsToText(current_row["columns"][0]).strip().lower()
        
        if len(flag_name) >= 3:
            status_reg_info["pragma"].append(
                    elementsToText(current_row["columns"][0]).strip().lower()
                )
            
        else:
            if flag_name.find(":") != -1:
                flag_name = flag_name[: flag_name.find(":")]

            flag_operation = elementsToText(current_row["columns"][1]).strip().lower()

            status_reg_info["flags"].append({
                    "flag": flag_name,
                    "operation": flag_operation
                })

    return [operations, status_reg_info]

def createIndexDocAVR32(path, path_out, title, index_name, pdf_version):

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

                    indexed_table["index"].append({
                            "filename": path_out + "/" + file,
                            "filename_html": path_out + "/" + file,
                            
                            "description": data_json["rootname"][1].strip(),
                            "operations": handleSectionAVR32(data_json)
                        })   

    return [indexed_table]

def makeAVR32Indexes():
    
    # Syntax | Description | Revision

    indexes = []

    indexes += createIndexDocAVR32("gen/avr32/main", "html/avr32/main", "AVR32 ISA Reference", "avr32_index", "32000D-04/2011")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("AVR32 ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › avr32")
    text.append(CloseTag("div"))

    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))


    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "300"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "100"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for op_element in element["operations"][0]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/avr32/"):-5] + ".html"}))
                ins_table.append(op_element["syntax"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(op_element["revision"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/avr32/avr32_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/avr32/avr32_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)


def makeAllFullDocs():
    createFullDoc("AVR8 ISA Reference", "gen/avr8/main", "html/avr8/avr8_full.html", "avr8_index.html")
    createFullDoc("AVR32 ISA Reference", "gen/avr32/main", "html/avr32/avr32_full.html", "avr32_index.html")
def makeAllIndexes():
    makeAVR8Indexes()
    makeAVR32Indexes()
    
#makeAllFullDocs()
#makeAllIndexes()