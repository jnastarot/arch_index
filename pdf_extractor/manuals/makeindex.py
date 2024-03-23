import os
import sys
import json

from parser.json2html import *

def addHeaderInject(text):
    return

def elementToText(element, ignore_su = False):
    
    text = ""

    if element["type"] == "paragraph":
        for text_el in element["elements"]: 
            
            if ignore_su \
                and "sub" in text_el["attributes"]\
                or "sup" in text_el["attributes"]:
                continue

            text += text_el["text"]
    elif element["type"] == "title":
        text += element["text"]

    return text

def elementsToText(elements, ignore_su = False):

    text = ""

    for element in elements["elements"]:
        text += elementToText(element, ignore_su)

    return text

def makeHeadTag(title, text, css_path):
    text.append(OpenTag("head"))
    text.append(OpenTag("meta", attributes={"charset": "UTF-8"}, self_closes=True))
    text.append(OpenTag("meta", attributes={"name": "viewport", "content" : "width=device-width, initial-scale=1"}, self_closes=True))
    text.append(OpenTag("link", attributes={"rel": "stylesheet", "type": "text/css", "href": css_path}, self_closes=True))
    text.append(OpenTag("title"))
    text.append(title)
    text.append(CloseTag("title"))
    addHeaderInject(text)
    text.append(CloseTag("head"))

def createFileDoc(path, path_out, index_name):
        
    with open(path, "r") as f:
        data_json = json.load(f)

    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag(" - ".join(data_json["rootname"]), text, "../../style.css")

    text.append(OpenTag("body"))
    text.append(OpenTag('div', attributes={"id": "head"}))
    text.append(OpenTag('a', attributes={"href": "../" + index_name + ".html"}))
    text.append("/home/arch-index/" + data_json["docname"].replace('\\', '/'))
    text.append(CloseTag("a"))
    text.append(" › ")
    text.append(" - ".join(data_json["rootname"]))
    text.append(CloseTag("div"))
    text.append(OpenTag('div', attributes={"id": "body"}))

    for element in data_json["elements"]:
        text.append(jsonElementHandleForHtml(element))

    text.append(CloseTag("div"))
    text.append(CloseTag('body'))

    with open(path_out, "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))


def createFullDoc(name, path, path_out, index_name):
    text = HtmlText()
    text.append(OpenTag("html"))
    makeHeadTag(name, text, "../style.css")
    
    text.append(OpenTag("body"))

    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".json"):
                with open(path + "/" + file, "r") as f:
                    data_json = json.load(f)

                    text.append(OpenTag('div', attributes={"id": "head"}))
                    text.append(OpenTag('a', attributes={"href": index_name}))
                    text.append("/home/arch-index/" + data_json["docname"].replace('\\', '/'))
                    text.append(CloseTag("a"))
                    text.append(" › ")
                    text.append(" - ".join(data_json["rootname"]))
                    text.append(CloseTag("div"))
                    text.append(OpenTag('div', attributes={"id": "body"}))

                    for element in data_json["elements"]:
                        text.append(jsonElementHandleForHtml(element))

                    text.append(CloseTag("div"))

    text.append(CloseTag('body'))

    with open(path_out, "wb") as fd:
        string_ = "<!DOCTYPE html>" + text.to_html() 
        fd.write(string_.encode("UTF-8"))
