import sys
sys.path.append('./parser')
sys.path.append('./manuals')

import avr_makeindex
import mips_makeindex
import x86_makeindex
import m68k_makeindex



avr_makeindex.makeAllFullDocs()
avr_makeindex.makeAllIndexes()
mips_makeindex.makeAllFullDocs()
mips_makeindex.makeAllIndexes()
x86_makeindex.makeAllFullDocs()
x86_makeindex.makeAllIndexes()
#m68k_makeindex.makeAllFullDocs()
#m68k_makeindex.makeAllIndexes()


