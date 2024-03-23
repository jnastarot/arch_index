import os
import sys
import json

from makeindex import *

def makeAllFullDocs():
    createFullDoc("Mips16 ISA Reference", "gen/mips16/ase_16", "html/mips16/mips_16_full.html", "mips16_index.html")
    createFullDoc("Mips16e2 ISA Reference", "gen/mips16/ase_16e2", "html/mips16/mips_16e2_full.html", "mips16_index.html")

    createFullDoc("Mips 3D ISA Reference", "gen/mips/ase_3d", "html/mips/mips_3d_full.html", "mips_index.html")
    createFullDoc("Mips DSP ISA Reference", "gen/mips/ase_dsp", "html/mips/mips_dsp_full.html", "mips_index.html")
    createFullDoc("Mips MCU ISA Reference", "gen/mips/ase_mcu", "html/mips/mips_mcu_full.html", "mips_index.html")
    createFullDoc("Mips MSA ISA Reference", "gen/mips/ase_msa", "html/mips/mips_msa_full.html", "mips_index.html")
    createFullDoc("Mips MT ISA Reference", "gen/mips/ase_mt", "html/mips/mips_mt_full.html", "mips_index.html")
    createFullDoc("Mips SMART ISA Reference", "gen/mips/ase_smart", "html/mips/mips_smart_full.html", "mips_index.html")
    createFullDoc("Mips VZ ISA Reference", "gen/mips/ase_vz", "html/mips/mips_vz_full.html", "mips_index.html")
    createFullDoc("Mips ISA Reference", "gen/mips/mips_6_6", "html/mips/mips_main_full.html", "mips_index.html")

    createFullDoc("MicroMips DSP ISA Reference", "gen/micromips/ase_dsp", "html/micromips/micromips_dsp_full.html", "micromips_index.html")
    createFullDoc("MicroMips MCU ISA Reference", "gen/micromips/ase_mcu", "html/micromips/micromips_mcu_full.html", "micromips_index.html")
    createFullDoc("MicroMips MT ISA Reference", "gen/micromips/ase_mt", "html/micromips/micromips_mt_full.html", "micromips_index.html")
    createFullDoc("MicroMips VZ ISA Reference", "gen/micromips/ase_vz", "html/micromips/micromips_vz_full.html", "micromips_index.html")
    createFullDoc("MicroMips ISA Reference", "gen/micromips/micromips_6_6", "html/micromips/micromips_main_full.html", "micromips_index.html")
    
    createFullDoc("NanoMips DSP ISA Reference", "gen/nanomips/ase_dsp", "html/nanomips/nanomips_dsp_full.html", "nanomips_index.html")
    createFullDoc("NanoMips MT ISA Reference", "gen/nanomips/ase_mt", "html/nanomips/nanomips_mt_full.html", "nanomips_index.html")
    createFullDoc("NanoMips ISA Reference", "gen/nanomips/main", "html/nanomips/nanomips_main_full.html", "nanomips_index.html")
    
def handleEncodingTable(table_data):
    table_rows = []
    table_sizes = []

    for idx in range(0, len(table_data["rows"]) - 1):
        current_row = table_data["rows"][idx]
        encoding_row = []
        for column in current_row["columns"]:
            
            column_text = []
            
            for column_element in column["elements"]:
                column_paragraph = ""
                
                for el_text in column_element["elements"]:
                    column_paragraph += el_text["text"]
                
                column_text.append(column_paragraph)

            encoding_row.append(column_text)
                
        table_rows.append(encoding_row)

    for size_column in table_data["rows"][-1]["columns"]:
        size_text = elementsToText(size_column)
        table_sizes.append(int(size_text))

    return  {
                "sizes": table_sizes,
                "encodings": table_rows
            }

def handleSectionEncoding(data_json):

    encodings = []

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "encoding":
            
            table_caption = ""
            encoding_table = []
            
            for encode_element in element["elements"]:
                if encode_element["type"] == "paragraph":
                    
                    if len(encoding_table):
                        encodings.append({
                                "caption": table_caption,
                                "tables": encoding_table
                            })
                        table_caption = ""
                        encoding_table = []

                    for text_el in encode_element["elements"]: 
                        table_caption += text_el["text"]

                elif encode_element["type"] == "table":
                    encoding_table.append(handleEncodingTable(encode_element))

            if len(encoding_table):
                encodings.append({
                        "caption": table_caption,
                        "tables": encoding_table
                    })

            break
        
    #if len(encodings) == 0:
    #    breakpoint()

    return encodings


def handleNanoSectionEncoding(data_json):

    encodings = []

    for root_element_idx in range(0, len(data_json["elements"])):
        
        if data_json["elements"][root_element_idx]["type"] == "title":
            text = data_json["elements"][root_element_idx]["text"][:data_json["elements"][root_element_idx]["text"].find(":")].strip().lower()

            # start from format title
            if text.lower() == "format":
                
                # if format has't sub encodings
                if len(data_json["elements"][root_element_idx]["elements"]) != 0:
                    
                    tables_list = []
                    post_decode_info = []

                    for inner_element_idx in range(0, len(data_json["elements"][root_element_idx]["elements"])):
                        
                        current_entry = data_json["elements"][root_element_idx]["elements"][inner_element_idx]

                        if current_entry["type"] == "table":                        
                            tables_list.append(handleEncodingTable(current_entry))
                        elif len(tables_list) and current_entry["type"] == "paragraph"\
                                and "code" in current_entry["attributes"]:
                            
                            post_decode_info = current_entry["elements"]

                    encodings.append({
                            "caption": "",
                            "tables": tables_list,
                            "postdecode": post_decode_info
                        })

                else:
                    # enum all next titles with lesser level
                    table_caption = ""
                    for element_idx in range(root_element_idx + 1, len(data_json["elements"])):
                        
                        # for every lesser title
                        if data_json["elements"][element_idx]["type"] == "title":
                            if data_json["elements"][element_idx]["level"] == 3:
                                table_caption = data_json["elements"][element_idx]["text"]

                                tables_list = []
                                post_decode_info = []

                                for inner_element_idx in range(0, len(data_json["elements"][element_idx]["elements"])):
                        
                                    current_entry = data_json["elements"][element_idx]["elements"][inner_element_idx]

                                    # lesser title has a table
                                    if current_entry["type"] == "table":                        
                                        tables_list.append(handleEncodingTable(current_entry))
                                    elif len(tables_list) and current_entry["type"] == "paragraph"\
                                            and "code" in current_entry["attributes"]:
                                        
                                        post_decode_info = current_entry["elements"]

                                encodings.append({
                                        "caption": table_caption,
                                        "tables": tables_list,
                                        "postdecode": post_decode_info
                                    })
                                              
                            else:
                                break # another top title



    #if len(encodings) == 0:
    #    breakpoint()

    return encodings

def handleSectionFormat(data_json):

    format_table = None
    formats = []

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "format":
            format_table = element["elements"][0]
            break

    for current_row in format_table["rows"]:

        if len(elementsToText(current_row["columns"][1]).strip()) == 0:
            continue

        formats.append(
                { 
                    "name": elementsToText(current_row["columns"][0]).strip(), 
                    "features": elementsToText(current_row["columns"][1]).strip(),
                    "description": elementsToText(current_row["columns"][2]).strip() 
                }
            )
    
    return formats

def handleSectionOperation(data_json):

    operation = []

    for element in data_json["elements"]:
        text = element["text"]

        if text.find(":") != -1:
            text = text[:text.find(":")]
        
        text = text.strip().lower()

        if text in ["operation", "operations"]:
            operation = element["elements"]
            break

    return operation

def handleNanoSectionFormat(data_json):

    format_table = None
    formats = []

    for element in data_json["elements"]:
        text = element["text"][:element["text"].find(":")].strip()
        if text.lower() == "assembly":
            format_table = element["elements"][0]
            break

    for current_row in format_table["rows"]:

        if len(elementsToText(current_row["columns"][1]).strip()) == 0:
            continue

        formats.append(
                { 
                    "name": elementsToText(current_row["columns"][0]).strip(), 
                    "features": elementsToText(current_row["columns"][1]).strip(),
                    "description": elementsToText(current_row["columns"][2]).strip() 
                }
            )
    
    return formats

def handleNanoSectionOperation(data_json):

    operation = []

    for element in data_json["elements"]:
        text = element["text"]

        if text.find(":") != -1:
            text = text[:text.find(":")]
        
        text = text.strip().lower()

        if text in ["operation", "operations"]:
            operation = element["elements"]
            break

    return operation

def createIndexDoc(path, path_out, title, index_name, pdf_version, new_format = False):

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

                    if not new_format:
                        indexed_table["index"].append( {
                            "filename": path_out + "/" + file,
                            "encoding": handleSectionEncoding(data_json),
                            "format": handleSectionFormat(data_json),
                            "operation": handleNanoSectionOperation(data_json)
                        })
                    else:
                        indexed_table["index"].append( {
                            "filename": path_out + "/" + file,
                            "encoding": handleNanoSectionEncoding(data_json),
                            "format": handleNanoSectionFormat(data_json),
                            "operation": handleSectionOperation(data_json)
                        })

    return [indexed_table]

def makeAllMips16Indexes():
    indexes = []
    indexes += createIndexDoc("gen/mips16/ase_16", "html/mips16/ase_16", "MIPS ASE-16", "mips16_index", "MD00076-2B-MIPS1632-AFP-02.63")
    indexes += createIndexDoc("gen/mips16/ase_16e2", "html/mips16/ase_16e2", "MIPS ASE-16e2", "mips16_index", "MD01172-2B-MIPS16e2-AFP-01.00")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("Mips16 ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › mips16")
    text.append(CloseTag("div"))
    
    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "350"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for fmt_element in element["format"]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/mips16/"):-5] + ".html"}))
                ins_table.append(fmt_element["name"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["features"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/mips16/mips16_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/mips16/mips16_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)
        


def makeAllMipsIndexes():

    indexes = []

    indexes += createIndexDoc("gen/mips/mips_6_6", "html/mips/mips_6_6", "MIPS ISA Reference", "mips_index", "MD00087-2B-MIPS64BIS-AFP-6.06")
    indexes += createIndexDoc("gen/mips/ase_3d", "html/mips/ase_3d", "MIPS ASE-3D ISA Reference", "mips_index", "MD00099-2B-MIPS3D64-AFP-02.61")
    indexes += createIndexDoc("gen/mips/ase_dsp", "html/mips/ase_dsp", "MIPS ASE-DSP ISA Reference", "mips_index", "MD00375-2B-MIPS64DSP-AFP-03.02")
    indexes += createIndexDoc("gen/mips/ase_mcu", "html/mips/ase_mcu", "MIPS ASE-MCU ISA Reference", "mips_index", "MD00834-2B-MUCON-AFP-01.03")
    indexes += createIndexDoc("gen/mips/ase_msa", "html/mips/ase_msa", "MIPS ASE-MSA ISA Reference", "mips_index", "MD00868-1D-MSA64-AFP-01.12")
    indexes += createIndexDoc("gen/mips/ase_mt", "html/mips/ase_mt", "MIPS ASE-MT ISA Reference", "mips_index", "MD00378-2B-MIPS32MT-AFP-01.12")
    indexes += createIndexDoc("gen/mips/ase_smart", "html/mips/ase_smart", "MIPS ASE-SMART ISA Reference", "mips_index", "MD00101-2B-SMARTMIPS32-AFP-03.00")
    indexes += createIndexDoc("gen/mips/ase_vz", "html/mips/ase_vz", "MIPS ASE-VZ ISA Reference", "mips_index", "MD00847-2B-VZMIPS64-AFP-01.06")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("Mips ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › mips")
    text.append(CloseTag("div"))
    
    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "350"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for fmt_element in element["format"]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/mips/"):-5] + ".html"}))
                ins_table.append(fmt_element["name"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["features"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/mips/mips_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/mips/mips_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)
        

def makeAllMicroMipsIndexes():

    indexes = []

    indexes += createIndexDoc("gen/micromips/micromips_6_5", "html/micromips/micromips_6_5", "MICROMIPS ISA Reference", "micromips_index", "MD00594-2B-microMIPS64-AFP-6.05")
    indexes += createIndexDoc("gen/micromips/ase_dsp", "html/micromips/ase_dsp", "MICROMIPS ASE-DSP ISA Reference", "micromips_index", "MD00765-2B-microMIPS64DSP-AFP-03.02")
    indexes += createIndexDoc("gen/micromips/ase_mcu", "html/micromips/ase_mcu", "MICROMIPS ASE-MCU ISA Reference", "micromips_index", "MD00838-2B-microMIPS32MUCON-AFP-01.03")
    indexes += createIndexDoc("gen/micromips/ase_mt", "html/micromips/ase_mt", "MICROMIPS ASE-MT ISA Reference", "micromips_index", "MD00768-1C-microMIPS32MT-AFP-01.12")
    indexes += createIndexDoc("gen/micromips/ase_vz", "html/micromips/ase_vz", "MICROMIPS ASE-VZ ISA Reference", "micromips_index", "MD00849-2B-VZmicroMIPS64-AFP-01.06")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("MicroMips ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › micromips")
    text.append(CloseTag("div"))
    
    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "350"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for fmt_element in element["format"]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/micromips/"):-5] + ".html"}))
                ins_table.append(fmt_element["name"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["features"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/micromips/micromips_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/micromips/micromips_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)

def makeAllNanoMipsIndexes():

    indexes = []

    indexes += createIndexDoc("gen/nanomips/main", "html/nanomips/main", "NANOMIPS ISA Reference", "nanomips_index", "MIPS_nanomips32_ISA_TRM_01_01_MD01247", True)
    indexes += createIndexDoc("gen/nanomips/ase_dsp", "html/nanomips/ase_dsp", "NANOMIPS ASE-DSP ISA Reference", "nanomips_index", "MIPS_nanoMIPS32_DSP_00_04_MD01249")
    indexes += createIndexDoc("gen/nanomips/ase_mt", "html/nanomips/ase_mt", "NANOMIPS ASE-MT ISA Reference", "nanomips_index", "MIPS_nanoMIPS32_MT_TRM_01_17_MD01255")

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag("NanoMips ISA", text, "../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../"}))
    text.append("/home/arch-index/")
    text.append(CloseTag("a"))
    text.append(" › nanomips")
    text.append(CloseTag("div"))
    
    text.append(OpenTag('div', attributes={"id": "body"}))

    ins_table = HtmlText()
    ins_table.append(OpenTag("table", attributes={"id": "index_table"}))

    for index in indexes:

        ins_table.append(OpenTag("tr"))
        
        ins_table.append(OpenTag("th", attributes={"width": "350"}))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_head"}))
        ins_table.append(index["title"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))
        
        ins_table.append(OpenTag("th", attributes={"width": "200"}))
        ins_table.append(CloseTag("th"))

        ins_table.append(OpenTag("th"))
        ins_table.append(OpenTag('h1', attributes={"id": "doc_version"}))
        ins_table.append(index["pdf_version"])
        ins_table.append(CloseTag("h1"))
        ins_table.append(CloseTag("th"))

        ins_table.append(CloseTag("tr"))  
        
        for element in index["index"]:
            for fmt_element in element["format"]:
                ins_table.append(OpenTag("tr"))
                
                ins_table.append(OpenTag("td"))
                ins_table.append(OpenTag('a', attributes={"href": "./" + element["filename"][len("html/nanomips/"):-5] + ".html"}))
                ins_table.append(fmt_element["name"])
                ins_table.append(CloseTag("a"))
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["features"])
                ins_table.append(CloseTag("td"))

                ins_table.append(OpenTag("td"))
                ins_table.append(fmt_element["description"])
                ins_table.append(CloseTag("td"))

                ins_table.append(CloseTag("tr"))        

    ins_table.append(CloseTag("table"))

    text.append(ins_table)
    text.append(CloseTag("div"))

    text.append(CloseTag('body'))
    
    with open("html/nanomips/nanomips_index.html", "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
    
    with open("gen/nanomips/nanomips_encoder_data.json", "w") as fd:
        json.dump(indexes, fd, indent = 4)


def makeAllIndexes():
    makeAllMipsIndexes()
    makeAllMips16Indexes()
    makeAllMicroMipsIndexes()
    makeAllNanoMipsIndexes()

#makeAllFullDocs()
#makeAllIndexes()


