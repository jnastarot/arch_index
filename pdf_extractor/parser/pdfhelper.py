#!/usr/bin/env python
# -*- coding: UTF-8 -*-
from copy import deepcopy, copy
import functools
import pdfminer.layout

class pseudofont:
    def __init__(self, name):
        self.fontname = name
        return
    def is_vertical(self):
        return False
    def get_height(self):
        return 12
    def get_descent(self):
        return 1


def get_char_font_name(char):
    if isinstance(char, pdfminer.layout.LTChar):
        if char.fontname.find('+') == -1:
            return char.fontname
        else:
            return char.fontname[char.fontname.find('+') + 1:]
    return ""

def get_char_font_size(char):
    if isinstance(char, pdfminer.layout.LTChar):
        return char.matrix[0]
    return 0

def make_sint_char_collection(string, fontname):
    
    char = pdfminer.layout.LTChar([0, 0, 0, 0, 0, 0], pseudofont(fontname), 12, 1, 0, string, 0, (0, 0))

    return CharCollection([char], Rect(0, 0, 0, 0), 0, 0, False)


def make_char_collection(chars):

    is_first_setted = False
    is_second_setted = False

    for idx in range(0, len(chars)):

        if not is_first_setted:
            if isinstance(chars[idx], pdfminer.layout.LTChar):
                first_box = chars[idx].bbox
                is_first_setted = True
        else:
            if isinstance(chars[idx], pdfminer.layout.LTChar):
                last_box = chars[idx].bbox
                is_second_setted = True
    
    if not is_second_setted:
        last_box = first_box

    return CharCollection(chars, Rect(
                                    first_box[0], 
                                    first_box[1], 
                                    last_box[2], 
                                    last_box[3]), 
                                    0, 0, False)

def divide_collection_by_font(collection):

    if len(collection.chars) == 0:
        return [collection]

    collections = []

    chars_line = []
    first_box = (0, 0, 0, 0)
    last_box = (0, 0, 0, 0)

    current_font = ""
    current_idx = 0

    while current_idx < len(collection.chars):

        current_char = collection.chars[current_idx]
        current_idx += 1

        if isinstance(current_char, pdfminer.layout.LTChar):
            if current_font == "":
                current_font = get_char_font_name(current_char)
                first_box = current_char.bbox
                last_box = current_char.bbox

            if current_font == get_char_font_name(current_char):
                chars_line.append(current_char)
                last_box = current_char.bbox
            else:
                if len(chars_line):
                    collections.append(CharCollection(chars_line, 
                                                Rect(
                                                    first_box[0], 
                                                    collection.y_offset + first_box[1], 
                                                    last_box[2], 
                                                    collection.y_offset + last_box[3]), 
                                                    collection.y_offset, collection.page_height, False))

                chars_line = [current_char]
                current_font = get_char_font_name(current_char)
                first_box = current_char.bbox
                last_box = current_char.bbox

        else:       
            chars_line.append(current_char)

    if len(chars_line):
        collections.append(CharCollection(chars_line, Rect(
                                                  first_box[0], 
                                                  collection.y_offset + first_box[1], 
                                                  last_box[2], 
                                                  collection.y_offset + last_box[3]), 
                                                  collection.y_offset, collection.page_height, False))
    return collections


def divide_collection_by_font_name(collection, fontname):

    if len(collection.chars) == 0:
        return [collection]

    collections = []

    chars_line = []
    first_box = (0, 0, 0, 0)
    last_box = (0, 0, 0, 0)

    current_font = ""
    current_idx = 0

    while current_idx < len(collection.chars):

        current_char = collection.chars[current_idx]
        current_idx += 1

        if isinstance(current_char, pdfminer.layout.LTChar):
            if current_font == "":
                current_font = get_char_font_name(current_char)
                first_box = current_char.bbox
                last_box = current_char.bbox

            is_match_first = current_font.find(fontname) != -1
            is_match_second = get_char_font_name(current_char).find(fontname) != -1

            if is_match_first == is_match_second:
                chars_line.append(current_char)
                last_box = current_char.bbox
            else:
                if len(chars_line):
                    collections.append(CharCollection(chars_line, 
                                                Rect(
                                                    first_box[0], 
                                                    collection.y_offset + first_box[1], 
                                                    last_box[2], 
                                                    collection.y_offset + last_box[3]), 
                                                    collection.y_offset, collection.page_height, False))

                chars_line = [current_char]
                current_font = get_char_font_name(current_char)
                first_box = current_char.bbox
                last_box = current_char.bbox

        else:       
            chars_line.append(current_char)

    if len(chars_line):
        collections.append(CharCollection(chars_line, Rect(
                                                  first_box[0], 
                                                  collection.y_offset + first_box[1], 
                                                  last_box[2], 
                                                  collection.y_offset + last_box[3]), 
                                                  collection.y_offset, collection.page_height, False))
    return collections


def divide_collection_by_index(collection, idx):

    collections = [
        CharCollection(collection.chars[0:idx], collection.rect, collection.y_offset, collection.page_height, False),
        CharCollection(collection.chars[idx:], collection.rect, collection.y_offset, collection.page_height, False),
    ]

    idx = 0
    while idx < len(collections[1].chars):
        if not isinstance(collections[1].chars[idx], pdfminer.layout.LTAnno):
            collections[1].set_x1(collections[1].chars[idx].x0)
            break
        idx += 1

    return collections

def divide_collection_by_pattern(collection, pattern):

    if len(collection.chars) == 0:
        return [collection]

    collections = []
    first_box = (0, 0, 0, 0)
    last_box = (0, 0, 0, 0)
    current_idx = 0

    while current_idx < len(collection.chars):

        current_pattern = ""

        for idx in range(0, len(pattern)):
            if len(collection.chars) > current_idx + idx:  
                current_pattern += collection.chars[current_idx + idx].get_text()
            else:
                break

        if current_pattern == pattern:

            sub_current_idx = 0
            is_first_setted = False
            is_second_setted = False

            for idx in range(0, (sub_current_idx + len(pattern))):

                if not is_first_setted:
                    if isinstance(collection.chars[idx], pdfminer.layout.LTChar):
                        first_box = collection.chars[idx].bbox
                        is_first_setted = True
                else:
                    if isinstance(collection.chars[idx], pdfminer.layout.LTChar):
                        last_box = collection.chars[idx].bbox
                        is_second_setted = True
           
            if not is_second_setted:
                last_box = first_box

            collections.append(CharCollection(collection.chars[0:current_idx + len(pattern)], 
                                Rect(
                                    first_box[0], 
                                    collection.y_offset + first_box[1], 
                                    last_box[2], 
                                    collection.y_offset + last_box[3]), 
                                    collection.y_offset, collection.page_height, False))
            
            del collection.chars[0:current_idx + len(pattern)]

            current_idx = 0
        else:
            current_idx += 1


    if len(collection.chars):
        current_idx = 0
        is_first_setted = False
        is_second_setted = False

        for idx in range(0, len(collection.chars)):

            if not is_first_setted:
                if isinstance(collection.chars[idx], pdfminer.layout.LTChar):
                    first_box = collection.chars[idx].bbox
                    is_first_setted = True
            else:
                if isinstance(collection.chars[idx], pdfminer.layout.LTChar):
                    last_box = collection.chars[idx].bbox
                    is_second_setted = True
        
        if not is_second_setted:
            last_box = first_box

        collections.append(CharCollection(collection.chars, Rect(
                                                  first_box[0], 
                                                  collection.y_offset + first_box[1], 
                                                  last_box[2], 
                                                  collection.y_offset + last_box[3]), 
                                                  collection.y_offset, collection.page_height, False))

    return collections

def delete_collections_pattern(collection, pattern):

    if len(collection.chars) == 0:
        return [collection]

    current_idx = 0

    while current_idx < len(collection.chars):

        current_pattern = ""

        for idx in range(0, len(pattern)):
            if len(collection.chars) > current_idx + idx:  
                current_pattern += collection.chars[current_idx + idx].get_text()
            else:
                break

        if current_pattern == pattern:
            del collection.chars[current_idx: current_idx + len(pattern)]
        else:
            current_idx += 1


def sort_rect_by_position(x, y, dimension):
    return lambda rect: y(rect) * dimension + x(rect)

def sort_rect(a, b):
    ydiff = a.y1() - b.y1()
    if abs(ydiff) > 0.7: return int(ydiff * 100)
    
    xdiff = a.x1() - b.x1()
    if abs(xdiff) > 0.7: return int(xdiff * 100)
    
    heightdiff = a.y2() - b.y2()
    return int(-heightdiff * 100)

def cluster_rects(lines):
    table_group = [lines.pop()]
    just_removed = table_group[:]
    while len(just_removed) > 0:
        removed = []
        for test_against in just_removed:
            i = 0
            while i < len(lines):
                if test_against.intersects(lines[i]):
                    removed.append(lines.pop(i))
                else:
                    i += 1
        table_group += removed
        just_removed = removed
    return table_group

# this is not particularly statistically sound, but I think that it works
def count_segments(list, expected_clusters):
    list.sort()
    expected_distance = (list[-1] - list[0]) / expected_clusters
    last_item = list[0]
    clusters = [1]
    for item in list[1:]:
        if item - last_item < expected_distance:
            clusters[-1] += 1
        else:
            clusters.append(1)
        last_item = item
    return clusters

def pretty_much_equal(a, b, threshold = 2):
    return abs(a - b) < threshold

def sort_lefttoright(a, b):
    aa = a.bounds()
    bb = b.bounds()

    if round(aa.x1()+ 0.49) < round(bb.x1()+ 0.49): return -1
    if round(aa.x1()+ 0.49) > round(bb.x1()+ 0.49): return 1
    return 0

def sort_topdown_ltr(a, b):
    aa = a.bounds()
    bb = b.bounds()

    if round(aa.y1()+ 0.49) < round(bb.y1()+ 0.49): return -1
    if round(aa.y1()+ 0.49) > round(bb.y1()+ 0.49): return 1
    if round(aa.x1()+ 0.49) < round(bb.x1()+ 0.49): return -1
    if round(aa.x1()+ 0.49) > round(bb.x1()+ 0.49): return 1
    return 0

def sort_topdown_ltr_center(a, b):
    aa = a.bounds()
    bb = b.bounds()

    if round(abs(aa.y1() - aa.y2()) + 0.49) < round(abs(bb.y1() - bb.y2()) + 0.49): return -1
    if round(abs(aa.y1() - aa.y2()) + 0.49) > round(abs(bb.y1() - bb.y2()) + 0.49): return 1
    if round(aa.x1()+ 0.49) < round(bb.x1()+ 0.49): return -1
    if round(aa.x1()+ 0.49) > round(bb.x1()+ 0.49): return 1
    return 0


def center_aligned_table(source):
    assert source.rows() == 1 and source.columns() == 1
    bounds = source.bounds()
    contents = source.get_at(0, 0)[:]
    contents.sort(key=functools.cmp_to_key(sort_topdown_ltr))
    column_centers = []
    last_y = contents[0].bounds().y1()
    for item in contents:
        if not pretty_much_equal(last_y, item.bounds().y1()): break
        column_centers.append(item.bounds().xmid())
    
    table = []
    row = [[]] * len(column_centers)
    for item in contents:
        item_bounds = item.bounds()
        if not pretty_much_equal(item_bounds.y1(), last_y):
            if any((len(c) == 0 for c in row)):
                for i in range(0, len(column_centers)):
                    table[-1][i] += row[i]
            else: table.append(row)
            row = [[]] * len(column_centers)
            last_y = item_bounds.y1()
        
        col_index = None
        min_dist = float("inf")
        for i in range(0, len(column_centers)):
            distance = abs(item_bounds.xmid() - column_centers[i])
            if distance < min_dist:
                min_dist = distance
                col_index = i
        
        row[col_index] = [item]
    
    if any((len(c) == 0 for c in row)):
        for i in range(0, len(column_centers)):
            table[-1][i] += row[i]
    else: table.append(row)
    
    return ImplicitTable(bounds, table)

def left_aligned_table(source):
    assert source.rows() == 1 and source.columns() == 1
    bounds = source.bounds()
    contents = source.get_at(0, 0)[:]
    contents.sort(key=functools.cmp_to_key(sort_topdown_ltr))
    
    table = []
    row = []
    columns = []
    last_y = contents[0].bounds().y1()
    for item in contents:
        item_bounds = item.bounds()
        if not pretty_much_equal(item_bounds.y1(), last_y):
            break
        columns.append(item_bounds.x1())
    
    last_y = contents[0].bounds().y1()
    row = [[]] * len(columns)
    for item in contents:
        item_bounds = item.bounds()
        if not pretty_much_equal(item_bounds.y1(), last_y):
            if any((len(c) == 0 for c in row)):
                for i in range(0, len(columns)):
                    table[-1][i] += row[i]
            else: table.append(row)
            row = [[]] * len(columns)
            last_y = item_bounds.y1()
        
        for i in range(0, len(columns)):
            if pretty_much_equal(item_bounds.x1(), columns[i]):
                col_index = i
                break
        else:
            print("No matching column!")
            print(columns)
            print(contents)
            #raise Exception("No matching column!")
        
        row[col_index] = [item]
    
    if any((len(c) == 0 for c in row)):
        for i in range(0, len(columns)):
            table[-1][i] += row[i]
    else: table.append(row)
    
    return ImplicitTable(bounds, table)

class Rect(object):
    def __init__(self, x1, y1, x2, y2):
        self.__x1 = x1
        self.__x2 = x2
        self.__y1 = y1
        self.__y2 = y2

    def debug_html(self, color="black", cls="black"):
        fmt = '<div class="%s" style="position:absolute;left:%fpx;top:%fpx;width:%fpx;height:%fpx;border:1px %s solid;background-color:%s"></div>'
        return fmt % (cls, self.x1(), self.y1(), self.width(), self.height(), color, color)
    
    def bounds(self): return Rect(self.__x1, self.__y1, self.__x2, self.__y2)
    def x1(self): return self.__x1
    def x2(self): return self.__x2
    def y1(self): return self.__y1
    def y2(self): return self.__y2
    
    def set_x1(self, x): self.__x1 = x
    def set_y1(self, y): self.__y1 = y
    def set_y2(self, y): self.__y2 = y

    def xmid(self): return self.__x1 + (self.__x2 - self.__x1) / 4
    def ymid(self): return (self.__y1 + self.__y2) / 2
    
    def width(self): return abs(self.__x1 - self.__x2)
    def height(self): return abs(self.__y1 - self.__y2)
    def area(self): return self.width() * self.height()
    
    def points(self):
        return ((self.__x1, self.__y1), (self.__x1, self.__y2), (self.__x2, self.__y2), (self.__x2, self.__y1))
    
    def union(self, rect):
        return Rect(min(rect.x1(), self.x1()), min(rect.y1(), self.y1()), max(rect.x2(), self.x2()), max(rect.y2(), self.y2()))
    
    def vertical(self): return self.width() < self.height()
    def horizontal(self): return self.height() < self.width()
    
    def __repr__(self):
        orientation = "V" if self.vertical() else "H"
        return "Rect%s(%0.2f,%0.2f,%0.2f,%0.2f)" % (orientation, self.x1(), self.y1(), self.x2(), self.y2())
    
    def intersects(self, that, threshold = 2):
        if self.x1() - that.x2() - threshold > 0:
            return False
        if that.x1() - self.x2() - threshold > 0:
            return False
        if self.y1() - that.y2() - threshold > 0:
            return False
        if that.y1() - self.y2() - threshold > 0:
            return False
        return True
    
    def contains(self, that):
        return (self.x1() <= that.x1() or (abs(self.x1() - that.x1()) < 2)) \
                    and self.x2() >= that.x2() \
                    and (self.y1() <= that.y1() or (abs(self.y1() - that.y1()) < 2))\
                    and self.y2() >= that.y2()

class Curve(object):
    def __init__(self, points):
        assert len(points) > 1
        x = [float("inf"), float("-inf")]
        y = x[:]
        for p in points:
            x[0] = min(p[0], x[0])
            x[1] = max(p[0], x[1])
            y[0] = min(p[1], y[0])
            y[1] = max(p[1], y[1])
        self.__bounds = Rect(x[0], y[0], x[1], y[1])
        self.points = points
    
    def bounds(self): return self.__bounds
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()
    
class List(object):
    def __init__(self, items):
        assert len(items) > 0
        self.items = items
        self.rect = items[0].bounds()
        for i in items[1:]:
            self.rect = self.rect.union(i.bounds())
    
    def bounds(self): return self.rect
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()

class TableBase(object):
    def get_at(self, x, y): raise Exception("Not implemented")
    def get_everything(self): raise Exception("Not implemented")
    def rows(self): raise Exception("Not implemented")
    def item_count(self): raise Exception("Not implemented")
    def columns(self): raise Exception("Not implemented")
    def bounds(self): raise Exception("Not implemented")
    def cell_size(self, x, y): raise Exception("Not implemented")
    def data_index(self, x, y): raise Exception("Not implemented")

class ImplicitTable(TableBase):
    def __init__(self, bounds, table_data):
        self.__bounds = bounds
        self.__data = table_data
    
    def bounds(self): return self.__bounds
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()
    
    def debug_html(self):
        result = '<table border="1">'
        for row in self.__data:
            result += '<tr>'
            for cell in row:
                result += '<td>'
                for element in cell:
                    result += str(element).replace("<", "&lt;").replace(">", "&gt;")
                result += '</td>'
            result += '</tr>'
        result += '</table>'
        return result
        
    def get_at_pixel(self, x, y):
        raise Exception("Not supported on implicit tables")
    
    def get_at(self, x, y):
        return self.__data[y][x]
    
    def get_everything(self):
        result = []
        for c in self.__data: result += c
        return result
    
    def item_count(self):
        count = 0
        for row in self.__data:
            for cell in row:
                count += len(cell)
        return count
    
    def rows(self): return len(self.__data)
    def columns(self): return len(self.__data[0])
    
    def cell_size(self, x, y):
        assert x >= 0 and x < self.columns()
        assert y >= 0 and y < self.rows()
        return (1, 1)
    
    def data_index(self, x, y): return self.__data


class Table(TableBase):

    def __init__(self, group, group_is_data = False, initialized_columns = 0):

        if group_is_data == True:
            self.__columns = [0 for n in range(0, initialized_columns + 1)]
            self.__rows = [0]
            self.__data_layout = []
            self.data_storage = []

            for line in group:
                self.add_row(line, False)

            return

        ver = []
        hor = []
        for line in group:
            (ver if line.vertical() else hor).append(line)
        
        assert len(ver) >= 2
        assert len(hor) >= 2
        
        self.__columns = self.__identify_dimension(ver, Rect.xmid)
        self.__rows = self.__identify_dimension(hor, Rect.ymid)
        self.__init_data_layout()
        
        if len(self.__columns) > 2:
            missingC = self.__identify_missing_col_lines(ver)
            missingC.sort(key=sort_rect_by_position(Rect.y1, Rect.xmid, self.__columns[-1]))
            for missing in missingC:
                rightColumn = self.data_col_index(missing.xmid())
                if rightColumn > 0:
                    assert rightColumn != 0 and rightColumn != len(self.__columns)
                    leftColumn = rightColumn - 1
                    beginIndex = self.data_row_index(missing.y1())
                    endIndex = self.data_row_index(missing.y2())
                    for i in range(beginIndex, endIndex):
                        self.__data_layout[i][rightColumn] = self.__data_layout[i][leftColumn]
        
        if len(self.__rows) > 2:
            missingR = self.__identify_missing_row_lines(hor)
            missingR.sort(key=sort_rect_by_position(Rect.x1, Rect.ymid, self.__rows[-1]))
            for missing in missingR:
                topRow = self.data_row_index(missing.ymid())
                if topRow > 0:
                    assert topRow != 0 and topRow != len(self.__rows) - 1
                    bottomRow = topRow - 1
                    beginIndex = self.data_col_index(missing.x1())
                    endIndex = self.data_col_index(missing.x2())
                
                    # Do not merge into non-rectangular cells.
                    if beginIndex > 0:
                        prev = beginIndex - 1
                        if self.__data_layout[topRow][prev] == self.__data_layout[topRow][beginIndex]:
                            continue
                
                    if endIndex < len(self.__rows) - 1:
                        prev = endIndex - 1
                        if self.__data_layout[topRow][prev] == self.__data_layout[topRow][endIndex]:
                            continue
                
                    for i in range(beginIndex, endIndex):
                        self.__data_layout[bottomRow][i] = self.__data_layout[topRow][i]
        
        self.__init_data_storage()

    def debug_html(self):
        result = '<table border="1">'
        print_index = -1
        for row_index in range(0, self.rows()):
            row = self.__data_layout[row_index]
            result += "<tr>"
            for cell_index in range(0, len(row)):
                cell = row[cell_index]
                if print_index >= cell: continue
                width, height = self.cell_size(cell_index, row_index)
                colspan = (' colspan="%i"' % width) if width != 1 else ""
                rowspan = (' rowspan="%i"' % height) if height != 1 else ""
                result += "<td%s%s>" % (colspan, rowspan)
                for element in self.get_at(cell_index, row_index):
                    result += str(element).replace("<", "&lt;").replace(">", "&gt;")
                result += "</td>"
                print_index = cell
            result += "</tr>"
        result += "</table>"
        return result

    def merge_table(self, table):
        
        for row_idx in range(0, table.rows()):

            row_layout = []

            for column_idx in range(0, table.columns()):
                row_layout.append(len(self.data_storage))
                self.data_storage.append(table.get_at(column_idx, row_idx))

            self.__data_layout.append(row_layout)
            self.__rows.append(table.__rows[row_idx])

    def add_row(self, data, first_row):
        
        if first_row == True:
            self.__rows.insert(0, 0)
        else:
            self.__rows.append(0) # syntetic row

        row_layout = []

        for idx in range(0, self.columns()):
            row_layout.append(len(self.data_storage))
            self.data_storage.append(data[idx])

        if first_row == True:
            self.__data_layout.insert(0, row_layout)
        else:
            self.__data_layout.append(row_layout)

    def delete_row(self, row_idx):
        del self.__rows[row_idx]
        del self.__data_layout[row_idx]

    def get_at_pixel(self, x, y):
        row_index = self.data_row_index(y)
        col_index = self.data_col_index(x)
        return self.get_at(col_index, row_index)
    
    def set_at(self, x, y, data):
        row = self.__data_layout[y]
        data_index = row[x]
        self.data_storage[data_index] = data

    def get_at(self, x, y):
        row = self.__data_layout[y]
        data_index = row[x]
        return self.data_storage[data_index]
    
    def get_everything(self):
        result = []
        for c in self.data_storage: result += c
        return result
    
    def get_row_data(self, row_idx):
        layout = self.__data_layout[row_idx]
        layout_data = [self.data_storage[n] for n in layout]
        return layout_data
    
    def rows(self): return len(self.__rows) - 1
    def columns(self): return len(self.__columns) - 1
    def columns_data(self): return self.__columns
    
    
    def item_count(self):
        count = 0
        for cell in self.data_storage: count += len(cell)
        return count
    
    def bounds(self):
        return Rect(self.__columns[0], self.__rows[0], self.__columns[-1], self.__rows[-1])
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()
    
    def set_y1(self, y1): 
        self.__rows[0] = y1

    def set_x1(self, x1): 
        self.__columns[0] = x1

    def cell_size(self, x, y):
        row_index = self.data_row_index(y)
        col_index = self.data_col_index(x)
        return self.__cell_size(col_index, row_index)

    def set_data_index(self, x, y, data):
         self.__data_layout[y][x] = data

    def data_index(self, x, y):
        return self.__data_layout[y][x]

    def __identify_dimension(self, lines, key):
        lines.sort(key=key)
        dim = []
        for line in lines:
            value = key(line)
            if len(dim) == 0 or value - dim[-1] > 1:
                dim.append(value)
        return dim
    
    def __identify_missing_col_lines(self, vertical):
        sort_key = sort_rect_by_position(Rect.y1, Rect.xmid, self.__rows[0] - self.__rows[-1])
        vertical.sort(key=sort_key)
        missing_lines = []
        def add_missing_line(x, y1, y2):
            missing_lines.append(Rect(x, y1, x, y2))
        
        topY = self.__rows[0]
        botY = self.__rows[-1] - 0.001
        lastX = self.__columns[0]
        lastY = botY
        for line in vertical[1:]:
            if not pretty_much_equal(line.xmid(), lastX):
                if not pretty_much_equal(lastY, botY):
                    add_missing_line(lastX, lastY, botY)
                lastY = topY
            
            if not pretty_much_equal(line.y1(), lastY):
                add_missing_line(line.xmid(), lastY, line.y1())
            lastY = line.y2()
            lastX = line.xmid()
        return missing_lines
    
    def __identify_missing_row_lines(self, horizontal):
        sort_key = sort_rect_by_position(Rect.x1, Rect.ymid, self.__columns[-1] - self.__columns[0])
        horizontal.sort(key=sort_key)
        missing_lines = []
        def add_missing_line(y, x1, x2):
            missing_lines.append(Rect(x1, y, x2, y))
        
        topX = self.__columns[0]
        botX = self.__columns[-1] - 0.001
        lastX = botX
        lastY = self.__rows[0]
        for line in horizontal[1:]:
            if not pretty_much_equal(line.ymid(), lastY):
                if not pretty_much_equal(lastX, botX):
                    add_missing_line(lastY, lastX, botX)
                lastX = topX
            
            if not pretty_much_equal(line.x1(), lastX):
                add_missing_line(line.ymid(), lastX, line.x1())
            lastY = line.ymid()
            lastX = line.x2()
        return missing_lines
    
    def __init_data_layout(self):
        self.__data_layout = []
        i = 0
        row_count = len(self.__rows) - 1
        col_count = len(self.__columns) - 1
        for _ in range(0, row_count):
            row = []
            for _ in range(0, col_count):
                row.append(i)
                i += 1
            self.__data_layout.append(row)
    
    def __init_data_storage(self):
        i = 0
        last_index = 0
        for row_index in range(0, len(self.__data_layout)):
            row = self.__data_layout[row_index]
            for cell_index in range(0, len(row)):
                if row[cell_index] > last_index:
                    i += 1
                    last_index = row[cell_index]
                row[cell_index] = i
        
        self.data_storage = []
        for i in range(0, self.__data_layout[-1][-1] + 1):
            self.data_storage.append([])
    
    def data_row_index(self, y):
        return self.__dim_index(self.__rows, y)
    
    def data_col_index(self, x):
        return self.__dim_index(self.__columns, x)
    
    def __dim_index(self, array, value):
        for i in range(1, len(array)):
            ref_value = array[i]
            if ref_value > value:
                return i - 1
        return 0
        #raise Exception("improbable (%g between %g and %g)" % (value, array[0], array[-1]))
    
    def __cell_size(self, column, row):
        value = self.__data_layout[row][column]
        width = 0
        x = column
        while x >= 0 and self.__data_layout[row][x] == value:
            width += 1
            x -= 1
        
        x = column + 1
        while x < len(self.__data_layout[row]) and self.__data_layout[row][x] == value:
            width += 1
            x += 1
        
        height = 0
        y = row
        while y >= 0 and self.__data_layout[y][column] == value:
            height += 1
            y -= 1
        
        y = row + 1
        while y < len(self.__data_layout) and self.__data_layout[y][column] == value:
            height += 1
            y += 1
        
        return (width, height)


class SingleCellTable(TableBase):
    def __init__(self, data):
        self.__data = data
        if len(self.__data) > 0:
            self.rect = data[0].bounds()
            for r in self.__data:
                self.rect = self.rect.union(r.bounds())
    
    def bounds(self): return self.rect
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()
    
    def item_count(self): return len(self.__data)
    def rows(self): return 1
    def columns(self): return 1
        
    def cell_size(self, x, y):
        return (self.rect.width(), self.rect.height())

    def get_at(self, x, y):
        assert x == 0 and y == 0
        return self.__data
    
    def get_at_pixel(self, x, y):
        if self.rect.x1() <= x and self.rect.x2() >= x and self.rect.y1() <= y and self.rect.y2() >= y:
            return self.__data
        return None
    
    def get_everything(self): return self.__data
    def data_index(self, x, y): return y * self.columns() + x

class Figure(object):
    def __init__(self, table):
        self.data = table
    
    def bounds(self): return self.data.bounds()
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()

class FakeChar(object):
    def __init__(self, t):
        self.text = t
    
    def get_text(self):
        return self.text

class CharCollection(object):
    def __init__(self, iterable, rect, y_offset, page_height, fixup_y = False, char_same_y = False):
        
        self.chars = []
        self.y_offset = y_offset
        self.page_height = page_height

        if char_same_y:
            ys = {}
            for c in iterable:
                if isinstance(c, pdfminer.layout.LTChar):
                    if c.y1 in ys:
                        ys[c.y1] = ys[c.y1] + 1
                    else:
                        ys[c.y1] = 1

            top_y = None
            top_coef = 0

            for coef in ys:
                if top_y == None or top_coef < ys[coef]:
                    top_coef = ys[coef] 
                    top_y = coef

            for c in iterable:
                if isinstance(c, pdfminer.layout.LTChar):
                    if c.y1 == top_y:
                        self.chars.append(deepcopy(c))
                else:
                    self.chars.append(deepcopy(c))

        else:
            self.chars = [deepcopy(c) for c in iterable]
        
        # fixup char's y
        if fixup_y == True:
            for idx in range(0, len(self.chars)):
                if isinstance(self.chars[idx], pdfminer.layout.LTChar):
                    self.chars[idx].bbox = (self.chars[idx].bbox[0],
                            (self.y_offset + self.page_height) - self.chars[idx].bbox[1],
                            self.chars[idx].bbox[2],
                            (self.y_offset + self.page_height) - self.chars[idx].bbox[3])
                    self.chars[idx].y0 = (self.y_offset + self.page_height) - self.chars[idx].y0
                    self.chars[idx].y1 = (self.y_offset + self.page_height) - self.chars[idx].y1
                     
                
        #while len(self.chars) > 0 and len(self.chars[-1].get_text().strip()) == 0:
        #    self.chars.pop()
        
        # actual, complete bounds (modified by caller)    
        self.rect = rect

        # bounds excluding abnormally-placed characters (exponents, symbols)
        self.approx_rect = self.__approximative_bounds()
    
    def bounds(self): return self.rect
    def x1(self): return self.bounds().x1()
    def x2(self): return self.bounds().x2()
    def y1(self): return self.bounds().y1()
    def y2(self): return self.bounds().y2()
       
    def set_x1(self, x): return self.rect.set_x1(x)
    def set_y1(self, y): return self.rect.set_y1(y)
    def set_y2(self, y): return self.rect.set_y2(y)
    
    def __len__(self): return len(self.chars)

    def __approximative_bounds(self):
        if len(self.chars) == 0: return self.rect
        size = self.font_size()
        approx = None
        for c in self.chars:
            if hasattr(c, "matrix") and c.matrix[0] == size:
                rect = Rect(c.x0, c.y1, c.x1, c.y0)
                if approx == None: approx = rect
                elif approx.y1() == rect.y1(): approx = approx.union(rect)
        return approx
    
    def append(self, line):
        self.rect = self.rect.union(line.rect)
        self.approx_rect = self.approx_rect.union(line.approx_rect)
        self.chars += line.chars
        #while len(self.chars[-1].get_text().strip()) == 0:
        #    self.chars.pop()
    
    def append_char(self, c):
        aChar = self.chars[0]
        self.chars.append(FakeChar(c))
    
    def font_name(self):
        if len(self.chars):
            return get_char_font_name(self.chars[0])
        return ""

    def font_size(self):
        if len(self.chars):
            return get_char_font_size(self.chars[0])
        return 0

    def __str__(self):
        uni = "".join([c.get_text() for c in self.chars])
        if len(uni) > 0 and uni[-1] != "-" and uni[-1] != "/":
            uni += " "
        return uni
    
    def __repr__(self):
        return "<%r text=%r>" % (self.rect, str(self))

class FontStyle(object):
    def __init__(self, char):
        self.font = get_char_font_name(char)
        if isinstance(char, pdfminer.layout.LTChar):
            self.size = char.matrix[0]
            self.baseline = char.matrix[5]
        else:
            self.size = 0
            self.baseline = 0
    
    def font_is(self, name):
        return self.font.find(name) != -1
    
    def compare_baseline(self, that):
        diff = abs(that.baseline - self.baseline)
        if diff < 0.5 or diff > 8:
            return None
        
        if self.baseline < that.baseline: return ("sub", "sup")
        if self.baseline > that.baseline: return ("sup", "sub")
        assert False
