import argparse
import sys

from arm_read_encodeindex import *
from arm_read_instruction import *

from arm_process_fulldefination import *

from arm_print_encodeindex import *
from arm_print_instruction import *



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verbose', '-v', help='Use verbose output',
                        action = 'count', default=0)
    parser.add_argument('--altslicesyntax', help='Convert to alternative slice syntax',
                        action='store_true', default=False)
    parser.add_argument('--sail_asts', help='Output Sail file for AST clauses',
                        metavar='FILE', default=None)
    parser.add_argument('--demangle', help='Demangle instruction ASL',
                        action='store_true', default=False)
    parser.add_argument('--output', '-o', help='Basename for output files',
                        metavar='FILE', default='arch')
    parser.add_argument('dir', metavar='<dir>',  nargs='+',
                        help='input directories')
    parser.add_argument('--filter',  help='Optional input json file to filter definitions',
                        metavar='FILE', default=[], nargs='*')
    parser.add_argument('--arch', help='Optional list of architecture states to extract',
                        choices=["AArch32", "AArch64"], default=[], action='append')
    parser.add_argument('--include', help='Regex to select instructions by name',
                        metavar='REGEX', default=None)
    parser.add_argument('--exclude', help='Regex to exclude instructions by name',
                        metavar='REGEX', default=None)
    #args = parser.parse_args()

    decoder_files = [ 
            'encodingindex.xml', 
            't32_encindex.xml', 
            'a32_encindex.xml' 
        ]
    
    instructions = {}

    definitions = [
        processArmFullDefination("D:\\projects\\archindex\\data\\onebigfile_a32_t32.xml"),
        processArmFullDefination("D:\\projects\\archindex\\data\\onebigfile_a64.xml") 
    ]

    breakpoint()
    

    with open("encodeindex_decoder.h", "w") as ofile:
        printDecodeTree(ofile, full_defination)
    with open("instruction_sections_decoder.h", "w") as ofile:
        fields_association_var = printInstructionVariableDecode(ofile, full_defination)
    with open("instruction_fields_decoder.h", "w") as ofile:
        fields_association_dec = printInstructionFieldTableDecode(ofile, full_defination)
    with open("instruction_asm_template.h", "w") as ofile:
        printInstructionAsmTemplate(ofile, full_defination)

    with open("features.h", "w") as ofile:
        printFeatureFunctions(ofile, full_defination)
    with open("mnemonic_dec.h", "w") as ofile:
        (encode_list, instruction_list) = printInstructionMnemonicDecode(ofile, full_defination)
    with open("class_dec.h", "w") as ofile:
        classes_list = printInstructionClassDecode(ofile, full_defination)
    with open("encoding_forms_list.h", "w") as ofile:
         printInstructionEncodingForms(ofile, full_defination)
    with open("instructions_list.h", "w") as ofile:
         printInstructionList(ofile, full_defination)
    with open("decoder_fields_list.h", "w") as ofile:
         printInstructionDecoderFields(ofile, fields_association_dec, fields_association_var)

if __name__ == "__main__":
    sys.exit(main())