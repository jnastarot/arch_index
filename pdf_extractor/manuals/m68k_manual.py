import sys
import math
import re
import functools

import pdfhelper
from pdfminer.layout import *
from htmltext import *
from json2html import *
from processing_helper import *

class m68kManParser(object):
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
        self.titlesName = [
            "Operation:",
            "Assembler",
            "Syntax:",
            "Attributes:",
            "Description:",
            "Condition Codes:",
            "Instruction Format:",
            "Instruction Fields:",

        ]

    def isTitleElement(self, element):
        
        if not isinstance(element, pdfhelper.CharCollection):
            return False

        if element.font_name() == "NeoSansIntelMedium":

            texts = str(element).split(' ')[0].strip().lower()
            first_name = self.TitleElements[0]
            is_subname = first_name.lower().find(texts) != -1\
                or texts.lower().find(first_name.lower()) != -1\
                or str(element).find('(') != -1\
                or texts.find('notes') != -1\
                or texts == 'note'  
            
            
            if str(element).strip().lower() in self.pseudo_title:
                return False

            if element.font_size() >= 12: 
                return True
            elif element.font_size() >= 9:
                if is_subname == False and element.bounds().x1() < 50: 
                    return True
            
        return False


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

                    idx += 1

        except Exception as e:
            print("Failed to prepare for ", str(idx), " ", str(element))

        return element    


    def mergeText(self, lines, isinTable):
       
        if len(lines) == 0: return []
        
        lines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
        merged = [lines[0]]

        for line in lines[1:]:
            
            last = merged[-1]
            if isinstance(last, pdfhelper.List) and len(last.items):            
                last = last.items[-1]

            if isinstance(line, pdfhelper.CharCollection) \
                    and isinstance(last, pdfhelper.CharCollection):

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

    def handleConnditionCodes(self):

        return
    
    def handleInstFormat(self):

        return
    
    def handleInstFields(self):

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

        #self.generateExceptionFlagTables()

        #self.objects = self.mergeText(self.objects, False)

        #self.splitSameTables()
        #self.assemblePseudocode()
        
        return self.mergeText(self.objects, False)

    def flush(self):
            
        displayable = self.prepareDisplay()
        
        self.outputFile(displayable)
    
    def processPage(self, page):
        
        proc_page = processedPage(page, 0)
        proc_page.cut_off(0, 10000, 5, 725)

        if len(proc_page.objects) >= 5 \
            and isinstance(proc_page.objects[0], pdfhelper.CharCollection)\
            and isinstance(proc_page.objects[1], pdfhelper.CharCollection)\
            and isinstance(proc_page.objects[2], pdfhelper.CharCollection)\
            and isinstance(proc_page.objects[3], pdfhelper.CharCollection)\
            and isinstance(proc_page.objects[4], pdfhelper.CharCollection):

            inst_name1 = proc_page.objects[1]
            inst_name2 = proc_page.objects[2]
            
            if inst_name1.font_size() > 20 and inst_name2.font_size() > 20\
                and inst_name2.font_name().find("Bold") != -1:

                inst_name = str(inst_name1).strip()
                category = str(proc_page.objects[0]).strip()
                description = str(proc_page.objects[3]).strip()
                features = str(proc_page.objects[4]).strip()
                
                if self.instName != inst_name:
                    if len(self.objects) != 0:
                        #try:
                        self.flush()
                        self.success += 1
                        #except Exception as e:
                        #    print("*** couldn't flush to disk")
                        #    self.fail += 1 

                    self.instName = inst_name
                    self.instCategory = category
                    self.instDescription = description
                    self.instFeature = features
                    self.y_offset = 0
                    self.objects = []

                proc_page = processedPage(page, self.y_offset) # update page with new y offset

                # shift page and add content
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

        not_accept_font_modifier = False

        current_paragraph = {
            "type": "paragraph",
            "elements": [],
            "attributes": []
        }
        
        if element.font_name() == "NeoSansIntelMedium":
            tag = ""
            index = 1

            if element.font_size() >= 12: 
                tag = "h1"
                index = 1
            elif element.font_size() >= 9:
                tag = "h2"
                index = 2
            else: 
                tag = "h3"
                index = 3

            if len(tag):
                parent_element["elements"].append({
                            "type": "title",
                            "text": str(element),
                            "elements": [],
                            "attributes": [tag],
                            "level": index
                        })
                
                return True

        elif element.font_name() == "NeoSansIntel" \
                and (len(self.__title_stack) >= 1 and (self.__title_stack[-1] in self.code_segments)\
                        or len(self.__title_stack) >= 2 and self.__title_stack[-2] in self.code_segments):
            
            current_paragraph["attributes"].append("code")
            
            indent = int((element.bounds().x1() - 46) / 4)
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
