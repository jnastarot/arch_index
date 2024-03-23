#!/bin/env python
# -*- coding: UTF-8 -*-

# OpenTag and CloseTag are NOT HARDENED against HTML injection!
# Do not use them for input that you cannot perfectly predict.

import re
import sys
import json
from parser.htmltext import *

def sortDescriptionByTitle(root_json):
        
    json_title_stack = []

    element_idx = 0
    while element_idx < len(root_json["elements"]):

        if root_json["elements"][element_idx]["type"] == "title":

            new_level = root_json["elements"][element_idx]["level"] 

            if len(json_title_stack) == 0:
                json_title_stack.append(root_json["elements"][element_idx])
            elif json_title_stack[-1]["level"] >= new_level:
                while len(json_title_stack) and json_title_stack[-1]["level"] >= new_level:
                    json_title_stack.pop()
                json_title_stack.append(root_json["elements"][element_idx])    
            else:
                json_title_stack.append(root_json["elements"][element_idx])
            
            element_idx += 1
        else:
            if len(json_title_stack):
                json_title_stack[-1]["elements"].append(root_json["elements"][element_idx])
                del root_json["elements"][element_idx]
            else:
                element_idx += 1

def jsonElementHandleForHtml(json_element):

    if json_element["type"] == "title":
        
        result = HtmlText()

        text = HtmlText()
        open = OpenTag("p")
        open.tag = "h" + str(json_element["level"])
        text.append(open)
        text.append(json_element["text"])
        text.autoclose()

        result.append(text)

        for element in json_element["elements"]:
            result.append(jsonElementHandleForHtml(element))

        return result
    
    elif json_element["type"] == "table":
        
        result = HtmlText()
        result.append(OpenTag("table"))
        
        for row in json_element["rows"]:
            result.append(OpenTag("tr"))
            
            for column in row["columns"]:
                is_th = "th" in column["attributes"]

                result.append(OpenTag("th") if is_th else OpenTag("td"))
                
                for element in column["elements"]:
                    result.append(jsonElementHandleForHtml(element))

                result.append(CloseTag("th") if is_th else CloseTag("td"))

            result.append(CloseTag("tr"))
        
        result.append(CloseTag("table"))

        return result
    
    elif json_element["type"] == "list":
        result = HtmlText()
        result.append(OpenTag("ul"))
    
        for item in json_element["elements"]:
            result.append(OpenTag("li"))
            result.append(jsonElementHandleForHtml(item))
            result.append(CloseTag("li"))
    
        result.append(CloseTag("ul"))

        return result
    
    elif json_element["type"] == "paragraph":
        result = HtmlText()
    
        if "code" in json_element["attributes"]:
            result.append(OpenTag("pre", True))
        else:
            result.append(OpenTag("p"))

        for element in json_element["elements"]:
            result.append(jsonElementHandleForHtml(element))

        if "code" in json_element["attributes"]:
            result.append(CloseTag("pre"))
        else:
            result.append(CloseTag("p"))

        return result

    elif json_element["type"] == "text":

        result = HtmlText()

        if "italic" in json_element["attributes"]:
            result.append(OpenTag("em"))           
        if "strong" in json_element["attributes"]:
            result.append(OpenTag("strong"))       
        if "sub" in json_element["attributes"]:
            result.append(OpenTag("sub"))       
        if "sup" in json_element["attributes"]:
            result.append(OpenTag("sup"))      

        result.append(json_element["text"])

        if "sup" in json_element["attributes"]:
            result.append(CloseTag("sup"))   
        if "sub" in json_element["attributes"]:
            result.append(CloseTag("sub"))       
        if "strong" in json_element["attributes"]:
            result.append(CloseTag("strong"))       
        if "italic" in json_element["attributes"]:
            result.append(CloseTag("em"))           
            
        return result
    
    return

def genHtmlDescription(json_elements):

    text = HtmlText()
    text.append(OpenTag("html"))
    text.append(OpenTag("head"))
    text.append(OpenTag("meta", attributes={"charset": "UTF-8"}, self_closes=True))
    text.append(OpenTag("meta", attributes={"name": "viewport", "content" : "width=device-width, initial-scale=1"}, self_closes=True))
    text.append(OpenTag("link", attributes={"rel": "stylesheet", "type": "text/css", "href": "../style.css"}, self_closes=True))
    text.append(OpenTag("script", attributes={"src": "..\\script.js"}))
    text.append(CloseTag("script"))
    text.append(OpenTag("title"))
    text.append(" - ".join(json_elements["rootname"]))
    text.append(CloseTag("title"))
    text.append(CloseTag("head"))
    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "index.html"}))
    text.append(json_elements["docname"])
    text.append(CloseTag("a"))
    text.append(" › ")
    text.append(" - ".join(json_elements["rootname"]))
    text.append(CloseTag("div"))
    text.append(OpenTag('div', attributes={"id": "body"}))

    for element in json_elements["elements"]:
        text.append(jsonElementHandleForHtml(element))

    return text

if __name__ == "__main__":

    with open (sys.argv[0], "r") as f:
        root_json = json.loads(f.read())
    
    with open(sys.argv[1], "wb") as fd:
        string_ = "<!DOCTYPE html>" + genHtmlDescription(root_json).to_html() 
        fd.write(string_.encode("UTF-8"))
    
    sys.exit(0)

