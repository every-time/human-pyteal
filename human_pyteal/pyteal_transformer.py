import ast
import warnings
from _ast import Constant, Call, Name, Return, FunctionDef, Assert, Attribute, While, Continue, Break, BoolOp, And, Or, UnaryOp, Not, Raise, If, Pass, IfExp, BinOp, Add, Expr, Assign, AST, Load, AugAssign, Compare
from ast import NodeTransformer
from typing import Optional, Any

import pyteal
from pyteal import TealType, ScratchVar, SubroutineFnWrapper

from human_pyteal import utility
from human_pyteal.container import TealFunction


class PyTealTransformer(NodeTransformer):
    def __init__(self, target_function_name: str, teal_functions: dict[str, TealFunction]):
        self._target_function_name = target_function_name
        self._teal_functions = teal_functions
        self._variables: dict[str, ScratchVar] = {}
        self._assign_nodes: list[Assign] = []
        self._current_function_name: Optional[str] = None
        self._locals_: dict[str, Any] = {}

    def _teal_type(self, node: AST):
        teal_type: Optional[TealType] = None

        if isinstance(node, Name):
            if node.id in self._variables:
                teal_type = self._variables[node.id].type
            elif node.id in self._teal_functions[self._current_function_name].arguments:
                teal_type = self._teal_functions[self._current_function_name].arguments[node.id]
        elif isinstance(node, Call) and isinstance(node.func, Name) and node.func.id in self._teal_functions:
            teal_type = self._teal_functions[node.func.id].return_type

        if not teal_type:
            try:
                self._locals_.update(self._variables)
                teal_type = eval(ast.unparse(node), pyteal.__dict__, self._locals_).type_of()
            except Exception as e:
                warnings.warn(f'Failed to determine the Teal type for {ast.unparse(node)}: {e}')

        return teal_type

    def visit_FunctionDef(self, node: FunctionDef):
        for arg in node.args.posonlyargs:
            arg.annotation = None

        if node.name != self._target_function_name:
            decorator_node = Attribute(utility.create_name('TealType'), attr=self._teal_functions[node.name].return_type.name)
            node.decorator_list.append(Call(utility.create_name('Subroutine'), args=[decorator_node], keywords=[]))

        self._variables.clear()
        self._assign_nodes.clear()
        self._current_function_name = node.name

        self._locals_.clear()
        self._locals_ = {k: SubroutineFnWrapper(lambda: pyteal.Return(), v.return_type) for k, v in self._teal_functions.items()}
        self._locals_.update({k: pyteal.SubroutineFnWrapper(lambda: pyteal.Return(), v)() for k, v in self._teal_functions[self._current_function_name].arguments.items()})

        node.returns = None
        self.generic_visit(node)
        body: list[AST] = self._assign_nodes
        node.body = body + [Return(Call(utility.create_name('Seq'), args=[*node.body], keywords=[]))]
        return node

    def visit_Expr(self, node: Expr):
        self.generic_visit(node)

        if isinstance(node.value, Call) and isinstance(node.value.func, Name):
            if node.value.func.id == 'Log' or node.value.func.id in self._teal_functions and self._teal_functions[node.value.func.id].return_type == TealType.none:
                return node

        return Call(utility.create_name('Pop'), args=[node], keywords=[])

    def visit_Name(self, node: Name):
        self.generic_visit(node)

        if isinstance(node.ctx, Load) and node.id in self._variables:
            name_node = Attribute(node, attr='load')
            return Call(name_node, args=[], keywords=[])

        return node

    def visit_Assign(self, node: Assign):
        self.generic_visit(node)
        teal_type = self._teal_type(node.value)
        seq_nodes: list[Assign | Call] = []

        for target in node.targets:
            if not teal_type or not isinstance(target, Name):
                assign_node = Assign(targets=[target], value=node.value)

                if isinstance(target, Name) and target.id in self._variables:
                    seq_nodes.append(assign_node)
                else:
                    self._assign_nodes.append(assign_node)

                continue

            if target.id not in self._variables:
                assign_node = Attribute(utility.create_name('TealType'), attr=teal_type.name)
                assign_node = Call(utility.create_name('ScratchVar'), args=[assign_node], keywords=[])
                self._assign_nodes.append(Assign(targets=[target], value=assign_node))
                self._variables[target.id] = ScratchVar(teal_type)

            store_call = Attribute(target, attr='store')
            seq_nodes.append(Call(store_call, args=[node.value], keywords=[]))

        return seq_nodes

    def visit_AugAssign(self, node: AugAssign):
        if isinstance(node.target, Name):
            aug_assign_node = BinOp(left=utility.create_name(node.target.id), right=node.value, op=node.op)
            aug_assign_node: AST = Assign(targets=[node.target], value=aug_assign_node)
            return self.visit(aug_assign_node)

        return node

    def visit_Call(self, node: Call):
        self.generic_visit(node)

        if isinstance(node.func, Name):
            if node.func.id == 'print':
                node.func.id = 'Log'
            elif node.func.id == 'len':
                node.func.id = 'Len'

        return node

    def visit_If(self, node: If):
        if_node = utility.transform_if(node)
        return self.generic_visit(if_node)

    def visit_IfExp(self, node: IfExp):
        if_exp_node = utility.transform_if(node)
        return self.generic_visit(if_exp_node)

    def visit_While(self, node: While):
        self.generic_visit(node)
        while_node = Call(utility.create_name('While'), args=[node.test], keywords=[])
        while_node = Attribute(while_node, attr='Do')
        return Call(while_node, args=[*node.body], keywords=[])

    def visit_Continue(self, node: Continue):
        return Call(utility.create_name('Continue'), args=[], keywords=[])

    def visit_Break(self, node: Break):
        return Call(utility.create_name('Break'), args=[], keywords=[])

    def visit_Pass(self, node: Pass):
        return Call(utility.create_name('Seq'), args=[], keywords=[])

    def visit_Constant(self, node: Constant):
        if isinstance(node.value, int):
            if node.value is True:
                node.value = 1
            elif node.value is False:
                node.value = 0

            return Call(utility.create_name('Int'), args=[node], keywords=[])

        if isinstance(node.value, str):
            return Call(utility.create_name('Bytes'), args=[node], keywords=[])

        return node

    def visit_UnaryOp(self, node: UnaryOp):
        self.generic_visit(node)

        if isinstance(node.op, Not):
            return Call(utility.create_name('Not'), args=[node.operand], keywords=[])

        return node

    def visit_BoolOp(self, node: BoolOp):
        self.generic_visit(node)

        if isinstance(node.op, And):
            return Call(utility.create_name('And'), args=[*node.values], keywords=[])

        if isinstance(node.op, Or):
            return Call(utility.create_name('Or'), args=[*node.values], keywords=[])

        return node

    def visit_BinOp(self, node: BinOp):
        self.generic_visit(node)

        if isinstance(node.op, Add):
            if isinstance(node.left, Call) and isinstance(node.left.func, Name) and node.left.func.id == 'Concat':
                return Call(utility.create_name('Concat'), args=[*node.left.args, node.right], keywords=[])

            if self._teal_type(node.left) == TealType.bytes:
                return Call(utility.create_name('Concat'), args=[node.left, node.right], keywords=[])

        return node

    def visit_Compare(self, node: Compare):
        self.generic_visit(node)

        if len(node.comparators) == 1:
            return node

        compare_node = Call(utility.create_name('And'), args=[], keywords=[])

        for i, op in enumerate(node.ops):
            left = node.left if i == 0 else node.comparators[i - 1]
            compare_node.args.append(Compare(left=left, ops=[op], comparators=[node.comparators[i]]))

        return compare_node

    def visit_Raise(self, node: Raise):
        self.generic_visit(node)
        raise_node = Call(utility.create_name('Err'), args=[], keywords=[])
        comment = utility.bytes_value(node.exc)

        if comment:
            return Call(utility.create_name('Comment'), args=[comment, raise_node], keywords=[])

        return raise_node

    def visit_Assert(self, node: Assert):
        self.generic_visit(node)
        assert_node = Call(utility.create_name('Assert'), args=[node.test], keywords=[])
        comment = utility.bytes_value(node.msg)

        if comment:
            assert_node.keywords.append(ast.keyword(arg='comment', value=comment))

        return assert_node

    def visit_Return(self, node: Return):
        self.generic_visit(node)
        return Call(utility.create_name('Return'), args=[node.value] if node.value else [], keywords=[])
