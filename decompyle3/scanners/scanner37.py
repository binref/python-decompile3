#  Copyright (c) 2016-2019, 2021-2022 by Rocky Bernstein
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Python 3.7 bytecode decompiler scanner.

Does some additional massaging of xdis-disassembled instructions to
make things easier for decompilation.

This sets up opcodes Python's 3.7 and calls a generalized
scanner routine for Python 3.
"""

from typing import Tuple

from decompyle3.scanners.scanner37base import Scanner37Base

# bytecode verification, verify(), uses JUMP_OPs from here
from xdis.opcodes import opcode_37 as opc

# bytecode verification, verify(), uses JUMP_OPS from here
JUMP_OPs = opc.JUMP_OPS


class Scanner37(Scanner37Base):
    def __init__(self, show_asm=None, debug="", is_pypy=False):
        Scanner37Base.__init__(self, (3, 7), show_asm, debug, is_pypy)
        self.debug = debug
        return

    pass

    def ingest(
        self, bytecode, classname=None, code_objects={}, show_asm=None
    ) -> Tuple[list, dict]:
        """
        Create "tokens" the bytecode of an Python code object. Largely these
        are the opcode name, but in some cases that has been modified to make parsing
        easier.
        returning a list of uncompyle6 Token's.

        Some transformations are made to assist the deparsing grammar:
           -  various types of LOAD_CONST's are categorized in terms of what they load
           -  COME_FROM instructions are added to assist parsing control structures
           -  operands with stack argument counts or flag masks are appended to the opcode name, e.g.:
              *  BUILD_LIST, BUILD_SET
              *  MAKE_FUNCTION and FUNCTION_CALLS append the number of positional arguments
           -  EXTENDED_ARGS instructions are removed

        Also, when we encounter certain tokens, we add them to a set which will cause custom
        grammar rules. Specifically, variable arg tokens like MAKE_FUNCTION or BUILD_LIST
        cause specific rules for the specific number of arguments they take.
        """
        tokens, customize = Scanner37Base.ingest(
            self, bytecode, classname, code_objects, show_asm
        )
        new_tokens = []
        for i, t in enumerate(tokens):
            # things that smash new_tokens like BUILD_LIST have to come first.
            if t.op in (
                self.opc.BUILD_CONST_KEY_MAP,
                self.opc.BUILD_LIST,
                self.opc.BUILD_SET,
            ):
                collection_type = (
                    "DICT"
                    if t.kind.startswith("BUILD_CONST_KEY_MAP")
                    else t.kind.split("_")[1]
                )
                new_tokens = self.bound_collection(
                    tokens, new_tokens, t, i, f"CONST_{collection_type}"
                )
                continue

            # The lowest bit of flags indicates whether the
            # var-keyword argument is placed at the top of the stack
            if t.op == self.opc.CALL_FUNCTION_EX and t.attr & 1:
                t.kind = "CALL_FUNCTION_EX_KW"
                pass
            elif t.op == self.opc.BUILD_STRING:
                t.kind = "BUILD_STRING_%s" % t.attr
            elif t.op == self.opc.CALL_FUNCTION_KW:
                t.kind = "CALL_FUNCTION_KW_%s" % t.attr
            elif t.op == self.opc.FORMAT_VALUE:
                if t.attr & 0x4:
                    t.kind = "FORMAT_VALUE_ATTR"
                    pass
            elif t.op == self.opc.BUILD_MAP_UNPACK_WITH_CALL:
                t.kind = "BUILD_MAP_UNPACK_WITH_CALL_%d" % t.attr
            elif (not self.is_pypy) and t.op == self.opc.BUILD_TUPLE_UNPACK_WITH_CALL:
                t.kind = "BUILD_TUPLE_UNPACK_WITH_CALL_%d" % t.attr
            new_tokens.append(t)

        return new_tokens, customize


if __name__ == "__main__":
    from xdis.version_info import PYTHON_VERSION_TRIPLE, version_tuple_to_str

    if PYTHON_VERSION_TRIPLE[:2] == (3, 7):
        import inspect

        co = inspect.currentframe().f_code  # type: ignore
        tokens, customize = Scanner37().ingest(co)
        for t in tokens:
            print(t.format())
        pass
    else:
        print(f"Need to be Python 3.7 to demo; I am version {version_tuple_to_str()}.")
