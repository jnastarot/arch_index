import sys
import math
import re
import functools

import pdfhelper
from pdfminer.layout import *
from htmltext import *
from json2html import *
from processing_helper import *


fpu_flags_format__ = re.compile(r"^C[0-9]")
exceptions_format__ = re.compile(r"^#?[A-Z]{1}")
all_format__ = re.compile(r"[a-zA-Z]{1}")

class x86ManParser(object):
    def __init__(self, outputDir, docname, laParams):
        self.outputDir = outputDir
        self.docname = docname
        self.laParams = laParams
        self.yBase = 0
        self.success = 0
        self.fail = 0
        
        self.hintText = ""
        self.TitleElements = []
        
        self.y_offset = 0
        self.objects = []

        self.hintText = ""
        self.hintChanged = False
        self.__title_stack = []
        self.code_segments = [
                "operation", 
                "operation in a uni-processor platform", 
                "c/c++ compiler intrinsic equivalent",
                "intel c/c++ compiler intrinsic equivalent",
                "intel c/c++ compiler intrinsic equivalent for returning index",
                "intel c/c++ compiler intrinsic equivalent for returning mask",
                "intel c/c++ compiler intrinsic equivalents",
                "intel c/c++ compiler intrinsics for reading eflag results"
            ]
        
        self.pseudo_title = [
            "outside 64-bit mode",
            "in 64-bit mode",
            'non-64-bit mode:',
            "64-bit mode:"
        ]

        self.tabled_title = [
            "use of prefixes"
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
                    and isinstance(last, pdfhelper.CharCollection) \
                    and (isinTable or line.font_name() != "NeoSansIntel"):

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

    def generateExceptionFlagTables(self):
        
        is_table_section = False
        expected_format = None

        line_idx = 0
        while line_idx < len(self.objects):
            
            current_line = self.objects[line_idx]

            if isinstance(current_line, pdfhelper.CharCollection) \
                    and current_line.font_name() == "NeoSansIntelMedium":

                title = str(current_line).strip().lower()
                if title[-10:] == "exceptions" or title == "exceptions (all operating modes)":
                    is_table_section = True
                    expected_format = exceptions_format__
                elif title == "fpu flags affected":
                    is_table_section = True
                    expected_format = fpu_flags_format__
                elif title in self.tabled_title:
                    is_table_section = True
                    expected_format = all_format__
                
                line_idx += 1

                if is_table_section:
                    table_data = [ [], []]
                    top_index = line_idx
                    bot_index = line_idx
                    
                    for data_line_idx in range(line_idx, len(self.objects)):
                        
                        data_line = self.objects[data_line_idx]

                        if isinstance(data_line, pdfhelper.CharCollection) \
                                            and data_line.font_name() == "NeoSansIntelMedium":
                            break

                        bot_index = data_line_idx

                        if data_line.bounds().x1() > 50:
                            table_data[1].append(data_line)
                        elif expected_format.search(str(data_line)) == None:
                            table_data[1].append(data_line)
                        else:
                            table_data[0].append(data_line)

                    if len(table_data[0]) and len(table_data[1]):

                        del self.objects[top_index : bot_index + 1]

                        table_collection = []

                        for tag_idx in range(0, len(table_data[0])):
                            
                            is_last_tag = (tag_idx + 1) == len(table_data[0])

                            tags_data = []

                            if is_last_tag:
                                while len(table_data[1]):
                                    tags_data.append(table_data[1].pop())
                            else:
                                table_data_idx = 0
                                
                                while table_data_idx < len(table_data[1]):
                                    if table_data[1][table_data_idx].y1() >= table_data[0][tag_idx].y1() \
                                            and table_data[1][table_data_idx].y1() < table_data[0][tag_idx + 1].y1():
                                    
                                        tags_data.append(table_data[1][table_data_idx])
                                        
                                        del table_data[1][table_data_idx]

                                    else:
                                        table_data_idx += 1
                            
                            table_collection.append([[table_data[0][tag_idx]], tags_data])


                        self.objects.insert(top_index, pdfhelper.Table(table_collection, True, 2))
                        self.objects[top_index].set_y1(self.objects[top_index - 1].y2())
                        
                        
                    #breakpoint()

    
            line_idx += 1

        return
    

    def splitSameTables(self):
        # try to split the same tables
        idx = 0
        while idx < len(self.objects):
            if isinstance(self.objects[idx], pdfhelper.Table):

                if len(self.objects) > idx + 1 and isinstance(self.objects[idx + 1], pdfhelper.Table): 
                    
                    if self.objects[idx].columns() == self.objects[idx + 1].columns():

                        table1_data = []
                        table2_data = []

                        for columns in self.objects[idx].get_row_data(0):
                            table1_data.append([str(column).strip() for column in columns])
                        for columns in self.objects[idx + 1].get_row_data(0):
                            table2_data.append([str(column).strip() for column in columns])

                        if table1_data == table2_data:
                            self.objects[idx + 1].delete_row(0) # delete title of table
                            self.objects[idx].merge_table(self.objects[idx + 1])

                            del self.objects[idx + 1]
                        else:
                            idx += 1
                    else:
                        idx += 1

                elif len(self.objects) > idx + 2 \
                    and isinstance(self.objects[idx + 1], pdfhelper.CharCollection)\
                    and isinstance(self.objects[idx + 2], pdfhelper.Table):
                    
                    if self.objects[idx].columns() == self.objects[idx + 2].columns():
                        
                        if str(self.objects[idx + 1]).strip().lower().find("(contd") != -1:

                            table1_data = []
                            table2_data = []

                            for columns in self.objects[idx].get_row_data(0):
                                table1_data.append([str(column).strip() for column in columns])
                            for columns in self.objects[idx + 2].get_row_data(0):
                                table2_data.append([str(column).strip() for column in columns])
                                
                            if table1_data == table2_data:
                                self.objects[idx + 2].delete_row(0)
                                self.objects[idx].merge_table(self.objects[idx + 2])

                                del self.objects[idx + 1]
                                del self.objects[idx + 1]
                            else:
                                idx += 1
                        else:
                            idx += 1
                    else:
                        idx += 1
                else:
                    idx += 1
            else:
                idx += 1

    def assemblePseudocode(self):

        idx = 0
        current_title = ""
        while idx < len(self.objects):
            item_idx = idx

            if isinstance(self.objects[item_idx], pdfhelper.CharCollection):

                # is code in operation titles
                if self.isTitleElement(self.objects[item_idx]):
                    current_title = str(self.objects[item_idx]).strip().lower()

                if current_title in self.code_segments and len(self.objects[item_idx]):

                    style = pdfhelper.FontStyle(self.objects[item_idx].chars[0])
                    
                    if style.font_is("NeoSansIntel"):
                        
                        if self.objects[item_idx].chars[-1].get_text() == '\n':
                            del self.objects[item_idx].chars[-1]
                        
                        next_idx = idx + 1
                        
                        while next_idx < len(self.objects):
                            
                            if not isinstance(self.objects[next_idx], pdfhelper.CharCollection) or not len(self.objects[next_idx]):
                                break

                            else:
                                style = pdfhelper.FontStyle(self.objects[next_idx].chars[0])
                        
                                if style.font_is("NeoSansIntel"):
                                    if abs(self.objects[item_idx].chars[0].y1 - self.objects[next_idx].chars[0].y1) < 4:

                                        # reindent
                                        indent = int(
                                                math.ceil((self.objects[next_idx].rect.x1() - self.objects[item_idx].rect.x2()) / 4)
                                            )

                                        #while isinstance(self.objects[next_idx].chars[0], LTChar) and self.objects[next_idx].chars[0].get_text() == ' ':
                                        #    del self.objects[next_idx].chars[0]

                                        self.objects[next_idx].chars = [pdfhelper.FakeChar(' ')] * indent + self.objects[next_idx].chars

                                        if self.objects[item_idx].chars[-1].get_text() == '\n':
                                            del self.objects[item_idx].chars[-1]

                                        self.objects[item_idx].append(self.objects[next_idx])
                                        del self.objects[next_idx]

                                        if self.objects[item_idx].chars[-1].get_text() == '\n':
                                            del self.objects[item_idx].chars[-1]

                                    else:
                                        break
                                else:

                                    if len(str(self.objects[next_idx]).strip()) == 0:
                                        del self.objects[next_idx]
                                    else:
                                        break

            idx += 1

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

        self.generateExceptionFlagTables()

        self.objects = self.mergeText(self.objects, False)

        self.splitSameTables()
        self.assemblePseudocode()
        
        return self.objects

    def flush(self):
            
        displayable = self.prepareDisplay()
        
        self.outputFile(displayable)
    
    def processPage(self, page):
        
        proc_page = processedPage(page, 0)

        # process page if it has 
        # INSTRUCTION SET REFERENCE
        # or
        # EXTENSIONS REFERENCE
        has_hint = False
        has_title = False
        title_parts = []

        if isinstance(proc_page.objects[0], pdfhelper.CharCollection):
            if not has_hint and (proc_page.objects[0].y1() <= 35 and proc_page.objects[0].font_size() < 12):

                hint_text = str(proc_page.objects[0]).strip()
                
                if hint_text.find("INSTRUCTION SET REFERENCE") != -1 or hint_text.find("EXTENSIONS REFERENCE") != -1:
                    has_hint = True
                        
                    if self.hintText != hint_text:
                        self.hintChanged = True
                        self.hintText = hint_text
 
        if isinstance(proc_page.objects[1], pdfhelper.CharCollection):           
            if not has_title and (proc_page.objects[1].y1() <= 70 and proc_page.objects[1].font_size() < 13):
                if proc_page.objects[1].font_name() == "NeoSansIntelMedium" and proc_page.objects[1].font_size() >= 12:
                    title_parts = [p.strip() for p in re.split("\s*[-–—]\s*", str(proc_page.objects[1]).strip(), 1)]
                    if len(title_parts) == 2:
                        has_title = True

        if has_hint:      
            if self.hintChanged or has_title: # new title - new instruction 
                
                if len(self.objects) != 0:
                    try:
                        self.flush()
                        self.success += 1
                    except Exception as e:
                        print("*** couldn't flush to disk")
                        self.fail += 1
                    
                self.TitleElements = title_parts
                self.y_offset = 0
                self.objects = []
                self.hintChanged = False

            if has_title or len(self.objects) > 0:
                proc_page = processedPage(page, self.y_offset) # update page with new y offset

                # shift page and add content
                proc_page.cut_off(0, 10000, 50, 725)

                self.y_offset += proc_page.page_heigth 
                self.objects += proc_page.objects
                

    def outputFile(self, displayable):

        title = self.TitleElements[0]
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
            "rootname": self.TitleElements, 
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
            
            texts = str(element).split(' ')[0].strip().lower()
            first_name = self.TitleElements[0]
            is_subname = first_name.lower().find(texts) != -1\
                or texts.find(first_name.lower()) != -1\
                or str(element).find('(') != -1\
                or texts.find('notes') != -1\
                or texts == 'note'

            if str(element).strip().lower() not in self.pseudo_title and element.font_size() >= 12: 
                tag = "h1"
                index = 1
            elif element.font_size() >= 9:
                if str(element).strip().lower() not in self.pseudo_title \
                        and is_subname == False and element.bounds().x1() < 50: 
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
                this_bold = this_style.font_is("Bold") or this_style.font_is("NeoSansIntelMedium")
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
