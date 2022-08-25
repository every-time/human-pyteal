from _ast import Assign
from dataclasses import dataclass
from typing import Optional

import pyteal
from pyteal import ScratchVar


@dataclass
class Variable:
    scratch_var: ScratchVar
    assign_node: Assign


@dataclass
class TransformResult:
    pyteal_program: str
    formatted_pyteal_program: Optional[str]
    pyteal_ast: Optional[pyteal.Expr]
    teal_program: Optional[str]
