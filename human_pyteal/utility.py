import sys
import traceback
from _ast import If, IfExp, Call, Attribute, AST, Name, Load, Constant
from typing import Optional

from pyteal import TealType


def annotation_teal_type(node: Optional[AST]) -> Optional[TealType]:
    teal_type: Optional[TealType] = None

    if isinstance(node, Constant) and node.value is None:
        teal_type = TealType.none
    elif isinstance(node, Name):
        if node.id == 'int' or node.id == 'bool':
            teal_type = TealType.uint64
        elif node.id == 'str':
            teal_type = TealType.bytes

    return teal_type


def bytes_value(item: Optional[AST]) -> Optional[AST]:
    if item and isinstance(item, Call) and isinstance(item.func, Name) and item.func.id == 'Bytes':
        return item.args[0]

    return None


def create_name(id_: str) -> Name:
    return Name(id_, ctx=Load())


def _ensure_list(item: AST | list[AST]) -> list[AST]:
    return item if isinstance(item, list) else [item]


def transform_if(node: If | IfExp, *, transformed_node: Optional[Call] = None) -> Call:
    func = create_name('If') if not transformed_node else Attribute(transformed_node, attr='ElseIf')
    if_node = Call(func, args=[node.test], keywords=[])
    if_node = Attribute(if_node, attr='Then')
    if_node = Call(if_node, args=[*_ensure_list(node.body)], keywords=[])
    else_args: list[AST] = []

    for item in _ensure_list(node.orelse):
        if isinstance(item, If | IfExp):
            if_node = transform_if(item, transformed_node=if_node)
        else:
            else_args.append(item)

    if else_args:
        if_node = Attribute(if_node, attr='Else')
        if_node = Call(if_node, args=[*else_args], keywords=[])

    return if_node


def print_action_exception(e: Exception, action: str):
    formatted = traceback.format_exception(e)

    if formatted[0] == 'Traceback (most recent call last):\n':
        formatted[0] = f'Traceback during {action} (most recent call last):\n'

    print(''.join(formatted), file=sys.stderr)
