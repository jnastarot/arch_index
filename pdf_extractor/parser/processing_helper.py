from copy import deepcopy, copy
from pdfminer.layout import *
from htmltext import *
import pdfhelper
import functools

class processedPage(object):
    def __init__(self, page, y_offset, discardOneCellTables = True):
        self.curves = []
        self.textLines = []
        self.rects = []
        self.y_offset = y_offset
        self.page_width = 0
        self.page_heigth = 0
        self.discardOneCellTables = discardOneCellTables
        self.objects = []

        self.process_page(page)

    def __fix_point(self, p):
        return (p[0], (self.y_offset + self.page_heigth) - p[1])
    
    def __fix_rect(self, r):
        return pdfhelper.Rect(r.x1(), (self.y_offset + self.page_heigth) - r.y1(), r.x2(), (self.y_offset + self.page_heigth) - r.y2())
    
    def __fix_bbox(self, bbox):
        return self.__fix_rect(pdfhelper.Rect(bbox[0], bbox[3], bbox[2], bbox[1]))
       
    def __check_in_the_box(self, box, object_rect):
            
        if object_rect.y1() < box.y1(): return False
        if object_rect.y2() > box.y2(): return False
        if object_rect.x1() < box.x1(): return False
        if object_rect.x2() > box.x2(): return False

        return True
    
    def __merge_text(self, lines):
       
        if len(lines) == 0: return []
        
        lines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
        merged = [lines[0]]
        for line in lines[1:]:
            last = merged[-1]
            same_x = pdfhelper.pretty_much_equal(line.x1(), last.x1())
            same_size = last.font_size() == line.font_size()
            decent_descent = line.approx_rect.y1() - last.approx_rect.y2() < 1.2
            if same_x and same_size and decent_descent:
                lastChar = last.chars[-1].get_text()[-1]
                if not (lastChar == "-" or lastChar == "/"):
                    last.append_char(" ")
                last.append(line)
            else:
                merged.append(line)
        return merged
    
    def process_text_line(self, line):
        coll = pdfhelper.CharCollection(deepcopy(line), self.__fix_bbox(line.bbox), self.y_offset, self.page_heigth, True)
        coll.approx_rect = self.__fix_rect(coll.approx_rect)
        if len(coll.chars) > 0:
            self.textLines.append(coll)
    
    def process_rect(self, rect):
        self.rects.append(self.__fix_bbox(rect.bbox))

    def process_curve(self, curve):
        if len(curve.pts):
            curve = pdfhelper.Curve([self.__fix_point(p) for p in curve.pts])
            self.curves.append(curve)
    
    def process_line(self, line):
        self.rects.append(self.__fix_bbox(line.bbox))

    def process_item(self, item, n=0):
        if isinstance(item, LTTextLineHorizontal):
            self.process_text_line(deepcopy(item))
        elif isinstance(item, LTRect) or isinstance(item, LTLine):
            self.process_rect(deepcopy(item))
        elif isinstance(item, LTCurve):
            self.process_curve(deepcopy(item))
        elif isinstance(item, LTContainer):
            for obj in item:
                self.process_item(obj, n+1)
        elif isinstance(item, LTImage):
            print("That Image OMFG!")
        elif isinstance(item, LTChar):
            pass
        else:
            breakpoint()


    def process_page(self, page):
        
        self.curves = []
        self.textLines = []
        self.rects = []
        self.page_heigth = (page.bbox[3] - page.bbox[1])
        self.page_width = (page.bbox[2] - page.bbox[0])

        for item in page:
            self.process_item(item)

        self.rects.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
        self.textLines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))

        #textLines__ = self.textLines[24:28]
        #textLines__.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))

        frames = []
        lines = []
        tables = []
        orphanCurves = []
        orphans = []

        rect_for_delete = []

        # try to convert curve to rect
        #for curve_idx in range(0, len(self.curves)):
        #    curve_first = self.curves[curve_idx]
        #    self.rects.append(curve_first.bounds())

        self.rects.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))

        # try to escape inwindow page rects
        for rect_idx in range(0, len(self.rects)):
            rect_first = self.rects[rect_idx]

            if (abs(rect_first.height() - self.page_heigth) < 5 \
                and abs(rect_first.width() - self.page_width) < 5) :

                rect_for_delete.append(rect_idx)
                
        # try to escape bad rects
        for rect_idx in range(0, len(self.rects)):
            rect_first = self.rects[rect_idx]

            for next_rect_idx in range(rect_idx + 1, len(self.rects)):
                rect_next = self.rects[next_rect_idx]

                if (rect_first.horizontal() and rect_next.horizontal()) \
                        or (rect_first.vertical() and rect_next.vertical()):

                    first_coord = 0
                    second_coord = 0
                    first_is_bigger = False
                    first_is_first_item = True
                    delta_coord = 0

                    if rect_first.horizontal():

                        first_coord = rect_first.y1()
                        second_coord = rect_next.y1()

                        min_x_line1 = min(rect_first.x1(), rect_first.x2())
                        max_x_line1 = max(rect_first.x1(), rect_first.x2())
                        min_x_line2 = min(rect_next.x1(), rect_next.x2())
                        max_x_line2 = max(rect_next.x1(), rect_next.x2())

                        if max_x_line1 < min_x_line2 or max_x_line2 < min_x_line1:
                            total_width = 0
                        else:
                            total_width = min(max_x_line1, max_x_line2) - max(min_x_line1, min_x_line2)


                        first_is_bigger = rect_first.width() >= rect_next.width()
                    #else:
                    #    first_coord = rect_first.y1()
                    #    second_coord = rect_next.y1()
                    #    first_is_bigger = rect_first.height() >= rect_next.height()
                         
                        first_is_first_item = first_coord <= second_coord

                        if first_is_first_item:
                            delta_coord = second_coord - first_coord
                        else:
                            delta_coord = first_coord - second_coord 

                        if total_width > 5 and delta_coord > 0 and delta_coord < 3:
                            if first_is_bigger:
                                rect_for_delete.append(next_rect_idx)
                            else:
                                rect_for_delete.append(rect_idx)

        rect_for_delete = set(rect_for_delete)

        idx = 0
        for del_idx in rect_for_delete:
            del self.rects[del_idx - idx]
            idx += 1

        # assemble rects to cells and lines
        for rect in self.rects:
            if (rect.horizontal() and rect.height() > 8) or (rect.vertical() and rect.width() > 8):
                table = pdfhelper.SingleCellTable([])
                table.rect = rect
                frames.append(table)
            else:
                lines.append(rect)
    
        # assemble lines to tables
        while len(lines) > 0:
            orphans = []

            cluster = pdfhelper.cluster_rects(lines)
            if len(cluster) >= 4:
                try:
                    frames.append(pdfhelper.Table(cluster))
                    continue
                except: pass

            orphans += cluster
        
        # fill tables with text lines
        for table in frames:
            orphans = []
            bounds = table.bounds()
            
            for line_index in range(0, len(self.textLines)):      
                line = self.textLines[line_index]
                
                if bounds.contains(line.bounds()):
                    table.get_at_pixel(line.rect.xmid(), line.rect.ymid()).append(line)
                else:
                    orphans.append(line)
                    
            self.textLines = orphans
            tables.append(table)
   
        self.textLines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
   
        # compact tables with inner tables
        all_tables = sorted(tables, key=lambda x: x.bounds().area())
        tables = set()
        figures = set()
        sublevel_figures = set()

        inner_table_index = 0
        while inner_table_index < len(all_tables):
            
            smaller = all_tables[inner_table_index]
            
            if smaller.rows() != 1 or smaller.columns() != 1:
                tables.add(smaller)
            else:
                top_table_index = inner_table_index + 1
                smaller_bounds = smaller.bounds()
            
                while top_table_index < len(all_tables):
                    
                    bigger = all_tables[top_table_index]

                    if bigger.bounds().contains(smaller_bounds) and \
                            bigger.get_at_pixel(smaller_bounds.xmid(), smaller_bounds.ymid()) != None:

                        bigger.get_at_pixel(smaller_bounds.xmid(), smaller_bounds.ymid()).append(smaller)
                        figures.add(bigger)
                        figures.add(smaller)
                        sublevel_figures.add(smaller)
                        break

                    top_table_index += 1
                else:
                    tables.add(smaller)
            inner_table_index += 1
        
        top_figures = [pdfhelper.Figure(t) for t in figures - sublevel_figures]
        top_tables = list(tables - figures)
     
        # insert curves to tables
        for figure in top_figures:
            for curve in self.curves:
                if figure.bounds().contains(curve.bounds()):
                    figure.data.get_at(0,0).append(curve)
                else:
                    orphanCurves.append(curve)
            curves = orphanCurves
            orphanCurves = []

        # if table has only one cell, so erase the table and get back the text to lines 
        table_index = 0    
        orphans = []

        if self.discardOneCellTables:
            while table_index < len(top_tables):
                count = top_tables[table_index].item_count()
                if count > 1: table_index += 1
                else:
                    if count == 1:
                        orphans += top_tables[table_index].get_at(0,0)
                    top_tables.pop(table_index)

        self.textLines += orphans
        self.textLines.sort(key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))
   
        # lists
        orphans = []
        lists = []
        this_list = []
        idx = 0
        while idx < len(self.textLines):
            
            line = self.textLines[idx]
            
            if isinstance(line, pdfhelper.CharCollection) and len(line) and (line.chars[0].get_text() == "•" or line.chars[0].get_text() == "(cid:129)"):
                if len(line.chars) == 1 or (len(line.chars) == 2 and line.chars[1].get_text() == '\n'):
                    if idx + 1 < len(self.textLines):
                        idx += 1
                        line = self.textLines[idx]
                else:
                    for char_idx in range(1, len(line.chars)):
                        if not line.chars[char_idx].get_text().isspace(): break
                    line.chars = line.chars[char_idx:]
                this_list.append(line)
            else:
                if len(this_list) > 0:
                    lists.append(pdfhelper.List(this_list))
                    this_list = []
                orphans.append(line)
            idx += 1        


        self.objects = sorted(orphans + lists + orphanCurves + top_tables + top_figures, 
                                    key=functools.cmp_to_key(pdfhelper.sort_topdown_ltr))

    def cut_off(self, content_x_from, content_x_to, content_y_from, content_t_to):

        box = pdfhelper.Rect(
            content_x_from, 
            content_y_from + self.y_offset, 
            content_x_to, 
            content_t_to + self.y_offset)

        idx = 0
        while idx < len(self.objects):
            if not self.__check_in_the_box(box, self.objects[idx]):          
                del self.objects[idx]
            else:
                idx += 1

        idx = 0
        while idx < len(self.rects):
            if not self.__check_in_the_box(box, self.rects[idx]):          
                del self.rects[idx]
            else:
                idx += 1

        return