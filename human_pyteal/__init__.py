import ast
import inspect
from _ast import Module
from typing import Optional

import black
import pyteal
from black import FileMode

from human_pyteal import utility
from human_pyteal.container import TransformResult
from human_pyteal.pyteal_transformer import PyTealTransformer
from human_pyteal.pyteal_visitor import PyTealVisitor


def transform(target_function: callable, *args, **kwargs) -> TransformResult:
    sorted_functions: list[tuple[str, Module]] = []

    for function_name, function in inspect.getmembers(inspect.getmodule(target_function), inspect.isfunction):
        item = (function_name, ast.parse(inspect.getsource(function)))

        if function == target_function:
            sorted_functions.insert(0, item)
        else:
            sorted_functions.append(item)

    visitor = PyTealVisitor()
    visitor.target_function_calls.add(target_function.__name__)

    for function_name, tree in sorted_functions:
        visitor.visit(tree)

    module = ast.parse('from pyteal import *')
    module.body += [tree for function_name, tree in sorted_functions if function_name in visitor.target_function_calls]
    pyteal_program = ast.unparse(ast.fix_missing_locations(PyTealTransformer(target_function.__name__, visitor.teal_functions).visit(module)))
    teal_program: Optional[str] = None

    try:
        formatted_pyteal_program: Optional[str] = black.format_str(pyteal_program, mode=FileMode())
    except Exception as e:
        utility.print_action_exception(e, 'PyTeal formatting')
        formatted_pyteal_program = None

    try:
        pyteal_env = {}
        exec(pyteal_program, pyteal_env)
        pyteal_ast: Optional[pyteal.Expr] = pyteal_env[target_function.__name__]()
    except Exception as e:
        utility.print_action_exception(e, 'PyTeal parsing')
        pyteal_ast = None

    if pyteal_ast:
        try:
            teal_program = pyteal.compileTeal(pyteal_ast, *args, **kwargs)
        except Exception as e:
            utility.print_action_exception(e, 'PyTeal compilation')

    return TransformResult(pyteal_program, formatted_pyteal_program, pyteal_ast, teal_program)
