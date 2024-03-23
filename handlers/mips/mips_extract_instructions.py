import sys
import json

# mips main

# COP1
# 0x10 - .S
# 0x11 - .D
# 0x14 - .W
# 0x15 - .L
# 0x16 - .PS

# COP1X
# S 

# df - 1 | 2
#  1 - .W .D 
#  2 - .B .H .W .D
#  
# df/n - 6
#  .B .H .W .D
#

def handleFormatPostfix(name):
    postfix = name[-2:]
    has_postfix = False
    inst_base_name = ""
    
    if postfix in [".B", ".H", ".W", ".D", ".S", ".L", ".PS"]:
        has_postfix = True
        inst_base_name = name[:-2]
    else:
        inst_base_name = name[0]

    return (has_postfix, inst_base_name, postfix)

def extractSection(section):

    format_section_description = []
    operation_section_string = ""
    section_name = ""
    for operation in section["format"]:
        format_items = section["format"][0]["name"].split()

        (has_postfix, inst_base_name, postfix) = handleFormatPostfix(format_items[0])

        #if len(section["encoding"]) == 1:

        #else:

    for paragraph in section["operation"]:


    return {
            "section": section_name,
            "description": format_section_description,
            "operation": operation_section_string
        }

def extractPDFSections(pdf_document):

    instructions = []

    for section in pdf_document["index"]:
        instructions |= extractSection(section)

    return instructions

def extractArchitecture(pdf_data):
    
    instructions = []

    for pdf_document in pdf_data:
        instructions |= extractPDFSections(pdf_document)

    return instructions
