# FlashHacker

FlashHacker is an ActionScript Bytecode instrumentation framework. The RABCDasm tool is used for disassembling and assembling of ActionScript Bytecode. The tool uses Bytecode disassembly to inject various instrumentation instructions.

This tool is very useful when you work with malicious Flash files.

The whole concept was introduced in my previous presentation at ShmooCon 2012
   http://www.shmoocon.org/2012/presentations/Jeong_Wook_Oh_AVM%20Inception%20-%20ShmooCon2012.pdf

## Prerequisite
* PySide: https://pypi.python.org/pypi/PySide (pip install -U PySide on Windows)
* Graphviz 2.x: included in the repo\
* RABCDasm binaries: https://github.com/CyberShadow/RABCDAsm/releases

After installing prerequisites, run python FlashHacker.py and it will ask path for RABCDasm package. 

## WARNING
The tool is still in very early age of development. You might get some errors, missing files, etc. Please open an issue, so that I can track and fix them.
