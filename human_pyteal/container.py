from dataclasses import dataclass
from typing import Optional

import pyteal
from pyteal import TealType


@dataclass
class TealFunction:
    arguments: dict[str, TealType]
    return_type: TealType


@dataclass
class TransformResult:
    pyteal_program: str
    formatted_pyteal_program: Optional[str]
    pyteal_ast: Optional[pyteal.Expr]
    teal_program: Optional[str]
