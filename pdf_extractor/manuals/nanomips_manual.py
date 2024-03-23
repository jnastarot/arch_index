import sys
import math
import re
import functools

import pdfhelper
from pdfminer.layout import *
from htmltext import *
from json2html import *
from processing_helper import *


class nanomipsISAManParser(object):
    def __init__(self, outputDir, docname, laParams, type):
        self.outputDir = outputDir
        self.laParams = laParams
        self.docname = docname
        self.type = type
        self.success = 0
        self.fail = 0
        
        self.hintText = ""
        self.TitleElements = []
        
        self.y_offset = 0
        self.instFormatTable = []
        self.objects = []

        self.__title_stack = []
        self.firstIsInstName = []

        self.main_titles = [
            "assembly:",
            "purpose:",
            "availability:",
            "format:",
            "operation:",
            "exceptions:",
            "expansion:"
        ]

    def elementIsTitle(self, element):
        
        if not isinstance(element, pdfhelper.CharCollection):
            return False
        
        style = pdfhelper.FontStyle(element.chars[0])
        
        return style.font_is("DejaVuSerif-Bold")

    def elementGetTitle(self, element):
        if isinstance(element,  pdfhelper.CharCollection):
            if len(element.chars) == 0: return False
        
            style = pdfhelper.FontStyle(element.chars[0])
            if style.font_is("DejaVuSerif-Bold"):
                str_title = str(element).strip().lower()
                return str_title
                
        return ""
    
    def replaceSpecSymbols(self, element): # convert silly symbols to normal  

        try:
            if isinstance(element, pdfhelper.CharCollection):

                idx = 0
                while idx < len(element.chars):

                    if isinstance(element.chars[idx], LTChar):
                        if element.chars[idx].width < 0.15 and element.chars[idx].height < 3:
                            del element.chars[idx]
                            continue

                    if isinstance(element.chars[idx], LTChar):

                        fontname = pdfhelper.get_char_font_name(element.chars[idx])
                        
                        if 1 == 1: # fontname == "Wingdings3" or fontname == "SymbolMT": # Courier
                            
                            has_chages = False
                            
                            if element.chars[idx]._text in ['\uf066', '\uf0ac', '\uf03d', '\uf0a8', '←']: 
                                element.chars[idx]._text = "="
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0ae':
                                element.chars[idx]._text = "->"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0b1':
                                element.chars[idx]._text = "±"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf02b':
                                element.chars[idx]._text = "+"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf02d':
                                element.chars[idx]._text = "-"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0b9' or element.chars[idx]._text == '≠':
                                element.chars[idx]._text = "!="
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0b3':
                                element.chars[idx]._text = ">="
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0a3':
                                element.chars[idx]._text = "<="
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0b4':
                                element.chars[idx]._text = "<="
                                has_chages = True
                            elif element.chars[idx]._text == '\uf03e':
                                element.chars[idx]._text = ">"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf03c':
                                element.chars[idx]._text = "<"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf07c':
                                element.chars[idx]._text = "|"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf028':
                                element.chars[idx]._text = "("
                                has_chages = True
                            elif element.chars[idx]._text == '\uf029':
                                element.chars[idx]._text = ")"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf05d':
                                element.chars[idx]._text = "]"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf0a5':
                                element.chars[idx]._text = "inf"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf05f':
                                element.chars[idx]._text = "_"
                                has_chages = True
                            elif element.chars[idx]._text == '\uf020':
                                element.chars[idx]._text = " "
                                has_chages = True
                            elif element.chars[idx]._text == '—' or element.chars[idx]._text == '\uf0be':
                                element.chars[idx]._text = "-"
                                has_chages = True
                            elif element.chars[idx]._text == '(cid:129)':
                                element.chars[idx]._text = "•"
                                has_chages = False

                            if fontname == "Wingdings3" or fontname == "SymbolMT": # for debug
                                if not has_chages:
                                    breakpoint()

                            if has_chages:
                                element.chars[idx].fontname = "DejaVuSansMono"
                    
                    idx += 1

        except Exception as e:
            print("Failed to prepare for ", str(idx), " ", str(element))

        return element    


    def tryAssembleLines(self, object_1, object_2):

        if not isinstance(object_1, pdfhelper.CharCollection) or not len(object_1):
            return False  
        if not isinstance(object_2, pdfhelper.CharCollection) or not len(object_2):
            return False
   
        if not self.elementIsTitle(object_1) and not self.elementIsTitle(object_2) \
            and abs(object_1.rect.y1() - object_2.rect.y1()) < 1 \
            and abs(object_1.rect.y1() - object_2.rect.y1()) < 6:
            
            if object_1.chars[-1].get_text() == '\n':
                del object_1.chars[-1]
            
            object_1.append(object_2)
            return True
                
        return False      

    def tryAssembleTextPartsHalf(self, object_1, object_2):

        if not isinstance(object_1, pdfhelper.CharCollection) or not len(object_1):
            return False  
        if not isinstance(object_2, pdfhelper.CharCollection) or not len(object_2):
            return False
        
        style = pdfhelper.FontStyle(object_1.chars[0])
        new_style = pdfhelper.FontStyle(object_2.chars[0])
    
        has_defis = False

        if len(object_1):
            if len(object_1.chars) > 0 and object_1.chars[-1].get_text() == '-':
                style = pdfhelper.FontStyle(object_1.chars[-1])
                has_defis = True
            elif len(object_1.chars) > 1 and object_1.chars[-2].get_text() == '-' and object_1.chars[-1].get_text() == '\n':
                style = pdfhelper.FontStyle(object_1.chars[-2])
                has_defis = True

        if style.font_is("Times") and (new_style.font == style.font or has_defis) \
                or (new_style.font == style.font and has_defis):
            
            if object_2.chars[0].get_text().islower() \
                    or object_2.chars[0].get_text() == ' ' \
                    or (new_style.font == style.font and has_defis):
            
                if object_1.chars[-1].get_text() == '\n':
                    del object_1.chars[-1]
            
                if len(object_1) >= 2:
                    if object_1.chars[-1].get_text() == '-':
                        del object_1.chars[-1]
                        has_defis = True
                    elif object_1.chars[-2].get_text() == '-' and object_1.chars[-1].get_text() == ' ':
                        del object_1.chars[-1]
                        has_defis = True
                
                if not has_defis and object_1.y1() != object_2.y1():
                    object_1.append_char(' ')
                
                object_1.append(object_2)
                
                return True
                
        return False        

    def erasePseudocodeLines(self):

        idx = 0
        while idx < len(self.objects):
            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.objects[idx].x1() < 60:
                    del self.objects[idx]
                else:
                    idx += 1
            else:
                idx += 1

        return
    
    def assemblePseudocode(self):

        idx = 0

        while idx < len(self.objects):
            item_idx = idx

            if isinstance(self.objects[item_idx], pdfhelper.CharCollection):
                
                if len(self.objects[item_idx]):

                    style = pdfhelper.FontStyle(self.objects[item_idx].chars[0])
                    
                    if style.font_is("DejaVuSansMono"):
                        
                        if self.objects[item_idx].chars[-1].get_text() == '\n':
                            del self.objects[item_idx].chars[-1]
                        
                        next_idx = idx + 1
                        
                        while next_idx < len(self.objects):
                            
                            if not isinstance(self.objects[next_idx], pdfhelper.CharCollection) or not len(self.objects[next_idx]):
                                break

                            else:
                                style = pdfhelper.FontStyle(self.objects[next_idx].chars[0])
                        
                                if style.font_is("DejaVuSansMono"):
                                    if abs(self.objects[item_idx].chars[0].y1 - self.objects[next_idx].chars[0].y1) < 4:

                                        if self.objects[item_idx].x1() > self.objects[next_idx].x1():
                                            current_item = self.objects[item_idx]
                                            next_item = self.objects[next_idx]

                                            self.objects[next_idx] = current_item
                                            self.objects[item_idx] = next_item
                                            
                                next_idx += 1

            idx += 1

        idx = 0

        while idx < len(self.objects):
            item_idx = idx

            if isinstance(self.objects[item_idx], pdfhelper.CharCollection):
                
                if len(self.objects[item_idx]):

                    style = pdfhelper.FontStyle(self.objects[item_idx].chars[0])
                    
                    if style.font_is("DejaVuSansMono"):
                        
                        if self.objects[item_idx].chars[-1].get_text() == '\n':
                            del self.objects[item_idx].chars[-1]
                        
                        next_idx = idx + 1
                        
                        while next_idx < len(self.objects):
                            
                            if not isinstance(self.objects[next_idx], pdfhelper.CharCollection) or not len(self.objects[next_idx]):
                                break

                            else:
                                style = pdfhelper.FontStyle(self.objects[next_idx].chars[0])
                        
                                if style.font_is("DejaVuSansMono"):
                                    if abs(self.objects[item_idx].chars[0].y1 - self.objects[next_idx].chars[0].y1) < 4:

                                        # reindent
                                        indent = int((self.objects[next_idx].rect.x1() - self.objects[item_idx].rect.x2()) / self.objects[item_idx].chars[0].width)
                                        
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



    def assembleTextPartsHalf(self, objects, asm_lines, current_title_ = ""):
        
        idx = 0
        current_title = current_title_

        while idx < len(objects):
            item_idx = idx

            if isinstance(objects[item_idx], pdfhelper.CharCollection) \
                    and self.elementIsTitle(objects[item_idx]):
                
                current_title = self.elementGetTitle(objects[item_idx]).lower()
                idx += 1
                continue

            if isinstance(objects[item_idx], pdfhelper.CharCollection):
                
                next_idx = idx + 1
                
                while next_idx < len(objects):
                    
                    if self.tryAssembleTextPartsHalf(objects[item_idx], objects[next_idx]) \
                            or (asm_lines == True and self.tryAssembleLines(objects[item_idx], objects[next_idx])):
                        
                        del objects[next_idx]
                    else:
                        break
                
                style = pdfhelper.FontStyle(objects[item_idx].chars[0])
                if not style.font_is("DejaVuSansMono"):
                    pdfhelper.delete_collections_pattern(objects[item_idx], "-\n ")

            elif isinstance(objects[item_idx], pdfhelper.Table):
                    
                for items in objects[item_idx].data_storage:
                    self.assembleTextPartsHalf(items, asm_lines, current_title)

            elif isinstance(objects[item_idx], pdfhelper.List):
                
                if len(objects[item_idx].items):
                        
                    next_idx = idx + 1
                    
                    while next_idx < len(objects):
                        
                        if self.tryAssembleTextPartsHalf(objects[item_idx].items[-1], objects[next_idx])\
                                or (asm_lines == True and self.tryAssembleLines(objects[item_idx], objects[next_idx])):

                            del objects[next_idx]
                        else:
                            break
                    
                    for item in objects[item_idx].items:
                        if isinstance(item, pdfhelper.CharCollection):
                            style = pdfhelper.FontStyle(item.chars[0])
                            if not style.font_is("DejaVuSansMono"):
                                pdfhelper.delete_collections_pattern(item, "-\n ")

            idx += 1

    def parsePurposes(self):
        # get first purpose sentence
        idx = 0
        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementGetTitle(self.objects[idx]) == "purpose:":
   
                    idx += 1

                    while idx < len(self.objects):

                        if self.elementIsTitle(self.objects[idx]) or not isinstance(self.objects[idx], pdfhelper.CharCollection):
                            break
                        
                        if isinstance(self.objects[idx], pdfhelper.CharCollection):
                            return pdfhelper.make_char_collection(self.objects[idx].chars)

                        idx += 1
                
                    break                
            idx += 1        

        return ""

    def parseAvailability(self):
        # get first availability sentence
        idx = 0
        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementGetTitle(self.objects[idx]) == "availability:":
   
                    idx += 1

                    while idx < len(self.objects):

                        if self.elementIsTitle(self.objects[idx]) or not isinstance(self.objects[idx], pdfhelper.CharCollection):
                            break
                        
                        if isinstance(self.objects[idx], pdfhelper.CharCollection):
                            return self.objects[idx]

                        idx += 1
                
                    break                
            idx += 1        

        return ""
    
    def parseListAssemble(self):

        # make table for formats
        idx = 0
        title_idx = 0
        start_assembly_index = 0 
        end_assembly_index = 0 
        assembly_table = []

        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementGetTitle(self.objects[idx]) == "assembly:":
                    
                    title_idx = idx
                    idx += 1
                    start_assembly_index = idx

                    while idx < len(self.objects):

                        if self.elementIsTitle(self.objects[idx]) or not isinstance(self.objects[idx], pdfhelper.CharCollection):
                            break

                        assembly_table.append(self.objects[idx])
                        idx += 1
                        end_assembly_index = idx
                
                    break                

            idx += 1

        return (title_idx, start_assembly_index, end_assembly_index, assembly_table)
    
    def createAssembleTables(self):
        purposes = self.parsePurposes()
        availability = self.parseAvailability()
        assemble_list = self.parseListAssemble()
        
        result_format_table = []

        for entry in assemble_list[3]:
            result_format_table.append([[entry], [availability], [purposes]])

        self.instFormatTable = result_format_table
        self.objects.insert(assemble_list[2], pdfhelper.Table(result_format_table, True, 3))
        self.objects[assemble_list[2]].set_y1(self.objects[assemble_list[0]].y1() + 2)

        del self.objects[assemble_list[1]:assemble_list[2]]

    def postFixEncodingArea(self):
       
        idx = 0
        current_title = ""
        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementIsTitle(self.objects[idx]): 
                    current_title = self.elementGetTitle(self.objects[idx]).strip().lower()

            if current_title == "format:":

                if isinstance(self.objects[idx], pdfhelper.Table):
                    try:
                        columns = self.objects[idx].columns()
                        
                        column_bit_ranges = []
                        column_bit_sizes = self.objects[(idx + 1): (idx + columns + 1)]

                        column_bit_sizes.sort(key=functools.cmp_to_key(pdfhelper.sort_lefttoright))

                        ranges_count = 0

                        for bits in column_bit_sizes:
                            bits_int = int(str(bits).strip())
                            if bits_int == 1:
                                ranges_count += 1
                            else:
                                ranges_count += 2

                        original_ranges_count = 0
                        
                        for sub_idx in range(idx - 1, max(-1, idx - ranges_count - 1), -1):

                            if not isinstance(self.objects[sub_idx], pdfhelper.CharCollection):
                                break

                            try:
                                bits_int = int(str(self.objects[sub_idx]).strip())
                            except:
                                break

                            original_ranges_count += 1
                        
                        ranges_count = original_ranges_count
                        
                        #column_bits_list =  [n for n in self.objects[(idx - ranges_count) : idx]]
                        
                        #ranges_idx = 0
                        #for bits in column_bit_sizes:
                        #    bits_int = int(str(bits).strip())
                        #    if bits_int == 1:
                        #        column_bit_ranges.append(column_bits_list[ranges_idx : (ranges_idx + 1)])
                        #        ranges_idx += 1
                        #    else:
                        #        column_bit_ranges.append(column_bits_list[ranges_idx : (ranges_idx + 2)])
                        #        ranges_idx += 2

                        #self.objects[idx].add_row(column_bit_ranges, True)
                        self.objects[idx].add_row([[n] for n in column_bit_sizes], False)
                        
                        # delete top items
                        del self.objects[(idx - ranges_count) : idx]
                        
                        # delete bottom items
                        del self.objects[(idx + 1 - ranges_count): (idx + columns + 1 - ranges_count)]

                        if idx - ranges_count < 0:
                            breakpoint() 

                        idx -= (ranges_count) 

                    except Exception as e:
                        pass

            idx += 1
    
    def makeSubtitlesFormat(self):
        
        idx = 0
        
        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementGetTitle(self.objects[idx]) == "format:":
   
                    if isinstance(self.objects[idx + 1], pdfhelper.CharCollection):

                        for char in self.objects[idx + 1].chars:
                            char.fontname = "DejaVuSerif-Bold"

            idx += 1
    
    def collapseFormatTitles(self):

        idx = 0
        has_format = False

        while idx < len(self.objects):

            if isinstance(self.objects[idx], pdfhelper.CharCollection):
                if self.elementGetTitle(self.objects[idx]) == "format:":
                    
                    if has_format:
                        del self.objects[idx]
                    else:
                        has_format = True
                        idx += 1
                else:
                    idx += 1
            else:
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
                
        # slice collections on sub collections by title name 
        idx = 0
        while idx < len(self.objects):
            if self.elementIsTitle(self.objects[idx]):
                result = pdfhelper.divide_collection_by_font(self.objects[idx])
                
                del self.objects[idx]

                for collection in result:
                    self.objects.insert(idx, collection)
                    idx += 1

            else:
                idx += 1


        # slice collections on Purpose title
        idx = 0
        is_in_purpose_title = False
        while idx < len(self.objects):
            
            if self.elementGetTitle(self.objects[idx]) == "Purpose":
                is_in_purpose_title = True
                idx += 1
            elif self.elementIsTitle(self.objects[idx]):
                if is_in_purpose_title:
                    break
                idx += 1
            else:
                if is_in_purpose_title and isinstance(self.objects[idx], pdfhelper.CharCollection):
                    result = pdfhelper.divide_collection_by_pattern(self.objects[idx], "\n ")
                    
                    del self.objects[idx]

                    for collection in result:

                        if collection.chars[-1].get_text() == ' ' or collection.chars[-1].get_text() == '\n': 
                            del collection.chars[-1]
                        if collection.chars[-1].get_text() == ' ' or collection.chars[-1].get_text() == '\n': 
                            del collection.chars[-1]
                        
                        self.objects.insert(idx, collection)
                        idx += 1

                else:
                    idx += 1


        # fixup opcode tables
        self.postFixEncodingArea()

        # assemble text parts on half word returned to new line
        self.assembleTextPartsHalf(self.objects, False)

        # fixup formats before assemble PS
        idx = 0
        current_title = ""

        while idx < len(self.objects):

            item_idx = idx

            if isinstance(self.objects[item_idx], pdfhelper.CharCollection) \
                    and self.elementIsTitle(self.objects[item_idx]):
                
                current_title = self.elementGetTitle(self.objects[item_idx]).lower()
                idx += 1
                continue
            
            if current_title == "format":
                if isinstance(self.objects[idx], pdfhelper.CharCollection):
                        
                    while len(self.objects[idx]) and self.objects[idx].chars[0].get_text() == ' ':
                        del self.objects[idx].chars[0]
                    
                    if len(self.objects[idx]) == 1 and self.objects[idx].chars[0].get_text() == '\n':
                        del self.objects[idx]
                        idx -= 1                

            idx += 1

        self.erasePseudocodeLines()
        # assemble pseudocode text parts
        self.assemblePseudocode()

        # make tables
        self.createAssembleTables()

        # assemble text parts on half word returned to new line
        self.assembleTextPartsHalf(self.objects, True)

        self.makeSubtitlesFormat()
        self.collapseFormatTitles()

        del self.objects[0] # erase instruction name as title

        return self.mergeText(self.objects, False)

    def flush(self):
        #try:
        displayable = self.prepareDisplay()
        #except Exception as e:
        #    print("Failed to prepare for " + str(e))
        #    raise
        
        self.outputFile(displayable)
    
    def processPage(self, page):
        
        idx = 0
        while idx < len(page._objs):
            if isinstance(page._objs[idx], LTRect):
                if page._objs[idx].height >= 30:
                    del page._objs[idx]
                else:
                    idx += 1
            else:
                idx += 1

        proc_page = processedPage(page, 0)

        newTitleElements = []

        if len(proc_page.objects) >= 2 and isinstance(proc_page.objects[1], pdfhelper.CharCollection):
            if proc_page.objects[1].y1() < 50 \
                    and str(proc_page.objects[1]).strip().lower() == 'instruction deﬁnitions':
                
                if isinstance(proc_page.objects[2], pdfhelper.CharCollection) \
                        and proc_page.objects[2].chars[0].height >= 25\
                        and proc_page.objects[2].font_name() == "DejaVuSerif-Bold":
                    
                    newTitleElements = [
                        str(proc_page.objects[2]).strip()
                    ]

                    if len(self.TitleElements) and newTitleElements[0] == self.TitleElements[0]:
                        self.TitleElements = newTitleElements
                    elif len(self.TitleElements) == 0:
                        self.TitleElements = newTitleElements
                    elif len(self.objects) > 0:
                    
                        #try:
                        self.flush()
                        self.success += 1
                        #except Exception as e:
                        #    print("*** couldn't flush to disk")
                        #    self.fail += 1
                        
                        self.y_offset = 0
                        self.objects = []
                        self.instFormatTable = []
                        self.TitleElements = newTitleElements
                
                proc_page = processedPage(page, self.y_offset) # update page with new y offset

                # shift page and add content
                proc_page.cut_off(0, 10000, 65, 725)

                self.y_offset += proc_page.page_heigth 
                self.objects += proc_page.objects
                return True

        return False


    def outputFile(self, displayable):

        title = self.TitleElements[0]

        title = title.replace('<', '_').replace('>', '_').replace('-', '_').replace('{', '_').replace('}', '_')
        path = "%s/%s" % (self.outputDir, title.replace("/", "_").replace(" ", ""))
        print("Writing to %s" % path)
        file_data = self.outputSection(displayable)
        with open(path + ".json", "w") as fd:
            json.dump(file_data, fd, indent = 4)
        with open(path + ".html", "wb") as fd:
            string_ = "<!DOCTYPE html>" + genHtmlDescription(file_data).to_html() 
            fd.write(string_.encode("UTF-8"))
             
    def outputSection(self, displayable):
        
        rootname = []

        if len(self.instFormatTable):
            rootname = [
                str(self.instFormatTable[0][0][0]).strip(),
                str(self.instFormatTable[0][2][0]).strip()
            ]
        
        root_json = {
            "docname": self.docname,
            "rootname": rootname, 
            "elements": [],
            "attributes": []
        }

        self.__title_stack = []
        
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
                    
                    if len(self.__title_stack):
                        heading = self.__title_stack[-1]
                        if heading.startswith("encoding"):
                            # operands encoding
                            children = element.get_at(col, row)
                        else:
                            children = self.mergeText(element.get_at(col, row), True)
                    else:
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
        
        assert False
        
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

        if self.elementIsTitle(element):

            parent_element["elements"].append({
                        "type": "title",
                        "text": str(element),
                        "elements": [],
                        "attributes": ["h2" if self.elementGetTitle(element) in self.main_titles else "h3"],
                        "level": 2 if self.elementGetTitle(element) in self.main_titles else 3
                    }) 
            
            return True
        
        elif style.font_is("DejaVuSansMono"):
            current_paragraph["attributes"].append("code")

            if len(self.__title_stack) \
                    and (
                            self.__title_stack[-1] == "operation:" \
                                or self.__title_stack[-1] == "format:" \
                                or (len(self.__title_stack) >= 2 and self.__title_stack[-2] == "format:")):
                
                indent = int((math.ceil(element.bounds().x1()) - 72) / element.chars[0].width)
                element.chars = [pdfhelper.FakeChar(' ')] * indent + element.chars
            
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
                    current_char_attributes.append("Italic")

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
    
    def mergeText(self, lines, isinTable):
       
        if len(lines) == 0: return []
        
        #lines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
        merged = [lines[0]]

        for line in lines[1:]:
            
            last = merged[-1]
            if isinstance(last, pdfhelper.List) and len(last.items):            
                last = last.items[-1]
            
            if isinstance(line, pdfhelper.CharCollection) \
                    and isinstance(last, pdfhelper.CharCollection) \
                    and (isinTable or line.font_name() != "DejaVuSansMono")\
                    and not self.elementIsTitle(line) \
                    and not self.elementIsTitle(last):
                
                same_x = pdfhelper.pretty_much_equal(line.rect.x1(), last.rect.x1())
                same_size = last.font_size() == line.font_size()
                decent_descent = abs(line.approx_rect.y1() - last.approx_rect.y2()) < 1.2

                if same_x and same_size and decent_descent:
                    lastChar = last.chars[-1].get_text()[-1]
                
                    if not (lastChar == "-" or lastChar == "/"):
                        last.append_char(" ")
                
                    last.append(line)
                else:
                    merged.append(line)
            else:
                merged.append(line)

        return merged
    
