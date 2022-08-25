# human-pyteal: [WIP] PyTeal for humans!

- [ ] PyTeal objects and functions (`Txn`, `App`, `Balance`, `Sha256`, etc.)
- [ ] ABI support
- [ ] Tests
- [ ] Subscripting (`'alogrand'[4]` -> `Extract(Bytes("algorand"), Int(4), Int(1))`, etc.)
- [ ] For loops
- [ ] Importing functions from other modules

## Example usage

```py
from pyteal import Mode

import human_pyteal


def add_str(x: str, y: str, /) -> str:
    return x + y


def add_int(x: int, y: int, /) -> int:
    return x + y


def get_program() -> int:
    a = 1
    b = add_int(a, 1)

    c = 'hello, '
    d = 'world!' if b == 2 or b == 3 else 'space!' if a == 1 and b == 4 else 'galaxy!'
    add_str(c, d)

    i = 0
    while i < b + 5:
        print('while loop!')

        if i == 1:
            if b == 2:
                print('nested...')
            elif b == 3:
                print('...if statement!')

            raise 'i == 1'
        elif i == 2:
            assert len(c) > 5, 'len(c) <= 5'
            return False
        elif i == 3:
            break

        i += 1

    return True


transform_result = human_pyteal.transform(get_program, mode=Mode.Application, version=5)
print(transform_result.formatted_pyteal_program)
```

->

```py
from pyteal import *


def get_program():
    a = ScratchVar(TealType.uint64)
    b = ScratchVar(TealType.uint64)
    c = ScratchVar(TealType.bytes)
    d = ScratchVar(TealType.bytes)
    i = ScratchVar(TealType.uint64)
    return Seq(
        a.store(Int(1)),
        b.store(add_int(a.load(), Int(1))),
        c.store(Bytes("hello, ")),
        d.store(
            If(Or(b.load() == Int(2), b.load() == Int(3)))
            .Then(Bytes("world!"))
            .ElseIf(And(a.load() == Int(1), b.load() == Int(4)))
            .Then(Bytes("space!"))
            .Else(Bytes("galaxy!"))
        ),
        Pop(add_str(c.load(), d.load())),
        i.store(Int(0)),
        While(i.load() < b.load() + Int(5)).Do(
            Log(Bytes("while loop!")),
            If(i.load() == Int(1))
            .Then(
                If(b.load() == Int(2))
                .Then(Log(Bytes("nested...")))
                .ElseIf(b.load() == Int(3))
                .Then(Log(Bytes("...if statement!"))),
                Comment("i == 1", Err()),
            )
            .ElseIf(i.load() == Int(2))
            .Then(Assert(Len(c.load()) > Int(5), comment="len(c) <= 5"), Return(Int(0)))
            .ElseIf(i.load() == Int(3))
            .Then(Break()),
            i.store(i.load() + Int(1)),
        ),
        Return(Int(1)),
    )


@Subroutine(TealType.uint64)
def add_int(x, y, /):
    return Seq(Return(x + y))


@Subroutine(TealType.bytes)
def add_str(x, y, /):
    return Seq(Return(Concat(x, y)))
```
