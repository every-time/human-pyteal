from _ast import Call, Name, FunctionDef, Constant
from ast import NodeVisitor
from typing import Optional

from pyteal import TealType


class PyTealVisitor(NodeVisitor):
    def __init__(self):
        self.target_function_calls: set[str] = set()
        self.function_argument_types: dict[str, dict[str, TealType]] = {}
        self.function_return_types: dict[str, TealType] = {}

    def visit_FunctionDef(self, node: FunctionDef):
        if node.name in self.target_function_calls:
            return_type: Optional[TealType] = None

            if isinstance(node.returns, Constant) and node.returns.value is None:
                return_type = TealType.none
            elif isinstance(node.returns, Name):
                if node.returns.id == 'int' or node.returns.id == 'bool':
                    return_type = TealType.uint64
                elif node.returns.id == 'str':
                    return_type = TealType.bytes

            if not return_type:
                raise ValueError('Must specify a valid return type for ' + node.name)

            self.function_return_types[node.name] = return_type

            if node.args.args or node.args.vararg or node.args.kwonlyargs or node.args.kw_defaults or node.args.kwarg or node.args.defaults:
                raise NotImplementedError('Only positional argument are allowed for ' + node.name)

            self.function_argument_types[node.name] = {}

            for arg in node.args.posonlyargs:
                arg_type: Optional[TealType] = None

                # TODO: Consolidate the below code with the above.
                if isinstance(arg.annotation, Name):
                    if arg.annotation.id == 'int' or arg.annotation.id == 'bool':
                        arg_type = TealType.uint64
                    elif arg.annotation.id == 'str':
                        arg_type = TealType.bytes

                if not arg_type:
                    raise ValueError(f'Must specify a valid argument type on "{arg.arg}" for {node.name}')

                self.function_argument_types[node.name][arg.arg] = arg_type

            self.generic_visit(node)

    def visit_Call(self, node: Call):
        if isinstance(node.func, Name):
            self.target_function_calls.add(node.func.id)
