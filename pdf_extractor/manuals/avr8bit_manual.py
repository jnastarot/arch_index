import sys
import math
import re
import functools

import pdfhelper
from pdfminer.layout import *
from htmltext import *
from json2html import *
from processing_helper import *

cycles_format__ = re.compile(r"table(.*)cycles")


def sort_topdown_ltr_prec_by_3(a, b):
    aa = a.bounds()
    bb = b.bounds()

    if abs(aa.y1() - bb.y1()) > 3:
        if aa.y1() < bb.y1(): return -1
        if aa.y1() > bb.y1(): return 1

    if aa.x1() < bb.x1(): return -1
    if aa.x1() > bb.x1(): return 1
    return 0


class avr8ManParser(object):
    def __init__(self, outputDir, docname, laParams):
        self.outputDir = outputDir
        self.docname = docname
        self.laParams = laParams
        self.yBase = 0
        self.success = 0
        self.fail = 0
        
        self.instName = ""
        self.instDescription = ""
        self.InstIndex = 1

        self.y_offset = 0
        self.objects = []
        self.rects = []
        self.__title_stack = []
        self.titles_list = [
            "description:",
            "description",
            "example:",
            "status register (sreg) and boolean formula",
            "status register and boolean formula",
            "table cycles",
            "words"
        ]
        self.enum_data = [
            "(i)",
            "(ii)",
            "(iii)",
            "(iv)",
            "(v)",
            "(vi)",
            "(vii)",
            "(viii)",
            "(i), (ii)",
            "(i)-(v)",
            "(i)-(iv)",
            "(v)-(viii)"
        ]
        self.enum_data_map = {
            "": [1],
            "(i)": [1],
            "(ii)": [2],
            "(iii)": [3],
            "(iv)": [4],
            "(v)": [5],
            "(vi)": [6],
            "(vii)": [7],
            "(viii)": [8],
            "(i), (ii)": [1, 2],
            "(i)-(iv)": [1, 2, 3, 4],
            "(i)-(v)": [1, 2, 3, 4, 5],
            "(v)-(viii)": [1, 2, 3, 4, 5, 6, 7, 8]
        }
        
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
            indent = int((line.bounds().x1() - start_x) / 4)
            line.chars = [pdfhelper.FakeChar(' ')] * indent + line.chars

    def findSectionTitleElement(self, start_index, proc_page):
        for obj_idx in range(start_index, len(proc_page.objects)):
            if isinstance(proc_page.objects[obj_idx], pdfhelper.CharCollection)\
                    and proc_page.objects[obj_idx].font_name().find("BoldMT") != -1\
                    and proc_page.objects[obj_idx].chars[0].size >= 17\
                    and (str(proc_page.objects[obj_idx]).find('–') != -1 or str(proc_page.objects[obj_idx]).find('-') != -1\
                             or str(proc_page.objects[obj_idx]).strip().lower() == "sleep"):
                
                return (True, obj_idx)

        return (False, -1)

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
                        elif element.chars[idx]._text == '\u2000':
                            element.chars[idx]._text = " "
                        elif element.chars[idx]._text == '←':
                            element.chars[idx]._text = "="
                        elif element.chars[idx]._text == '→':
                            element.chars[idx]._text = "->"
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

                same_x = pdfhelper.pretty_much_equal(line.rect.x1(), last.rect.x1())
                same_size = last.font_size() == line.font_size()
                decent_descent = abs(line.rect.y1() - last.rect.y2()) < 2

                if same_x and same_size and decent_descent:
                    lastChar = last.chars[-1].get_text()[-1]

                    if lastChar == "-": # most of them is line redirect
                        del last.chars[-1]
                    else:
                        if lastChar != "/":
                            last.append_char(" ")
                        
                    last.append(line)
                else:
                    merged.append(line)
            else:
                merged.append(line)

        return merged    
    
    def eraseTitleNumber(self):
        idx = 0
        while idx < len(self.objects):
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                ch_idx = 0
                while ch_idx < len(self.objects[idx].chars):
                    if isinstance(self.objects[idx].chars[ch_idx], LTChar):
                        if self.objects[idx].chars[ch_idx].x0 < 78:
                            del self.objects[idx].chars[ch_idx]

                            while len(self.objects[idx].chars) \
                                    and len(self.objects[idx].chars[ch_idx].get_text().strip()) == 0:
                                del self.objects[idx].chars[ch_idx]

                        else:
                            ch_idx += 1
                    else:
                        ch_idx += 1

                if len(self.objects[idx].chars) == 0:
                    del self.objects[idx]
                else:
                    idx += 1
            else:
                idx += 1

    def unboxFigure(self):

        idx = 0
        while idx < len(self.objects):
            if isinstance(self.objects[idx], pdfhelper.Figure):
                for data in self.objects[idx].data.data_storage:
                    for subentry in data:
                        self.objects.insert(idx + 1, subentry)

                del self.objects[idx]
            else:
                idx += 1

        return

    def handleSREGNagateFormula(self, text):
        
        if len(text) == 0:
            return

        text_words = []

        current_word = []
        for char in text.chars:
            if char.get_text() == " ":
                text_words.append(current_word)
                current_word = []
            else:
                current_word.append(char)

        if len(current_word):
            text_words.append(current_word)

        for word in text_words:
            if len(word) == 0:
                continue
            
            word_confid_x = word[0].x0 + 3
            word_confid_y = word[0].y1 + 3
            
            for rect in self.rects:
                if rect.horizontal()\
                        and rect.x1() < word_confid_x and rect.x2() > word_confid_x\
                        and abs(rect.y1() - word_confid_y) < 5:
                    word[0]._text = word[0].text = "~" + word[0].get_text()

        return

    def handleDescTables(self, caption):

        operation_idx = 0
        while operation_idx < len(self.objects):
            if isinstance(self.objects[operation_idx], pdfhelper.CharCollection)\
                and str(self.objects[operation_idx]).strip().lower() == caption:
                
                if (operation_idx + 1) < len(self.objects)\
                        and isinstance(self.objects[operation_idx + 1], pdfhelper.CharCollection)\
                        and str(self.objects[operation_idx + 1]).strip().lower() == caption:
                    operation_idx += 1
                    continue
                
                break
            else:
                operation_idx += 1

        if operation_idx >= len(self.objects):
            return
        
        titles_end_idx = operation_idx + 1
        while titles_end_idx < len(self.objects): 
            if isinstance(self.objects[titles_end_idx], pdfhelper.CharCollection)\
                and str(self.objects[titles_end_idx]).find(":") != -1:
                
                titles_end_idx += 1
            else:
                break
        
        end_of_operation_section = titles_end_idx
        while end_of_operation_section < len(self.objects): 
            if isinstance(self.objects[end_of_operation_section], pdfhelper.CharCollection)\
                and (str(self.objects[end_of_operation_section]).strip().find(":") == (len(str(self.objects[end_of_operation_section]).strip()) - 1)\
                        or str(self.objects[end_of_operation_section]).strip().lower()[0:14] in ["16-bit opcode:", "16 bit opcode:", "16-bit opcode "])\
                and self.objects[end_of_operation_section].x1() >= 78:
                
                break
            else:
                end_of_operation_section += 1
        
        if caption == "operation:":
            header_data = [[], [], []]      # (*) | Operation | Comment
        else:                          
            header_data = [[], [], [], [], []]  # (*) | Syntax | Operands | Program Counter | Stack

        real_idx = 1
        for idx in range(operation_idx, titles_end_idx):
            
            if real_idx >= len(header_data):
                #breakpoint()
                continue

            header_data[real_idx] = [self.objects[idx]]
            real_idx += 1

        table_data = [header_data]
        
        self.objects.sort(key=functools.cmp_to_key(sort_topdown_ltr_prec_by_3))
        


        idx = titles_end_idx
        current_row = []
        while idx < end_of_operation_section:
            
            if str(self.objects[idx]).strip().lower() in self.enum_data:
                
                if len(current_row):
                    table_data.append(current_row)

                current_row = []
                for item in table_data[0]:
                    current_row.append([])

                current_row[0].append(self.objects[idx])
                idx += 1
                continue

            
            if len(current_row):
                current_x = self.objects[idx].x1()

                found_place = False
                for item_idx in range(1, len(table_data[0])):
                    if len(table_data[0][item_idx]) \
                            and abs(table_data[0][item_idx][0].x1() - current_x) < 10:
                        current_row[item_idx].append(self.objects[idx])
                        found_place = True
                        idx += 1
                        break
                
                if not found_place:
                    if caption == "operation:":
                        if current_x <= 200:
                            current_row[1].append(self.objects[idx])
                            idx += 1
                        else:
                            current_row[2].append(self.objects[idx])
                            idx += 1
                    else:
                        if current_x <= 200:
                            current_row[1].append(self.objects[idx])
                            idx += 1
                        elif current_x <= 350:
                            current_row[2].append(self.objects[idx])
                            idx += 1
                        elif current_x <= 500:
                            current_row[3].append(self.objects[idx])
                            idx += 1
    

            else:
                #current_row[0][1].append(self.objects[idx])
                idx += 1
        
        if len(current_row) and len(current_row[1]):
            table_data.append(current_row)

        table_y = self.objects[end_of_operation_section - 1].y2()
        
        del self.objects[operation_idx: end_of_operation_section]

        return (table_data, table_y)
    
    def handleOpcode(self):

        opcode_size = 0
        opcode_title_idx = 0
        while opcode_title_idx < len(self.objects):
            if isinstance(self.objects[opcode_title_idx], pdfhelper.CharCollection)\
                and (str(self.objects[opcode_title_idx]).strip().lower()[0:14] in ["16-bit opcode:", "16 bit opcode:", "16-bit opcode "] \
                        or str(self.objects[opcode_title_idx]).strip().lower() == "32-bit opcode:"):
                
                opcode_size = 16 if str(self.objects[opcode_title_idx]).strip().lower()[0:14] in ["16-bit opcode:", "16 bit opcode:", "16-bit opcode "] else 32
                break
            else:
                opcode_title_idx += 1

        if opcode_title_idx >= len(self.objects):
            return
        
        end_of_opcode_section = opcode_title_idx
        while end_of_opcode_section < len(self.objects): 
            if isinstance(self.objects[end_of_opcode_section], pdfhelper.CharCollection)\
                and str(self.objects[end_of_opcode_section]).strip().lower() in ["status register (sreg) and boolean formula", "status register and boolean formula", "example:", "words"]:
                
                break
            else:
                end_of_opcode_section += 1

        tables_data = []

        for idx in range(opcode_title_idx + 1, end_of_opcode_section):

            if not isinstance(self.objects[idx], pdfhelper.SingleCellTable):
                #breakpoint()
                ""
            else:
                tables_data.append(self.objects[idx])

        if len(tables_data) == 0:
            result_alias = [[[""], [self.objects[opcode_title_idx]]]]

            del self.objects[opcode_title_idx: end_of_opcode_section]
            return (result_alias, 16)

        opcodes = []
        current_opcode = ""
        name_idx = ""
        for idx in range(0, len(tables_data)):

            if opcode_size == 16:
                
                for item in tables_data[idx].get_everything():
                    if str(item).strip() not in self.enum_data:
                        current_opcode += str(item).strip()
                    else:
                        name_idx = str(item).strip()

                opcodes.append([[name_idx], [pdfhelper.make_sint_char_collection(current_opcode, "ArialMT")]])
                current_opcode = ""
                name_idx = ""

            elif opcode_size == 32:
                
                for item in tables_data[idx].get_everything():
                    if str(item).strip() not in self.enum_data:
                        current_opcode += str(item).strip()
                    else:
                        name_idx = str(item).strip()

                if (idx & 1 == 1):
                    opcodes.append([[name_idx], [pdfhelper.make_sint_char_collection(current_opcode, "ArialMT")]])
                    current_opcode = ""
                    name_idx = ""

        del self.objects[opcode_title_idx: end_of_opcode_section]

        return (opcodes, opcode_size)

    def findItemFromInstInfoByIndex(self, idx, instinf_list):

        for list_idx in range(0, len(instinf_list)):
            index_str = ""    
            if len(instinf_list[list_idx][0]):
                index_str = str(instinf_list[list_idx][0][0]).strip().lower()
            
            if index_str == "" or index_str in self.enum_data_map:
                if index_str == "" or idx in self.enum_data_map[index_str]:
                    return instinf_list[list_idx]
            #else:
            #    breakpoint()

        #breakpoint()

    def generateInstInfoTable(self, operation_data, syntax_data, opcode_data):

        table_data = []
        max_index = 0

        for idx in range(1, len(operation_data[0])):
            index_str = ""    
            if len(operation_data[0][idx][0]):
                index_str = str(operation_data[0][idx][0][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            #else:
            #    breakpoint()

        for idx in range(1, len(syntax_data[0])):
            index_str = ""    
            if len(syntax_data[0][idx][0]):
                index_str = str(syntax_data[0][idx][0][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            #else:
            #    breakpoint()

        for idx in range(0, len(opcode_data[0])):
            index_str = ""    
            if len(opcode_data[0][idx][0]):
                index_str = str(opcode_data[0][idx][0][0]).strip().lower()

            if index_str in self.enum_data_map:
                if max_index < max(self.enum_data_map[index_str]):
                    max_index = max(self.enum_data_map[index_str])
            #else:
            #    breakpoint()
        
        # op syntax | operation | operands | program counter | opcode | comment | stack
        title_row_data = [
                syntax_data[0][0][1] if len(syntax_data[0][0][1]) else [pdfhelper.make_sint_char_collection("Syntax", "ArialMT")], 
                operation_data[0][0][1] if len(operation_data[0][0][1]) else [pdfhelper.make_sint_char_collection("Operation", "ArialMT")], 
                syntax_data[0][0][2] if len(syntax_data[0][0][2]) else [pdfhelper.make_sint_char_collection("Operands", "ArialMT")], 
                syntax_data[0][0][3] if len(syntax_data[0][0][3]) else [pdfhelper.make_sint_char_collection("Program counter", "ArialMT")], 
                [pdfhelper.make_sint_char_collection("Opcode", "ArialMT")], 
                operation_data[0][0][2] if len(operation_data[0][0][2]) else [pdfhelper.make_sint_char_collection("Comment", "ArialMT")],
                syntax_data[0][0][4] if len(syntax_data[0][0][4]) else [pdfhelper.make_sint_char_collection("Stack", "ArialMT")]
            ]

        table_data.append(title_row_data)

        for idx in range(1, max_index + 1):
            operation = self.findItemFromInstInfoByIndex(idx, operation_data[0][1:])
            syntax = self.findItemFromInstInfoByIndex(idx, syntax_data[0][1:])
            opcode = self.findItemFromInstInfoByIndex(idx, opcode_data[0])

            if operation == None:
                 operation = [[], [], []]
            
            #if syntax == None or opcode == None:
            #   breakpoint()

            row_data = [syntax[1], operation[1], syntax[2], syntax[3], opcode[1], operation[2], syntax[4]]

            table_data.append(row_data)


        for row in table_data[1:]:
            self.replaceCodeForCollection(row[1])
            self.replaceCodeForCollection(row[2])
            self.replaceCodeForCollection(row[3])

        self.objects.insert(0, pdfhelper.Table(table_data, True, len(table_data[0])))
        self.objects[0].set_y1(0)
        return

    def handleStatusRegister(self):

        sreg_section = 0
        while sreg_section < len(self.objects): 
            if isinstance(self.objects[sreg_section], pdfhelper.CharCollection)\
                and str(self.objects[sreg_section]).strip().lower() in ["status register (sreg) and boolean formula", "status register and boolean formula"]:
                
                break
            else:
                sreg_section += 1

        if sreg_section >= len(self.objects):
            return

        sreg_section_end = sreg_section + 1
        while sreg_section_end < len(self.objects): 
            if isinstance(self.objects[sreg_section_end], pdfhelper.CharCollection)\
                and str(self.objects[sreg_section_end]).strip().lower() in ["example:", "words"]:
                
                break
            else:
                sreg_section_end += 1

        if not isinstance(self.objects[sreg_section + 1], pdfhelper.SingleCellTable)\
                or not isinstance(self.objects[sreg_section + 2], pdfhelper.SingleCellTable):

        #    breakpoint()
            ""

        idx = sreg_section
        while idx < sreg_section_end:
            if isinstance(self.objects[idx], pdfhelper.CharCollection)\
                    and self.objects[idx].font_name().find("BoldMT") != -1:
                
                current_x = self.objects[idx].x1()
                current_y = self.objects[idx].y1()
                current_y2 = self.objects[idx].y2()
                
                result = pdfhelper.divide_collection_by_font_name(self.objects[idx], "BoldMT")
                
                del self.objects[idx]

                for collection in result:
                    #collection.set_x1(current_x)
                    collection.set_y1(current_y)
                    collection.set_y2(current_y2)
                    
                    self.objects.insert(idx, collection)
                    idx += 1
                    sreg_section_end += 1
                
                sreg_section_end -= 1

            else:
                idx += 1

        table_data = []

        if str(self.objects[sreg_section + 1].get_everything()[0]).strip().lower() == "i":
            row_data = []
            for item in self.objects[sreg_section + 1].get_everything():
                row_data.append([item])

            table_data.append(row_data)

            row_data = []
            for item in self.objects[sreg_section + 2].get_everything():
                row_data.append([item])

            table_data.append(row_data)
        else:
            row_data = []
            for item in self.objects[sreg_section + 2].get_everything():
                row_data.append([item])

            table_data.append(row_data)

            row_data = []
            for item in self.objects[sreg_section + 1].get_everything():
                row_data.append([item])

            table_data.append(row_data)
        
        flag_description = []

        # it has flags desciption
        if sreg_section + 2 < sreg_section_end:
            # flag formula description
            data_items = []

            for idx in range(sreg_section + 3, sreg_section_end):
                if self.objects[idx].x1() < 90:
                    flag_description.append([self.objects[idx], []])
                else:
                    data_items.append(self.objects[idx])
            
            for item in data_items:
                
                item_handled = False
                flag_item_idx = 0
                while flag_item_idx < len(flag_description):
                    
                    if item.y2() < flag_description[flag_item_idx][0].y1():
                        # prev
                        if flag_item_idx == 0:
                            flag_description[0][1].append(item)
                        else:
                            flag_description[flag_item_idx - 1][1].append(item)
                        
                        item_handled = True
                        break
                    
                    flag_item_idx += 1


                if not item_handled: # for last
                    flag_description[-1][1].append(item)

        table_y = self.objects[sreg_section_end - 1].y2()
        
        complound_table = []

        idx_flag = 0
        while idx_flag < len(table_data[0]):

            complound_row = [[table_data[0][idx_flag][0]], [table_data[1][idx_flag][0]], [], []]
            current_flag_name = str(table_data[0][idx_flag][0]).strip().lower()
            desc_idx = 0

            while desc_idx < len(flag_description):
                desc_flag_name = str(flag_description[desc_idx][0]).strip().lower()

                if current_flag_name == desc_flag_name:
     
                    for item_idx in range(0, len(flag_description[desc_idx][1])):
                        if item_idx == 0:
                            complound_row[2].append(flag_description[desc_idx][1][item_idx])
                        else:
                            complound_row[3].append(flag_description[desc_idx][1][item_idx])

                    del flag_description[desc_idx]

                desc_idx += 1

            complound_table.append(complound_row)
            idx_flag += 1

        for item in flag_description:
            complound_row = [[ pdfhelper.make_char_collection(item[0].chars[0:10]) ]]
            
            for sub_item in item:
                complound_row.append([sub_item])

            while len(complound_row) < 4:
                complound_row.append([])

            complound_table.append(complound_row)

        del self.objects[sreg_section + 1: sreg_section_end]

        for item in complound_table:
            for subitem in item[2]:
                self.handleSREGNagateFormula(subitem)

        self.objects.insert(sreg_section + 1, pdfhelper.Table(complound_table, True, len(complound_table[0])))
        self.objects[sreg_section + 1].set_y1(table_y)
        return
    
    def handleExamples(self):

        idx = 0
        while idx < len(self.objects):       
            if isinstance(self.objects[idx], pdfhelper.CharCollection) \
                    and str(self.objects[idx]).strip().lower() == "example:":
                
                idx += 1
                
                while idx < len(self.objects):

                    if isinstance(self.objects[idx], pdfhelper.CharCollection) \
                        and str(self.objects[idx]).strip().lower() in self.titles_list:

                        return
                    else:
                        if isinstance(self.objects[idx], pdfhelper.SingleCellTable):
                            for data in self.objects[idx].get_everything():
                                self.objects.insert(idx + 1, data)

                            del self.objects[idx]

                        idx += 1

            else:
                idx += 1

        return
    
    def handleCycles(self):

        idx = 0
        while idx < len(self.objects):       
            if isinstance(self.objects[idx], pdfhelper.CharCollection) \
                    and cycles_format__.search(str(self.objects[idx]).strip().lower()) != None:

                cycle_idx = 0
                while cycle_idx < len(self.objects[idx].chars):
                    if self.objects[idx].chars[cycle_idx].get_text() == "C":
                        break
                    cycle_idx += 1
                
                del self.objects[idx].chars[5: cycle_idx]
                self.objects[idx].chars.insert(5, pdfhelper.FakeChar(' '))
                
                break
            else:
                idx += 1

        cycles_start = idx + 1
        cycles_end = cycles_start
        while cycles_end < len(self.objects):  
            
            if isinstance(self.objects[cycles_end], pdfhelper.CharCollection) \
                    and (str(self.objects[cycles_end]).strip().lower() == "notes:" \
                            or str(self.objects[cycles_end]).strip().lower() == "note:"\
                            or self.objects[cycles_end].chars[0].fontname.find("Bold") == -1):
                
                break

            cycles_end += 1

        table_items = []
        idx = cycles_start
        while idx < cycles_end:
            
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if len(table_items):
                    break
                
            if isinstance(self.objects[idx], pdfhelper.SingleCellTable):
                row_items = []
                invalid_table = False
                
                if len(self.objects[idx].get_everything()) < 2:
                    idx += 1
                    continue

                for data in self.objects[idx].get_everything():
                    if data.font_name().find("Bold") != -1:
                        invalid_table = True
                
                if invalid_table == True:
                    break

                for data in self.objects[idx].get_everything():
                    row_items.append(data)

                row_items.sort(key=functools.cmp_to_key(sort_topdown_ltr_prec_by_3))
                
                table_items.append(row_items)
                del self.objects[idx]
                cycles_end -= 1
            else:
                idx += 1

        # unpack tables with other text 
        idx = cycles_start
        while idx < cycles_end:
            if isinstance(self.objects[idx], pdfhelper.SingleCellTable):
                for data in self.objects[idx].get_everything():
                    self.objects.insert(idx + 1, data)

                cycles_end += (len(self.objects[idx].get_everything()) - 1)
                del self.objects[idx]
                
            idx += 1

        cycles_texts = []
        idx = cycles_start
        while idx < cycles_end:         
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                cycles_texts.append(self.objects[idx])
                del self.objects[idx]
                cycles_end -= 1
            else:
                idx += 1

        # make titles
        titles_items = []
        for item in table_items[0]:
            items_for_title = []

            text_idx = 0
            while text_idx < len(cycles_texts):
                if abs(cycles_texts[text_idx].x1() - item.x1()) < 10:
                    items_for_title.append(cycles_texts[text_idx])
                    del cycles_texts[text_idx]
                else:
                    text_idx += 1

            titles_items.append(items_for_title)
        
        table_data = [titles_items]
        for row in table_items:
            row_data = []
            for item in row:
                row_data.append([item])
            table_data.append(row_data)

        self.objects.insert(cycles_start, pdfhelper.Table(table_data, True, len(table_data[0])))
        self.objects[cycles_start].set_y1(self.objects[cycles_start - 1].y1() + 2)
        return

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

        self.eraseTitleNumber()
        self.unboxFigure()
        
        operation_data = self.handleDescTables("operation:")
        syntax_data = self.handleDescTables("syntax:")
        opcode_data = self.handleOpcode()
        
        self.generateInstInfoTable(
                operation_data, syntax_data, opcode_data
            )

        self.handleStatusRegister()
        self.handleExamples()
        self.handleCycles()
        
        return self.mergeText(self.objects, False)

    def flush(self):
            
        displayable = self.prepareDisplay()
        
        self.outputFile(displayable)
    
    def processPage(self, page):
        
        
        proc_page = processedPage(page, 0)
        
        if isinstance(proc_page.objects[0], pdfhelper.CharCollection)\
            and isinstance(proc_page.objects[1], pdfhelper.CharCollection):

            # in instructions section
            if str(proc_page.objects[1]).strip().lower() == 'instruction description':
                
                # cut header and body from pdf
                proc_page.cut_off(0, 10000, 50, 745)

                current_index = 0
                titles_list = []

                while current_index != -1:

                    (has_inst_title, current_index) = self.findSectionTitleElement(current_index + 1, proc_page)

                    if current_index != -1:
                        titles_list.append(current_index)

                last_object_index = 0
                for title_idx in titles_list:
                    
                    title_items = []
                    if str(proc_page.objects[title_idx]).strip().lower() == "sleep":
                        title_items.append(str(proc_page.objects[title_idx]).strip())
                        title_items.append("")
                    else:
                        if str(proc_page.objects[title_idx]).find('–') != -1:
                            title_items = str(proc_page.objects[title_idx]).split('–')
                        else:
                            title_items = str(proc_page.objects[title_idx]).split('-')

                    inst_name = title_items[0].strip()
                    description = title_items[1].strip()

                    # add page section tail for instruction if previous inst exisits
                    if self.instName == "":
                        self.instName = inst_name
                        self.instDescription = description
                        self.InstIndex = 1
                        self.y_offset = 0
                        self.objects = []
                        self.rects = []
                        last_object_index = title_idx + 1

                    elif self.instName != inst_name \
                            or self.instDescription != description: # inst changed
                        
                        new_proc_page = processedPage(page, self.y_offset) # update page with new y offset

                        # shift page and add content
                        new_proc_page.cut_off(0, 10000, 50, 745)

                        self.y_offset += new_proc_page.page_heigth 
                        self.objects += new_proc_page.objects[last_object_index:title_idx]
                        self.rects += new_proc_page.rects
                    
                        if len(self.objects) != 0:
                            # try:
                            self.flush()
                            self.success += 1
                            #except Exception as e:
                            #    print("*** couldn't flush to disk")
                            #    self.fail += 1 

                        self.instName = inst_name
                        self.instDescription = description
                        self.InstIndex += 1
                        self.y_offset = 0
                        self.objects = []
                        self.rects = []
                        last_object_index = title_idx + 1


                # add last part of the page
                if last_object_index < len(proc_page.objects): 

                    new_proc_page = processedPage(page, self.y_offset)
                    new_proc_page.cut_off(0, 10000, 50, 745)
                    self.y_offset += new_proc_page.page_heigth 
                    self.objects += new_proc_page.objects[last_object_index:]
                    self.rects += new_proc_page.rects


    def outputFile(self, displayable):

        title = self.instName
        path = "%s/%s_%d" % (self.outputDir, title.replace("/", "_").replace(" ", ""),  self.InstIndex)
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
                    
                    children = self.mergeText(element.get_at(col, row), True)
                    
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
        
        if is_code or (len(self.__title_stack) >= 1 \
                        and (self.__title_stack[-1] == "example:")):
            
            current_paragraph["attributes"].append("code")
            
            if len(self.__title_stack) >= 1 \
                        and (self.__title_stack[-1] == "example:"):
                indent = int((element.bounds().x1() - 85) / 4)
                element.chars = [pdfhelper.FakeChar(' ')] * indent + element.chars

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
        
