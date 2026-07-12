from algopy import ARC4Contract, Box, Bytes, Account, UInt64
from algopy.arc4 import Struct, Address, UInt64 as Arc4UInt64, DynamicBytes
class MediatorData(Struct):
    address: Address
    bond_amount: Arc4UInt64
    did_hash: DynamicBytes
