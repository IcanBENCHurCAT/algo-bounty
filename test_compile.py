import typing
from algopy import ARC4Contract, arc4, Account, UInt64, String, Bytes, Box

class MediatorData(arc4.Struct):
    address: arc4.Address
    bond_amount: arc4.UInt64
    is_bonded: arc4.UInt64
    did_hash: arc4.StaticArray[arc4.Byte, typing.Literal[32]]

class TestContract(ARC4Contract):
    def __init__(self) -> None:
        self.mediator_data = Box(MediatorData, key="mediator_data")

    @arc4.abimethod
    def test(self, mediator: Account) -> None:
        pass
