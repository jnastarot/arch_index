#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
sys.path.append('./parser')
sys.path.append('./manuals')

import json
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.layout import LAParams
from pdfminer.converter import PDFPageAggregator

from x86_manual import x86ManParser
from mips_manual import mipsManParser
from nanomips_manual import nanomipsISAManParser
from m68k_manual import m68kManParser
from avr8bit_manual import avr8ManParser
from avr32bit_manual import avr32ManParser

def processPdfFile(type, pdf_path, out_path, doc_name):
    print("Processing ", pdf_path)
    fd = open(pdf_path, 'rb')
    parser = PDFParser(fd)
    document = PDFDocument(parser)
    if not document.is_extractable:
        print("Document not extractable.")
        return 1

    params = LAParams(char_margin=1)
    resMan = PDFResourceManager(caching=True)
    device = PDFPageAggregator(resMan, laparams=params)
    interpreter = PDFPageInterpreter(resMan, device)

    if type == "intel":
        parser = x86ManParser(out_path, doc_name, params)
    elif type == "mips" or type == "nanomips":
        parser = mipsManParser(out_path, doc_name, params, type)
    elif type == "nanomips_isa":
        parser = nanomipsISAManParser(out_path, doc_name, params, type)
    elif type == "m68k":
        parser = m68kManParser(out_path, doc_name, params)
    elif type == "avr8":
        parser = avr8ManParser(out_path, doc_name, params)
    elif type == "avr32":
        parser = avr32ManParser(out_path, doc_name, params)

    i = 1
    for page in PDFPage.get_pages(fd, set(), caching=True, check_extractable=True):
        print("Processing page %i" % i)
        if i >= 0:#170:#i >= 102 and i <= 103: #310: 
            # 92:
            interpreter.process_page(page)
            page1 = device.get_result()
            parser.processPage(page1)
        i += 1

    parser.flush()
    fd.close()
    
    print("Conversion result: %i/%i" % (parser.success, parser.success + parser.fail))

def main(argv):

    with open(argv[1], "r") as f:
        parser_config = json.load(f)

    for task in parser_config["tasks"]:
        processPdfFile(
            task["type"],
            task["pdfpath"],
            task["outpath"],
            task["docname"]
        )

if __name__ == "__main__":
    result = main(sys.argv)
    sys.exit(result)