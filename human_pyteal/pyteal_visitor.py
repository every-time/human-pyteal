from _ast import Call, Name, FunctionDef
from ast import NodeVisitor

from pyteal import TealType

from human_pyteal import utility
from human_pyteal.container import TealFunction


class PyTealVisitor(NodeVisitor):
    def __init__(self):
        self.target_function_calls: set[str] = set()
        self.teal_functions: dict[str, TealFunction] = {}

    def visit_FunctionDef(self, node: FunctionDef):
        if node.name in self.target_function_calls:
            return_type = utility.annotation_teal_type(node.returns)

            if not return_type:
                raise ValueError('Must specify a valid return type for ' + node.name)

            if node.args.args or node.args.vararg or node.args.kwonlyargs or node.args.kw_defaults or node.args.kwarg or node.args.defaults:
                raise NotImplementedError('Only positional arguments are allowed for ' + node.name)

            arguments: dict[str, TealType] = {}

            for argument in node.args.posonlyargs:
                argument_type = utility.annotation_teal_type(argument.annotation)

                if not argument_type or argument_type == TealType.none:
                    raise ValueError(f'Must specify a valid argument type on "{argument.arg}" for {node.name}')

                arguments[argument.arg] = argument_type

            self.teal_functions[node.name] = TealFunction(arguments, return_type)
            self.generic_visit(node)

    def visit_Call(self, node: Call):
        if isinstance(node.func, Name):
            self.target_function_calls.add(node.func.id)
