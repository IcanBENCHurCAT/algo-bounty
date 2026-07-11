import typing
from algopy import ARC4Contract, Box, Bytes, Account, UInt64, arc4

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
        self.mediator_data.value = MediatorData(
            address=arc4.Address(mediator),
            bond_amount=arc4.UInt64(0),
            is_bonded=arc4.UInt64(0),
            did_hash=arc4.StaticArray[arc4.Byte, typing.Literal[32]].from_bytes(Bytes(b"\x00" * 32))
        )
