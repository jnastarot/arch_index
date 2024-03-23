import argparse
import sys
import json

import mips_extract_instructions

def main():
    
    encoder_data = {}

    with open("data/mips/mips_encoder_data.json") as f:
        encoder_data = json.load(f)

    instructions = mips_extract_instructions.extractArchitecture(encoder_data)

    return


if __name__ == "__main__":
    sys.exit(main())