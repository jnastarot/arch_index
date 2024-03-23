import sys
import math
import re
import functools

import pdfhelper
from pdfminer.layout import *
from htmltext import *
from json2html import *
from processing_helper import *


def sort_topdown_ltr_prec_by_3(a, b):
    aa = a.bounds()
    bb = b.bounds()

    if abs(aa.y1() - bb.y1()) > 3:
        if aa.y1() < bb.y1(): return -1
        if aa.y1() > bb.y1(): return 1

    if aa.x1() < bb.x1(): return -1
    if aa.x1() > bb.x1(): return 1
    return 0

class avr32ManParser(object):
    def __init__(self, outputDir, docname, laParams):
        self.outputDir = outputDir
        self.docname = docname
        self.laParams = laParams
        self.yBase = 0
        self.success = 0
        self.fail = 0
        
        self.instName = ""
        self.instCategory = ""
        self.instFeature = ""
        self.instDescription = ""

        self.y_offset = 0
        self.objects = []
        self.__title_stack = []
        self.titles_list = [
            "architecture revision:",
            "architecture revision",
            "description",
            "operation:",
            "operands:",
            "syntax:",
            "example:",
            "example",
            "status flags",
            "status flags:",
            "status flag:",
            "opcode:",
            "opcode",
            "opcode(s):",
            "opcode(s)",
            "format",
            "format:",
            "note:"
        ]
        self.enum_data_map = {
            "": [1],
            "none": [1],
            "i.": [1],
            "i": [1],
            "format i:": [1],
            "format i:i": [1],
            "ii.": [2],
            "ii": [2],
            "format ii:": [2],
            "format  ii:": [2],
            "iii.": [3],
            "iii": [3],
            "format iii:": [3],
            "format  iii:": [3],
            "iv.": [4],
            "format iv:": [4],
            "v.": [5],
            "format v:": [5],
            "vi.": [6],
            "format vi:": [6],
            "i, ii.": [1, 2],
            "i,ii": [1, 2],
            "i,ii.": [1, 2],
            "i-ii.": [1, 2], 
            "format i, ii:": [1, 2],
            "ii, iii": [2, 3],
            "ii, iii.": [2, 3],
            "i, ii, iii.": [1, 2, 3],
            "i-iii.": [1, 2, 3],
            "i, iv.": [1, 4],
            "iii, vi.": [3, 4],
            "format iii, iv:": [3, 4],
            "i, ii, iii, iv.": [1, 2, 3, 4],
            "i-ii, iv-v.": [1, 2, 4, 5],
            "i-v.": [1, 2, 3, 4, 5],
            "i-vi.": [1, 2, 3, 4, 5, 6]
        }

    def isTitleElement(self, element):
        
        if not isinstance(element, pdfhelper.CharCollection):
            return False

        if element.font_name().find("Bold") != -1:
            if str(element).strip().lower() in self.titles_list:
                return True

        return False

    def replaceCodeForCollection(self, lines):
        for line in lines:
            if isinstance(line, pdfhelper.CharCollection):
                for char in line.chars:
                    if isinstance(char, LTChar):
                        char.fontname = "code"
        start_x = 0
        if len(lines):
            start_x = lines[0].x1()

        for line in lines[1:]:
            indent = int((line.bounds().x1() - start_x) / 6)
            line.chars = [pdfhelper.FakeChar(' ')] * indent + line.chars

    def findItemFromInstInfoByIndex(self, idx, instinf_list):

        for list_idx in range(0, len(instinf_list)):
            index_str = ""    
            if instinf_list[list_idx][0] == None or len(instinf_list[list_idx][0]):
                index_str = str(instinf_list[list_idx][0]).strip().lower()
            
            if index_str == "" or index_str in self.enum_data_map:
                if index_str == "" or idx in self.enum_data_map[index_str]:
                    return instinf_list[list_idx]
            #else:
            #    breakpoint()

        #breakpoint()

    def replaceSpecSymbols(self, element): # convert silly symbols to normal  

        try:
            if isinstance(element, pdfhelper.CharCollection):

                idx = 0
                while idx < len(element.chars):

                    if isinstance(element.chars[idx], LTChar):
                        if element.chars[idx]._text in ['\u2014', '\u2212']: 
                            element.chars[idx]._text = " - "
                        elif element.chars[idx]._text in ['\u2013']: 
                            element.chars[idx]._text = "-"
                        elif element.chars[idx]._text in ['\u201c', '\u201d']:
                            element.chars[idx]._text = "\""
                        elif element.chars[idx]._text == '\u00ab':
                            element.chars[idx]._text = "<<"
                        elif element.chars[idx]._text == '\u2019':
                            element.chars[idx]._text = "'"
                        elif element.chars[idx]._text == '\u2217':
                            element.chars[idx]._text = "*"
                        elif element.chars[idx]._text == '\u2265':
                            element.chars[idx]._text = ">="
                        elif element.chars[idx]._text == '\u2264':
                            element.chars[idx]._text = "<="
                        elif element.chars[idx]._text == '\u2260':
                            element.chars[idx]._text = "!="
                        elif element.chars[idx]._text == '\uf020':
                            element.chars[idx]._text = " U"
                        elif element.chars[idx]._text == '\u00b1':
                            element.chars[idx]._text = "+-"
                        elif element.chars[idx]._text == '\u221e':
                            element.chars[idx]._text = "inf"
                        elif element.chars[idx]._text == '\uf0e1':
                            element.chars[idx]._text = "("
                        elif element.chars[idx]._text == '\uf0f1':
                            element.chars[idx]._text = ")"
                        elif element.chars[idx]._text == '←':
                            element.chars[idx]._text = "="
                        elif element.chars[idx]._text == '→':
                            element.chars[idx]._text = "->"
                        elif element.chars[idx]._text == '¬':
                            element.chars[idx]._text = "~"                            
                        elif element.chars[idx]._text == '∧':
                            result_char = ""
                            
                            if idx and element.chars[idx - 1].get_text() != " ":
                                result_char += " "
                            result_char += "AND"
                            if len(element.chars) < (idx + 1) and element.chars[idx + 1].get_text() != " ":
                                result_char += " "

                            element.chars[idx]._text = result_char
                        elif element.chars[idx]._text == '∨':
                            result_char = ""
                            
                            if idx and element.chars[idx - 1].get_text() != " ":
                                result_char += " "
                            result_char += "OR"
                            if len(element.chars) < (idx + 1) and element.chars[idx + 1].get_text() != " ":
                                result_char += " "

                            element.chars[idx]._text = result_char
                        elif element.chars[idx]._text == '⊕':
                            result_char = ""
                            
                            if idx and element.chars[idx - 1].get_text() != " ":
                                result_char += " "
                            result_char += "XOR"
                            if len(element.chars) < (idx + 1) and element.chars[idx + 1].get_text() != " ":
                                result_char += " "

                            element.chars[idx]._text = result_char

                    idx += 1

        except Exception as e:
            print("Failed to prepare for ", str(idx), " ", str(element))

        return element    

    def mergeText(self, lines, isinTable):
       
        if len(lines) == 0: return []
        
        lines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
        merged = [lines[0]]
        current_title = ""
        for line in lines[1:]:
            
            last = merged[-1]
            if isinstance(last, pdfhelper.List) and len(last.items):            
                last = last.items[-1]

            if isinstance(last, pdfhelper.CharCollection) \
                    and str(line).strip().lower() in self.titles_list:
                current_title = str(line).strip().lower()

            if isinstance(line, pdfhelper.CharCollection) \
                    and isinstance(last, pdfhelper.CharCollection)\
                    and str(line).strip().lower() not in self.titles_list\
                    and str(last).strip().lower() not in self.titles_list\
                    and current_title != "example:":

                is_code = False
                for char in line.chars:
                    if isinstance(char, LTChar):
                        if char.fontname.find("code")  != -1:
                            is_code = True
                            break
                if not is_code:
                    for char in last.chars:
                        if isinstance(char, LTChar):
                            if char.fontname.find("code")  != -1:
                                is_code = True
                                break

                if is_code == True:
                    merged.append(line)
                    continue

                same_x = pdfhelper.pretty_much_equal(line.rect.x1(), last.rect.x1())
                same_size = last.font_size() == line.font_size()
                decent_descent = abs(line.rect.y1() - last.rect.y2()) < 2.3

                if same_x and same_size and decent_descent:
                    last.append(line)
                else:
                    merged.append(line)
            else:
                merged.append(line)

        return merged    
    
    def handleArchRev(self):
        
        arch_rev_lines = []
        arch_title = None

        start_desc_section = 0
        while start_desc_section < len(self.objects): 
            if isinstance(self.objects[start_desc_section], pdfhelper.CharCollection):
                
                if self.isTitleElement(self.objects[start_desc_section]) \
                        and str(self.objects[start_desc_section]).strip().lower() == "architecture revision:":
                    
                    arch_title = self.objects[start_desc_section]
                    del self.objects[start_desc_section]
                    break
                
                start_desc_section += 1
            else:
                start_desc_section += 1

        end_desc_section = start_desc_section
        while end_desc_section < len(self.objects): 
            if isinstance(self.objects[end_desc_section], pdfhelper.CharCollection):
                
                if self.isTitleElement(self.objects[end_desc_section]):
                    break
                
                arch_rev_lines.append(self.objects[end_desc_section])
                del self.objects[end_desc_section]
            else:
                end_desc_section += 1

        arch_level = 0
        for item in arch_rev_lines:
            text = str(item).strip()
            if text.find("1") != -1:
                arch_level = 1
            elif text.find("2") != -1:
                arch_level = 2
            elif text.find("3") != -1:
                arch_level = 3

        if arch_level:
            return (arch_title, [pdfhelper.make_sint_char_collection("Rev" + str(arch_level) + "+", "Helvetica")])
        else:
            return (arch_title, [])
        

    def handleDescTables(self, caption):
        
        start_desc_section = 0
        while start_desc_section < len(self.objects): 
            if isinstance(self.objects[start_desc_section], pdfhelper.CharCollection):
                
                if self.isTitleElement(self.objects[start_desc_section]) \
                        and str(self.objects[start_desc_section]).strip().lower() == caption:
                    break
                
                start_desc_section += 1
            else:
                start_desc_section += 1

        end_desc_section = start_desc_section + 1
        while end_desc_section < len(self.objects): 
            if isinstance(self.objects[end_desc_section], pdfhelper.CharCollection):
                
                if self.isTitleElement(self.objects[end_desc_section]):
                    break
                
                end_desc_section += 1
            else:
                end_desc_section += 1
        
        if (end_desc_section - (start_desc_section + 1)) == 1:
            title_item = self.objects[start_desc_section]
            flag_items = [[[], [self.objects[start_desc_section + 1]]]]
            del self.objects[start_desc_section: end_desc_section]
            return (title_item, flag_items)
        

        flag_items = []
        data_items = []

        for idx in range(start_desc_section + 1, end_desc_section):
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.objects[idx].x1() < 160:
                    if (self.objects[idx].x2() - self.objects[idx].x1()) >= 85:
                        
                        dot_index = 0
                        while dot_index < len(self.objects[idx].chars):
                            if self.objects[idx].chars[dot_index].get_text() == ".":
                                dot_index += 1
                                break
                            dot_index += 1
                        
                        if dot_index >= len(self.objects[idx].chars) - 1:
                            flag_items.append([self.objects[idx], []])
                        else:
                            collection = pdfhelper.divide_collection_by_index(self.objects[idx], dot_index)
                            flag_items.append([collection[0], []])

                            if len(str(collection[1]).strip()):
                                data_items.append(collection[1])
                    else:
                        flag_items.append([self.objects[idx], []])
                else:
                    data_items.append(self.objects[idx])

        if len(flag_items) == 0:
            flag_items.append([pdfhelper.make_sint_char_collection("", "Helvetica"), []])

        for data_item in data_items:
                
            item_handled = False
            flag_item_idx = 0
            while flag_item_idx < len(flag_items):
                
                if len(flag_items) == 1 \
                        or data_item.y2() < flag_items[flag_item_idx][0].y1():
                    
                    # prev
                    if flag_item_idx == 0:
                        flag_items[0][1].append(data_item)
                    else:
                        flag_items[flag_item_idx - 1][1].append(data_item)
                    
                    item_handled = True
                    break
                
                flag_item_idx += 1     

            if not item_handled: # for last
                flag_items[-1][1].append(data_item)

        title_item = self.objects[start_desc_section]

        idx = start_desc_section
        while idx < end_desc_section:
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                del self.objects[idx]
                end_desc_section -= 1
            else:
                idx += 1

        return (title_item, flag_items)

    def generateInstInfoTable(self, operation_data, syntax_data, operands_data, arch_data, opcode_data):

        table_data = []
        max_index = 0

        for idx in range(0, len(operation_data[1])):
            index_str = ""    
            if len(operation_data[1][idx][0]):
                index_str = str(operation_data[1][idx][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            else:
                breakpoint()

        for idx in range(0, len(syntax_data[1])):
            index_str = ""    
            if len(syntax_data[1][idx][0]):
                index_str = str(syntax_data[1][idx][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            else:
                breakpoint()

        for idx in range(0, len(operands_data[1])):
            index_str = ""    
            if len(operands_data[1][idx][0]):
                index_str = str(operands_data[1][idx][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            else:
                breakpoint()
     
        # format | syntax | operation | operands | revision | opcode
        title_row_data = [
                [pdfhelper.make_sint_char_collection("Format", "ArialMT")], 
                [syntax_data[0]] if len(syntax_data[0]) else [pdfhelper.make_sint_char_collection("Syntax", "ArialMT")], 
                [operation_data[0]] if len(operation_data[0]) else [pdfhelper.make_sint_char_collection("Operation", "ArialMT")], 
                [operands_data[0]] if len(operands_data[0]) else [pdfhelper.make_sint_char_collection("Operands", "ArialMT")],
                [arch_data[0]] if arch_data[0] != None else [pdfhelper.make_sint_char_collection("Architecture revision", "ArialMT")],
                [pdfhelper.make_sint_char_collection("Opcode", "ArialMT")]
            ]

        opcode_table = []

        for opcode in opcode_data:
            opcode_row = []

            format_table = []
            format_table_name_row = []
            format_table_size_row = []
            
            for fmt_item in opcode[1]:
                item_size = 0
                item_texts = []
                
                if fmt_item["bitstring"] == True:
                    bitstring = ""
                    for text in fmt_item["text"]:
                        bitstring += str(text).strip()
                    
                    item_texts = [pdfhelper.make_sint_char_collection(bitstring, "Helvetica")]
                else:
                    item_texts = fmt_item["text"]

                addend = 1 if len(item_texts) else 0
                item_size = fmt_item["bit_start"] - fmt_item["bit_end"] + addend

                format_table_name_row.append(item_texts)
                format_table_size_row.append([pdfhelper.make_sint_char_collection(str(item_size), "Helvetica")])
            
            format_table.append(format_table_name_row)
            format_table.append(format_table_size_row)

            opcode_row.append(pdfhelper.Table(format_table, True, len(format_table[0])))

            opcode_table.append((opcode[0], opcode_row))

        table_data.append(title_row_data)

        for idx in range(1, max_index + 1):
            operation = self.findItemFromInstInfoByIndex(idx, operation_data[1])
            syntax = self.findItemFromInstInfoByIndex(idx, syntax_data[1])
            operand = self.findItemFromInstInfoByIndex(idx, operands_data[1])
            opcode = self.findItemFromInstInfoByIndex(idx, opcode_table)
            
            if operation == None:
                 operation = [[], [], [], []]
            
            #if syntax == None or opcode == None:
            #   breakpoint()

            row_data = [[pdfhelper.make_sint_char_collection(str(idx), "ArialMT")], syntax[1], operation[1], operand[1], [], opcode[1]]

            table_data.append(row_data)

        for item in table_data[1:]:
            lines = item[1]
            lines.sort(key=functools.cmp_to_key(sort_topdown_ltr_prec_by_3))

            merged = [lines[0]]
            for line in lines[1:]:            
                last = merged[-1]

                if abs(line.y1() - last.y1()) < 3:
                    
                    while len(last.chars) and last.chars[-1].get_text() == "\n":
                        del last.chars[-1]

                    if last.chars[-1].get_text() != " " and  line.chars[0].get_text() != " ":
                        last.chars.append(pdfhelper.FakeChar(' '))

                    last.append(line)
                else:
                    merged.append(line)

            item[1] = merged

        for row in table_data[1:]:
            self.replaceCodeForCollection(row[2])
            self.replaceCodeForCollection(row[3])
            
        for row in table_data[1:]:
            row[4] = arch_data[1]
        
        self.objects.insert(0, pdfhelper.Table(table_data, True, len(table_data[0])))
        self.objects[0].set_y1(0)

        return

    def handleStatusFlags(self):
        
        start_flags_section = 0
        while start_flags_section < len(self.objects): 
            if not isinstance(self.objects[start_flags_section], pdfhelper.CharCollection)\
                or (isinstance(self.objects[start_flags_section], pdfhelper.CharCollection)\
                    and (not self.isTitleElement(self.objects[start_flags_section])\
                            or str(self.objects[start_flags_section]).strip().lower() not in ["status flags:", "status flags", "status flag:"])):
                
                start_flags_section += 1
            else:
                break       

        end_flags_section = start_flags_section + 1
        while end_flags_section < len(self.objects): 
            if isinstance(self.objects[end_flags_section], pdfhelper.CharCollection)\
                and not self.isTitleElement(self.objects[end_flags_section]):
                
                end_flags_section += 1
            else:
                break     

        flag_items = []
        data_items = []

        for idx in range(start_flags_section + 1, end_flags_section):
            if self.objects[idx].x1() < 200:
                flag_items.append([[self.objects[idx]], []])
            else:
                data_items.append(self.objects[idx])


        for data_item in data_items:
                
            item_handled = False
            flag_item_idx = 0
            while flag_item_idx < len(flag_items):
                
                if data_item.y2() < flag_items[flag_item_idx][0][0].y1():
                    # prev
                    if flag_item_idx == 0:
                        flag_items[0][1].append(data_item)
                    else:
                        flag_items[flag_item_idx - 1][1].append(data_item)
                    
                    item_handled = True
                    break
                
                flag_item_idx += 1     

            if not item_handled: # for last
                flag_items[-1][1].append(data_item)

        del self.objects[start_flags_section + 1 : end_flags_section]
        self.objects.insert(start_flags_section + 1, pdfhelper.Table(flag_items, True, len(flag_items[0])))
        self.objects[start_flags_section + 1].set_y1(self.objects[start_flags_section].y1() + 2)
        return


    def preparseOpcodeFormat(self, format):
        preparsed_formats = []
        format_row_desc = []

        item_idx = 0
        last_format_start =  0
        for item_idx in range(0, len(format[1])):

            item = format[1][item_idx]
            if isinstance(item, pdfhelper.Table):

                bit_hints = format[1][last_format_start:item_idx]

                format_sub_row_desc = [{"hint": -1, "text": []} for i in item.data_storage]

                columns_data = item.columns_data()
                
                for hint in bit_hints:
                    for idx in range(0, len(columns_data)):
                        ref_value_start = columns_data[idx]
                        ref_value_end = ref_value_start + 1000
                        
                        if (idx + 1) < len(columns_data):
                            ref_value_end = columns_data[idx + 1]
                        
                        if ref_value_start <= hint.x1() and ref_value_end > hint.x1():
                            format_sub_row_desc[idx]["hint"] = int(str(hint).strip())

                for column_idx in range(0, len(item.data_storage)):
                    data = item.data_storage[column_idx]
                    format_sub_row_desc[column_idx]["text"] = data

                # fix up bad rows ;(
                if False and len(item.data_storage) != 16:
                    idx = 0
                    last_hint_num = -1
                    last_hint_idx = -1
                    while idx < len(format_sub_row_desc):
                        if format_sub_row_desc[idx]["hint"] != -1:
                            if last_hint_num == -1:
                                last_hint_num = format_sub_row_desc[idx]["hint"]
                                last_hint_idx = idx
                            else:
                                hint_delta = last_hint_num - format_sub_row_desc[idx]["hint"]
                                idx_delta = idx - last_hint_idx 

                                if hint_delta != idx_delta:
                                    for i in range(0, (hint_delta - idx_delta)):
                                        format_sub_row_desc.insert(idx, {"hint": -1, "text": []})

                                    idx += (hint_delta - idx_delta)

                                last_hint_num = format_sub_row_desc[idx]["hint"]
                                last_hint_idx = idx

                        idx += 1

                format_row_desc.append(format_sub_row_desc)
                last_format_start = item_idx + 1
        
        # split bit lines and add missed hints
        for row in format_row_desc:
            start_bit_line_idx = -1
            previous_bit_idx = -1

            for idx in range(0, len(row)):
                if len(row[idx]["text"]) == 1\
                        and (str(row[idx]["text"][0]).strip() == "0" or str(row[idx]["text"][0]).strip() == "1"):
                    
                    if start_bit_line_idx == -1:
                        start_bit_line_idx = idx
                        previous_bit_idx = idx

                        # try to add missed hints
                        if idx > 1:
                            if row[idx - 1]["hint"] == -1:
                                row[idx - 1]["hint"] = row[0]["hint"] - (idx - 1)
                    else:
                        if start_bit_line_idx != previous_bit_idx:
                            row[previous_bit_idx]["hint"] = -1

                        previous_bit_idx = idx
                        
                else:
                    if previous_bit_idx != -1 and row[previous_bit_idx]["hint"] == -1:
                        row[previous_bit_idx]["hint"] = row[0]["hint"] - previous_bit_idx

                    if previous_bit_idx != -1 and row[idx]["hint"] == -1:
                            row[idx]["hint"] = row[0]["hint"] - idx

                    start_bit_line_idx = -1
                    previous_bit_idx = -1

        return format_row_desc

    def handleOpcode(self):

        start_opcode_section = 0
        while start_opcode_section < len(self.objects): 
            if not isinstance(self.objects[start_opcode_section], pdfhelper.CharCollection)\
                or (isinstance(self.objects[start_opcode_section], pdfhelper.CharCollection)\
                    and (not self.isTitleElement(self.objects[start_opcode_section])\
                            or str(self.objects[start_opcode_section]).strip().lower() not in ["opcode:", "opcode", "opcode(s):", "opcode(s)"])):
                
                start_opcode_section += 1
            else:
                break       

        end_opcode_section = start_opcode_section + 1
        while end_opcode_section < len(self.objects): 
            if not self.isTitleElement(self.objects[end_opcode_section]):
                
                end_opcode_section += 1
            else:
                break

        formats = []
        current_format_data = []
        current_title = None

        idx = start_opcode_section + 1
        while idx < end_opcode_section:

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                is_sub_title = False
                for char in self.objects[idx].chars:
                    if isinstance(char, LTChar):
                        if char.fontname.find("Bold") != -1:
                            is_sub_title = True
                            break
                if not is_sub_title:
                    is_sub_title = str(self.objects[idx]).strip().find(":") == (len(str(self.objects[idx]).strip()) - 1)

                if is_sub_title:
                    if len(current_format_data):
                        formats.append((current_title, current_format_data))
                        current_format_data = []

                    current_title = self.objects[idx]
                else:
                    current_format_data.append(self.objects[idx])
            else:
                current_format_data.append(self.objects[idx])

            idx += 1
        
        if len(current_format_data):
            formats.append((current_title, current_format_data))

        preparsed_formats = []

        for format in formats:
            format_items = []
            for row in self.preparseOpcodeFormat(format):
                 
                current_item = {
                    "bit_start": -1,
                    "bit_end": -1,
                    "text": [],
                    "bitstring": False
                }

                idx = 0
                while idx < len(row):
                    
                    item = row[idx]
                    
                    is_bit_element = (len(item["text"]) and (str(item["text"][0]).strip() == "0" or str(item["text"][0]).strip() == "1"))

                    if is_bit_element:
                        current_item["bit_start"] = item["hint"]
                        current_item["bit_end"] = item["hint"]
                        current_item["text"] += item["text"]
                        current_item["bitstring"] = True
                        current_item["bit_end"] -= len(item["text"]) - 1
                        idx += 1
                                                    
                        if idx < len(row):
                            item = row[idx]
                        
                        is_bit_element = (len(item["text"]) and (str(item["text"][0]).strip() == "0" or str(item["text"][0]).strip() == "1"))
                        
                        while idx < len(row) and is_bit_element:
                            
                            current_item["text"] += item["text"]
                            current_item["bit_end"] -= len(item["text"])

                            idx += 1
                                                    
                            if idx < len(row):
                                item = row[idx]
                            else:
                                break

                            is_bit_element = (len(item["text"]) and (str(item["text"][0]).strip() == "0" or str(item["text"][0]).strip() == "1"))

                        format_items.append(current_item)
                        current_item = {
                                        "bit_start": -1,
                                        "bit_end": -1,
                                        "text": [],
                                        "bitstring": False
                                    }
                    else:
                        current_item["bit_start"] = item["hint"]
                        current_item["bit_end"] = item["hint"]
                        current_item["text"] += item["text"]
                        idx += 1
                        
                        if idx < len(row):
                            item = row[idx]

                        is_bit_element = (len(item["text"]) and (str(item["text"][0]).strip() == "0" or str(item["text"][0]).strip() == "1"))

                        while idx < len(row):

                            if len(current_item["text"]) != 0 and item["hint"] != -1:

                                if len(item["text"]) == 0:
                                    current_item["bit_end"] = item["hint"]
                                    current_item["text"] += item["text"]
                                    idx += 1
                                                            
                                    if idx < len(row):
                                        item = row[idx]
                                    else:
                                        break
                                break
                            
                            if is_bit_element:
                                break

                            current_item["bit_end"] -= 1
                            current_item["text"] += item["text"]
                            idx += 1
                                                    
                            if idx < len(row):
                                item = row[idx]
                            else:
                                current_item["bit_end"] -= 1 # last hint
                                break
                            
                            is_bit_element = (len(item["text"]) and (str(item["text"][0]).strip() == "0" or str(item["text"][0]).strip() == "1"))

                        format_items.append(current_item)
                        current_item = {
                                        "bit_start": -1,
                                        "bit_end": -1,
                                        "text": [],
                                        "bitstring": False
                                    }
                        
                if current_item["bit_start"] != -1:
                    current_item["bit_end"] = row[0]["hint"] - 15

                    format_items.append(current_item)

            preparsed_formats.append((format[0], format_items))

        # try concat free space for non bitstring items
        for items in preparsed_formats:
            idx = 0
            while idx < len(items[1]):
                if items[1][idx]["bit_end"] < 0:
                    items[1][idx]["bit_end"] = 0

                if len(items[1][idx]["text"]) == 0:
                    if idx == 0:
                        items[1][idx + 1]["bit_start"] = items[1][idx]["bit_start"]
                    else:
                        items[1][idx - 1]["bit_end"] = items[1][idx]["bit_end"]
                    
                    del items[1][idx]
                else:
                    idx += 1

        for items in preparsed_formats:
            # check for correct hints

            has_error = False
            current_hint = -1
            for element in items[1]:
                if current_hint == -1:
                    current_hint = element["bit_end"]
                else:
                    if (current_hint - 1) != element["bit_start"]:
                        has_error = True
                    current_hint = element["bit_end"]
            if has_error:
                print("----------------------------------Can't parse opcode format ", items[0])

        del self.objects[start_opcode_section: end_opcode_section]
        return preparsed_formats

    def prepareDisplay(self):

        # escase symbols
        for obj in self.objects:
            if isinstance(obj, pdfhelper.Table):

                for row_idx in range(0, obj.rows()):
                    for column_idx in range(0, obj.columns()):
                        
                        for item in obj.get_at(column_idx, row_idx):
                            self.replaceSpecSymbols(item)            

                
            else:
                self.replaceSpecSymbols(obj)

        self.objects.sort(key=functools.cmp_to_key(sort_topdown_ltr_prec_by_3))

        if self.instName == 'STC0.{D,W}':
            del self.objects[19]
            del self.objects[20]
            del self.objects[21]
        elif self.instName == 'STCM.{D,W}':
            del self.objects[48]
            del self.objects[48]
        elif self.instName == 'STHH.W':
            del self.objects[6]
            del self.objects[6]
        elif self.instName == 'STM':
            self.objects.insert(5, pdfhelper.make_sint_char_collection("Operation:", "Helvetica-Bold"))
        elif self.instName == 'STMTS':
            self.objects.insert(5, pdfhelper.make_sint_char_collection("Operation:", "Helvetica-Bold"))

        operation_data = self.handleDescTables("operation:")
        syntax_data = self.handleDescTables("syntax:")
        operands_data = self.handleDescTables("operands:")
        arch_data = []
        
        (arch_title, current_arch_data) = self.handleArchRev()
        while len(current_arch_data) != 0:
            arch_data += current_arch_data
            (arch_title, current_arch_data) = self.handleArchRev()

        if self.instName == 'MVRC.{D,W}': # bug in doc
            operands_data[1][1][0].chars.insert(1, pdfhelper.FakeChar('I'))
        elif self.instName == 'PSAD':
            del operands_data[1][0][0].chars[1:-2]
        elif self.instName == 'PSUBADDS.{UH/SH}':
            operands_data[1][0][0].chars.insert(1, pdfhelper.FakeChar(', II'))
            
        opcode_data = self.handleOpcode()

        self.generateInstInfoTable(
                operation_data, 
                syntax_data, 
                operands_data, 
                (arch_title, arch_data), 
                opcode_data
            )

        self.handleStatusFlags()

        return self.mergeText(self.objects, False)

    def flush(self):
        
        if len(self.objects) == 0:
            return
        
        displayable = self.prepareDisplay()
        
        self.outputFile(displayable)
    
    def processPage(self, page):
        
        proc_page = processedPage(page, 0, False)
        proc_page.cut_off(0, 10000, 50, 725)

        if len(proc_page.objects)\
            and isinstance(proc_page.objects[0], pdfhelper.CharCollection)\
            and proc_page.objects[0].font_name().find("Bold") != -1\
            and proc_page.objects[0].font_size() >= 11\
            and (str(proc_page.objects[0]).find('–') != -1):

            title_items = str(proc_page.objects[0]).split('–')
            inst_name = title_items[0].strip()
            description = title_items[1].strip()
            
            if self.instName != "" and self.instName != inst_name:
                
                if len(self.objects) != 0:
                    #try:
                    self.flush()
                    self.success += 1
                    #except Exception as e:
                    #    print("*** couldn't flush to disk")
                    #    self.fail += 1

                    self.instName = inst_name
                    self.instDescription = description
                    self.y_offset = 0
                    self.objects = []

            if self.instName == "":
                self.instName = inst_name
                self.instDescription = description
                self.y_offset = 0
                self.objects = []

        if self.instName != "":
            
            if len(proc_page.objects) == 0:
                if len(self.objects) != 0:
                    self.flush()

                self.instName = ""
                self.instDescription = ""
                self.y_offset = 0
                self.objects = []
                return
            
            proc_page = processedPage(page, self.y_offset, False) # update page with new y offset

            # shift page and add content
            if len(self.objects):
                proc_page.cut_off(0, 10000, 50, 725)
            else:
                proc_page.cut_off(0, 10000, 95, 725)

            self.y_offset += proc_page.page_heigth 
            self.objects += proc_page.objects

    def outputFile(self, displayable):

        title = self.instName
        path = "%s/%s" % (self.outputDir, title.replace("/", "_").replace(" ", ""))
        print("Writing to %s" % path)

        file_data = self.outputSection(displayable)
        with open(path + ".json", "w") as fd:
            json.dump(file_data, fd, indent = 4)
        with open(path + ".html", "wb") as fd:
            string_ = "<!DOCTYPE html>" + genHtmlDescription(file_data).to_html() 
            fd.write(string_.encode("UTF-8"))
    
    def outputSection(self, displayable):
    
        root_json = {
            "docname": self.docname,
            "rootname": [self.instName, self.instDescription], 
            "elements": [],
            "attributes": []
        }

        root_json["elements"].append({
                    "type": "title",
                    "text": "Operations:",
                    "elements": [],
                    "attributes": ["h2"],
                    "level": 2
                }) 
        
        level = 1
        self.__title_stack = self.__title_stack[0:level]
        self.__title_stack.append("operations:")     

        for element in displayable:
            self.outputElement(root_json, element)
        
        sortDescriptionByTitle(root_json)
        
        return root_json
    
    def outputElement(self, parent_element, element):

        if isinstance(element, pdfhelper.CharCollection):
                        
            if self.outputText(parent_element, element):
                if parent_element["elements"][-1]["type"] == "title":
                    level = parent_element["elements"][-1]["level"] - 1
                    self.__title_stack = self.__title_stack[0:level]
                    self.__title_stack.append("".join(parent_element["elements"][-1]["text"]).strip().lower())

            return
        
        elif isinstance(element, pdfhelper.List):
            
            list_result = {
                "type": "list",
                "elements": [],
                "attributes": []
            }
            
            for item in element.items:
                self.outputElement(list_result, item)
                
                for item in list_result["elements"]:
                    if "p" in item["attributes"]:
                        item["text"] = item["text"][1:-1]

            parent_element["elements"].append(list_result)
            return

        elif isinstance(element, pdfhelper.TableBase):
            
            table_result = {
                "type": "table",
                "rows": [],
                "attributes": []
            }
            
            print_index = -1

            for row in range(0, element.rows()):
                    
                table_row_result = {
                    "type": "row",
                    "columns": [],
                    "attributes": []
                }

                for col in range(0, element.columns()):
                    
                    row_column_result = {
                        "type": "column",
                        "elements": [],
                        "attributes": []
                    }

                    index = element.data_index(col, row)
                    
                    if index <= print_index: 
                        continue
                    
                    index = print_index
                    
                    children = element.get_at(col, row)
                    
                    for child in children:
                        self.outputElement(row_column_result, child)                            
                    
                    size = element.cell_size(col, row)

                    if size[0] > 1: 
                        row_column_result["attributes"].append({"colspan": size[0]})
                    if size[1] > 1: 
                        row_column_result["attributes"].append({"colspan": size[1]})

                    table_row_result["columns"].append(row_column_result)
                table_result["rows"].append(table_row_result)

            parent_element["elements"].append(table_result)
            return
        
        else:
            return
        
    def outputText(self, parent_element, element):
                
        if len(element.chars) == 0: 
            return False
                
        style = pdfhelper.FontStyle(element.chars[0])
        style0 = style

        is_code = False
        for char in element.chars:
            if isinstance(char, LTChar):
                if char.fontname.find("code") != -1:
                    is_code = True

        not_accept_font_modifier = False

        current_paragraph = {
            "type": "paragraph",
            "elements": [],
            "attributes": []
        }
        
        if str(element).strip().lower() in self.titles_list:
            tag = "h2"
            index = 2
            parent_element["elements"].append({
                                        "type": "title",
                                        "text": str(element),
                                        "elements": [],
                                        "attributes": [tag],
                                        "level": index
                                    })
            return True
        
        if is_code == True \
                or (len(self.__title_stack) >= 1 \
                    and (self.__title_stack[-1] == "example:")):
            
            current_paragraph["attributes"].append("code")


            if element.chars[-1].get_text() == '\n':
                del element.chars[-1]
        
            not_accept_font_modifier = True

        current_text_elements = {
            "type": "text",
            "text": "",
            "attributes": []
        }

        is_first_char = True
        prev_char_attributes = []
        
        for char in element.chars:

            string = char.get_text()
            current_char_attributes = []

            if hasattr(char, "fontname") and hasattr(char, "matrix"):

                this_style = pdfhelper.FontStyle(char)
                this_italic = this_style.font_is("Italic")
                this_bold = this_style.font_is("Bold")
                baseline = this_style.compare_baseline(style)

                if not not_accept_font_modifier and this_italic:
                    current_char_attributes.append("italic")

                if not not_accept_font_modifier and this_bold:
                    current_char_attributes.append("strong")

                if baseline != None:
                    if this_style.size < style0.size:
                        current_char_attributes.append(baseline[0])
                    else:
                        current_char_attributes.append(baseline[1])

                if is_first_char:
                    prev_char_attributes = current_char_attributes
                    current_text_elements["attributes"] = prev_char_attributes
                    is_first_char = False

                if prev_char_attributes != current_char_attributes:
                    current_paragraph["elements"].append(current_text_elements)
                    prev_char_attributes = current_char_attributes
                    current_text_elements = {
                            "type": "text",
                            "text": "",
                            "attributes": current_char_attributes
                        }

            current_text_elements["text"] += string

        if len(current_text_elements["text"]):
            current_paragraph["elements"].append(current_text_elements)
        
        parent_element["elements"].append(current_paragraph)
        return True
        
