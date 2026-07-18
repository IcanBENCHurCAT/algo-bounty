import typing
from algopy import (
    Account,
    ARC4Contract,
    Box,
    Bytes,
    Global,
    Txn,
    UInt64,
    arc4,
    gtxn,
    itxn,
    op,
    log,
    TemplateVar,
    TransactionType,
    OnCompleteAction,
)

# State machine constants (standard Python literals)
OPEN = 0
CLAIMED = 1
SUBMITTED = 2
REJECTED = 3
DISPUTED = 4
CLOSED = 5
DISPUTED_TIMEOUT = 6
CLAIM_EXPIRED = 7

PAYOUT = b"PAYOUT"
REFUND = b"REFUND"
SPLIT = b"SPLIT"

MAX_REJECTIONS = 3
MAX_PROOF_BYTES = 2048
MAX_URL_BYTES = 512
MAX_DISPUTE_REASON_BYTES = 256


class MediatorData(arc4.Struct):
    address: arc4.Address
    bond_amount: arc4.UInt64
    is_bonded: arc4.UInt64
    did_hash: arc4.StaticArray[arc4.Byte, typing.Literal[32]]

class EscrowContract(ARC4Contract):
    def __init__(self) -> None:
        self.payout_type = Box(Bytes, key="payout_type")
        self.is_hitm = Box(UInt64, key="is_hitm")
        self.review_deadline = Box(UInt64, key="review_deadline")
        self.rejection_count = Box(UInt64, key="rejection_count")
        self.escrow_amount = Box(UInt64, key="escrow_amount")
        self.asset_id = Box(UInt64, key="asset_id")
        self.creator_address = Box(Account, key="creator_address")
        self.agent_address = Box(Account, key="agent_address")
        self.proof_url = Box(Bytes, key="proof_url")
        self.proof_data = Box(Bytes, key="proof_data")
        self.bounty_id = Box(Bytes, key="bounty_id")
        self.dispute_reason = Box(Bytes, key="dispute_reason")
        self.dispute_initiator = Box(Account, key="dispute_initiator")
        self.claim_deadline = Box(UInt64, key="claim_deadline")
        self.claim_timestamp = Box(UInt64, key="claim_timestamp")
        self.github_status = Box(Bytes, key="github_status")
        self.dispute_timestamp = Box(UInt64, key="dispute_timestamp")
        self.review_days = Box(UInt64, key="review_days")
        self.state_box = Box(UInt64, key="state")
        self.mediator_data = Box(MediatorData, key="mediator_data")
        self.treasury_address = Box(Account, key="treasury_address")
        self.oidc_token = Box(Bytes, key="oidc_token")
        self.candidate_count = Box(UInt64, key="candidate_count")
        self.arbitrator_1 = Box(Account, key="arbitrator_1")
        self.arbitrator_2 = Box(Account, key="arbitrator_2")
        self.arbitrator_3 = Box(Account, key="arbitrator_3")
        self.arbitrator_1_vote = Box(UInt64, key="arbitrator_1_vote")
        self.arbitrator_2_vote = Box(UInt64, key="arbitrator_2_vote")
        self.arbitrator_3_vote = Box(UInt64, key="arbitrator_3_vote")

    def _get_candidate_count(self) -> UInt64:
        val, exists = self.candidate_count.maybe()
        return val if exists else UInt64(0)

    def _get_asset_id(self) -> UInt64:
        val, exists = self.asset_id.maybe()
        return val if exists else UInt64(0)

    def _get_is_hitm(self) -> UInt64:
        val, exists = self.is_hitm.maybe()
        return val if exists else UInt64(0)

    def _get_review_days(self) -> UInt64:
        val, exists = self.review_days.maybe()
        return val if exists else UInt64(0)

    def _get_agent_address(self) -> Account:
        val, exists = self.agent_address.maybe()
        return val if exists else Account(Bytes(32 * b"\x00"))

    def _get_rejection_count(self) -> UInt64:
        val, exists = self.rejection_count.maybe()
        return val if exists else UInt64(0)

    def _verify_escrow_funding(self, escrow_amount: UInt64, asset_id: UInt64) -> None:
        assert Global.group_size == 2, "Group size must be 2"
        assert Txn.group_index == 1, "App call must be second in group"

        if asset_id > 0:
            asset_tx = gtxn.AssetTransferTransaction(0)
            assert asset_tx.xfer_asset.id == asset_id, "Asset ID mismatch"
            assert asset_tx.asset_amount == escrow_amount, "Asset amount mismatch"
            assert asset_tx.asset_receiver == Global.current_application_address, "Asset receiver mismatch"
        else:
            pay_tx = gtxn.PaymentTransaction(0)
            assert pay_tx.receiver == Global.current_application_address, "Receiver mismatch"
            assert pay_tx.amount == escrow_amount, "Amount mismatch"

    def _verify_escrow_balance(self, asset_id: UInt64, escrow_amount: UInt64) -> None:
        if asset_id > 0:
            balance, exists = op.AssetHoldingGet.asset_balance(
                Global.current_application_address, asset_id
            )
            assert exists, "Contract is not opted into the asset"
            assert balance >= escrow_amount, "Insufficient asset balance"
        else:
            app_balance, exists = op.AcctParamsGet.acct_balance(Global.current_application_address)
            assert exists, "Failed to read contract balance"
            assert app_balance >= escrow_amount, "Insufficient contract balance"

    def _send_payout(self, receiver: Account, amount: UInt64, asset_id: UInt64) -> None:
        if asset_id == 0:
            itxn.Payment(
                receiver=receiver,
                amount=amount,
                fee=0,
            ).submit()
        else:
            itxn.AssetTransfer(
                xfer_asset=asset_id,
                asset_receiver=receiver,
                asset_amount=amount,
                fee=0,
            ).submit()

    def _send_fee_split(
        self,
        primary_recipient: Account,
        escrow_amount: UInt64,
        asset_id: UInt64,
        mediator_addr: Account,
        is_dispute: UInt64 = UInt64(0),
    ) -> UInt64:
        """Split the 2% platform fee 50/50 between royalty and treasury,
        pay the 0.25% mediator fee, and return the remaining balance.

        - 1% of escrow_amount -> Creator royalty (deduped if primary == creator)
        - 1% of escrow_amount  -> Treasury
        - 0.25% of escrow_amount -> Mediator (redirected to primary_recipient if undisputed or HITM)
        """
        fee_platform = escrow_amount * 2 // 100  # 2% total platform fee
        fee_creator = fee_platform // 2          # 1% royalty
        fee_treasury = fee_platform - fee_creator  # 1% treasury
        fee_mediator = escrow_amount * 25 // 10000  # 0.25%

        # Dedup royalty when primary recipient is the creator
        is_creator = self.creator_address.value == primary_recipient

        if not is_creator:
            self._send_payout(self.creator_address.value, fee_creator, asset_id)

        self._send_payout(self.treasury_address.value, fee_treasury, asset_id)

        # Mediator Fee Safety Net (Constitution v2.1.0)
        is_hitm = self._get_is_hitm() == 1
        if is_hitm or is_dispute == UInt64(0):
            self._send_payout(primary_recipient, fee_mediator, asset_id)
        else:
            self._send_payout(mediator_addr, fee_mediator, asset_id)

        return escrow_amount - fee_creator - fee_treasury - fee_mediator

    @arc4.abimethod(create="require")
    def deploy(self) -> None:
        pass

    @arc4.abimethod
    def create_bounty(
        self,
        bounty_id: Bytes,
        escrow_amount: UInt64,
        is_hitm: UInt64,
        asset_id: UInt64,
        review_days: UInt64,
        mediator: Account,
        treasury: Account,
    ) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        # SECURITY FIX: Prevent re-initialization
        val, exists = self.state_box.maybe()
        assert not exists, "Bounty already initialized"

        # Validate inputs
        assert bounty_id.length <= 64
        assert escrow_amount > 0
        assert is_hitm <= 1
        assert asset_id >= 0

        # OPT-IN ASA: If asset_id > 0, the app account must opt-in to it first.
        if asset_id > 0:
            itxn.AssetTransfer(
                xfer_asset=asset_id,
                asset_receiver=Global.current_application_address,
                asset_amount=0,
                fee=0,
            ).submit()

        # Initialize state
        self.state_box.value = UInt64(OPEN)

        # Initialize mediator data inside a single box
        self.mediator_data.value = MediatorData(
            address=arc4.Address(mediator),
            bond_amount=arc4.UInt64(0),  # Will be populated when bonded
            is_bonded=arc4.UInt64(0),
            did_hash=arc4.StaticArray[arc4.Byte, typing.Literal[32]].from_bytes(Bytes(b"\x00" * 32))
        )
        self.treasury_address.value = treasury
        self.escrow_amount.value = escrow_amount
        self.bounty_id.value = bounty_id
        self.creator_address.value = Txn.sender

        if is_hitm > 0:
            self.is_hitm.value = is_hitm
        if asset_id > 0:
            self.asset_id.value = asset_id
        if review_days > 0:
            self.review_days.value = review_days

        log(Bytes(b"bounty_created"))
        log(bounty_id)

    @arc4.abimethod
    def claim_bounty(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == OPEN
        assert Txn.sender != self.creator_address.value, "Cannot claim your own bounty"
        assert self._get_agent_address() == Account(Bytes(32 * b"\x00")), "Bounty already claimed"

        # Validate that the claiming agent has opted in to the reward ASA (if asset bounty)
        asset_id = self._get_asset_id()
        if asset_id > 0:
            balance, exists = op.AssetHoldingGet.asset_balance(Txn.sender, asset_id)
            assert exists, "Claiming agent must opt-in to the asset first"

        self.agent_address.value = Txn.sender
        self.state_box.value = UInt64(CLAIMED)

        # Set claim deadline
        claim_timeout = TemplateVar[UInt64]("CLAIM_TIMEOUT")
        self.claim_deadline.value = Global.latest_timestamp + claim_timeout
        self.claim_timestamp.value = Global.latest_timestamp

        log(Bytes(b"bounty_claimed"))

    @arc4.abimethod
    def submit_work(self, proof_url: Bytes, proof_data: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        current = self.state_box.value

        if current == CLAIMED:
            assert Txn.sender == self.agent_address.value, "Only claiming agent can submit work"
            assert proof_url.length > 0
            assert proof_url.length <= MAX_URL_BYTES
            assert proof_data.length > 0
            assert proof_data.length <= MAX_PROOF_BYTES

            self.proof_url.value = proof_url
            self.proof_data.value = proof_data
            self.state_box.value = UInt64(SUBMITTED)

            # HITM: Set review deadline if enabled
            is_hitm_val, hitm_exists = self.is_hitm.maybe()
            if hitm_exists and is_hitm_val == 1:
                review_days_val, days_exists = self.review_days.maybe()
                days = review_days_val if days_exists else UInt64(0)
                self.review_deadline.value = Global.latest_timestamp + days * 86400

            log(Bytes(b"work_submitted"))

        elif current == REJECTED:
            agent_val, agent_exists = self.agent_address.maybe()
            assert agent_exists and Txn.sender == agent_val, "Only claiming agent can submit work"
            
            rej_val, rej_exists = self.rejection_count.maybe()
            rejections = rej_val if rej_exists else UInt64(0)
            assert rejections < MAX_REJECTIONS

            assert proof_url.length > 0
            assert proof_url.length <= MAX_URL_BYTES
            assert proof_data.length > 0
            assert proof_data.length <= MAX_PROOF_BYTES

            self.proof_url.value = proof_url
            self.proof_data.value = proof_data
            self.rejection_count.value = rejections + 1
            self.state_box.value = UInt64(SUBMITTED)

            # HITM: Reset review deadline on revision if enabled
            is_hitm_val, hitm_exists = self.is_hitm.maybe()
            if hitm_exists and is_hitm_val == 1:
                review_days_val, days_exists = self.review_days.maybe()
                days = review_days_val if days_exists else UInt64(0)
                self.review_deadline.value = Global.latest_timestamp + days * 86400

            log(Bytes(b"work_revise_submitted"))

        else:
            assert False, "Invalid state for submit_work"

    @arc4.abimethod
    def approve_work(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == SUBMITTED
        assert Txn.sender == self.creator_address.value, "Only creator can approve work"

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        self.payout_type.value = Bytes(PAYOUT)
        self.state_box.value = UInt64(CLOSED)

        # Split platform fee: 1% royalty (creator) + 1% treasury, 0.25% mediator
        remaining_amount = self._send_fee_split(
            self._get_agent_address(), escrow_amount, asset_id,
            Account(self.mediator_data.value.address.bytes),
        )
        self._send_payout(self._get_agent_address(), remaining_amount, asset_id)

        log(Bytes(b"work_approved"))

    @arc4.abimethod
    def reject_work(self, reason: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == SUBMITTED
        assert Txn.sender == self.creator_address.value, "Only creator can reject work"
        assert self._get_rejection_count() < MAX_REJECTIONS

        self.rejection_count.value = self._get_rejection_count() + 1
        self.state_box.value = UInt64(REJECTED)

        log(Bytes(b"work_rejected"))
        log(reason)

    @arc4.abimethod
    def submit_dispute(self, reason: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        state = self.state_box.value
        assert state == SUBMITTED or state == REJECTED
        assert Txn.sender == self.creator_address.value or Txn.sender == self._get_agent_address()
        assert reason.length > 0
        assert reason.length <= MAX_DISPUTE_REASON_BYTES

        self.dispute_reason.value = reason
        self.dispute_initiator.value = Txn.sender
        self.state_box.value = UInt64(DISPUTED)
        self.dispute_timestamp.value = Global.latest_timestamp

        # Select 3 arbitrators (fallback to treasury if pool size is too small)
        count = self._get_candidate_count()
        treasury = self.treasury_address.value
        creator = self.creator_address.value
        worker = self._get_agent_address()

        arb1 = treasury
        arb2 = treasury
        arb3 = treasury

        if count > UInt64(0):
            seed = op.sha256(Txn.tx_id + op.itob(Global.latest_timestamp))
            start_idx = op.btoi(seed) % count

            # Try to find arb1
            idx = start_idx
            found = False
            searched = UInt64(0)
            while searched < count and not found:
                candidate = Box(Account, key=Bytes(b"cand_addr_") + op.itob(idx)).value
                if candidate != creator and candidate != worker:
                    arb1 = candidate
                    found = True
                idx = (idx + 1) % count
                searched = searched + 1

            # Try to find arb2
            found = False
            searched = UInt64(0)
            while searched < count and not found:
                candidate = Box(Account, key=Bytes(b"cand_addr_") + op.itob(idx)).value
                if candidate != creator and candidate != worker and candidate != arb1:
                    arb2 = candidate
                    found = True
                idx = (idx + 1) % count
                searched = searched + 1

            # Try to find arb3
            found = False
            searched = UInt64(0)
            while searched < count and not found:
                candidate = Box(Account, key=Bytes(b"cand_addr_") + op.itob(idx)).value
                if candidate != creator and candidate != worker and candidate != arb1 and candidate != arb2:
                    arb3 = candidate
                    found = True
                idx = (idx + 1) % count
                searched = searched + 1

        self.arbitrator_1.value = arb1
        self.arbitrator_2.value = arb2
        self.arbitrator_3.value = arb3

        self.arbitrator_1_vote.value = UInt64(0)
        self.arbitrator_2_vote.value = UInt64(0)
        self.arbitrator_3_vote.value = UInt64(0)

        log(Bytes(b"dispute_submitted"))
        log(arb1.bytes)
        log(arb2.bytes)
        log(arb3.bytes)

    @arc4.abimethod
    def vote_dispute(self, vote_option: UInt64) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == DISPUTED, "Bounty is not disputed"
        assert vote_option == UInt64(1) or vote_option == UInt64(2) or vote_option == UInt64(3), "Invalid vote option"

        sender = Txn.sender
        voted = False
        if sender == self.arbitrator_1.value and self.arbitrator_1_vote.value == UInt64(0):
            self.arbitrator_1_vote.value = vote_option
            voted = True
        elif sender == self.arbitrator_2.value and self.arbitrator_2_vote.value == UInt64(0):
            self.arbitrator_2_vote.value = vote_option
            voted = True
        elif sender == self.arbitrator_3.value and self.arbitrator_3_vote.value == UInt64(0):
            self.arbitrator_3_vote.value = vote_option
            voted = True

        assert voted, "Sender is not an assigned arbitrator with a pending vote"

        log(Bytes(b"arbitrator_voted"))
        log(sender.bytes)
        log(op.itob(vote_option))

        # Check consensus
        v1 = self.arbitrator_1_vote.value
        v2 = self.arbitrator_2_vote.value
        v3 = self.arbitrator_3_vote.value

        consensus_option = UInt64(0)
        if v1 != UInt64(0) and v1 == v2:
            consensus_option = v1
        elif v1 != UInt64(0) and v1 == v3:
            consensus_option = v1
        elif v2 != UInt64(0) and v2 == v3:
            consensus_option = v2
        elif v1 != UInt64(0) and v2 != UInt64(0) and v3 != UInt64(0):
            consensus_option = UInt64(3)

        if consensus_option != UInt64(0):
            self._execute_arbitration_payout(consensus_option)

    def _execute_arbitration_payout(self, consensus_option: UInt64) -> None:
        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        fee_arbitration = escrow_amount * 5 // 10000

        v1 = self.arbitrator_1_vote.value
        v2 = self.arbitrator_2_vote.value
        v3 = self.arbitrator_3_vote.value

        voted_count = UInt64(0)
        if v1 != UInt64(0):
            voted_count = voted_count + 1
        if v2 != UInt64(0):
            voted_count = voted_count + 1
        if v3 != UInt64(0):
            voted_count = voted_count + 1

        fee_per_arbitrator = fee_arbitration // voted_count
        actual_arbitration_payout = fee_per_arbitrator * voted_count

        # Pay platform fee split (royalty + treasury + mediator) then arbitrators
        if consensus_option == UInt64(1):
            remaining_amount = self._send_fee_split(
                self._get_agent_address(), escrow_amount, asset_id,
                Account(self.mediator_data.value.address.bytes),
                is_dispute=UInt64(1),
            )
            remaining_amount = remaining_amount - actual_arbitration_payout
            self.payout_type.value = Bytes(PAYOUT)
            self.state_box.value = UInt64(CLOSED)

            # Pay voting arbitrators
            if v1 != UInt64(0):
                self._send_payout(self.arbitrator_1.value, fee_per_arbitrator, asset_id)
            if v2 != UInt64(0):
                self._send_payout(self.arbitrator_2.value, fee_per_arbitrator, asset_id)
            if v3 != UInt64(0):
                self._send_payout(self.arbitrator_3.value, fee_per_arbitrator, asset_id)

            self._send_payout(self._get_agent_address(), remaining_amount, asset_id)
            log(Bytes(b"dispute_resolved_agent_win"))
        elif consensus_option == UInt64(2):
            remaining_amount = self._send_fee_split(
                self.creator_address.value, escrow_amount, asset_id,
                Account(self.mediator_data.value.address.bytes),
                is_dispute=UInt64(1),
            )
            remaining_amount = remaining_amount - actual_arbitration_payout
            self.payout_type.value = Bytes(REFUND)
            self.state_box.value = UInt64(CLOSED)

            # Pay voting arbitrators
            if v1 != UInt64(0):
                self._send_payout(self.arbitrator_1.value, fee_per_arbitrator, asset_id)
            if v2 != UInt64(0):
                self._send_payout(self.arbitrator_2.value, fee_per_arbitrator, asset_id)
            if v3 != UInt64(0):
                self._send_payout(self.arbitrator_3.value, fee_per_arbitrator, asset_id)

            self._send_payout(self.creator_address.value, remaining_amount, asset_id)
            log(Bytes(b"dispute_resolved_creator_win"))
        else:
            remaining_amount = self._send_fee_split(
                self.creator_address.value, escrow_amount, asset_id,
                Account(self.mediator_data.value.address.bytes),
                is_dispute=UInt64(1),
            )
            remaining_amount = remaining_amount - actual_arbitration_payout
            self.payout_type.value = Bytes(SPLIT)
            self.state_box.value = UInt64(CLOSED)

            # Pay voting arbitrators
            if v1 != UInt64(0):
                self._send_payout(self.arbitrator_1.value, fee_per_arbitrator, asset_id)
            if v2 != UInt64(0):
                self._send_payout(self.arbitrator_2.value, fee_per_arbitrator, asset_id)
            if v3 != UInt64(0):
                self._send_payout(self.arbitrator_3.value, fee_per_arbitrator, asset_id)

            half_amount = remaining_amount // 2
            self._send_payout(self.creator_address.value, half_amount, asset_id)
            self._send_payout(self._get_agent_address(), half_amount, asset_id)
            log(Bytes(b"dispute_resolved_split"))

    @arc4.abimethod
    def resolve_dispute(self, resolution: Bytes, mediator_signature: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == DISPUTED
        assert resolution == Bytes(b"agent_win") or resolution == Bytes(b"creator_win")
        assert mediator_signature.length > 0

        # Cryptographically verify mediator signature
        mediator_addr = self.mediator_data.value.address.bytes
        message = op.itob(Global.current_application_id.id) + resolution
        assert op.ed25519verify(message, mediator_signature, mediator_addr), "Invalid mediator signature"

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        if resolution == Bytes(b"agent_win"):
            self.payout_type.value = Bytes(PAYOUT)
            self.state_box.value = UInt64(CLOSED)
            remaining_amount = self._send_fee_split(
                self._get_agent_address(), escrow_amount, asset_id,
                Account(self.mediator_data.value.address.bytes),
                is_dispute=UInt64(1),
            )
            self._send_payout(self._get_agent_address(), remaining_amount, asset_id)
            log(Bytes(b"dispute_resolved_agent_win"))
        else:
            self.payout_type.value = Bytes(REFUND)
            self.state_box.value = UInt64(CLOSED)
            remaining_amount = self._send_fee_split(
                self.creator_address.value, escrow_amount, asset_id,
                Account(self.mediator_data.value.address.bytes),
                is_dispute=UInt64(1),
            )
            self._send_payout(self.creator_address.value, remaining_amount, asset_id)
            log(Bytes(b"dispute_resolved_creator_win"))

    @arc4.abimethod
    def auto_resolve_creator_win(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp

        assert self.state_box.value == DISPUTED

        created_ts = self.dispute_timestamp.value
        timeout = UInt64(14 * 24 * 60 * 60)  # 14 days
        assert Global.latest_timestamp > created_ts + timeout

        self.payout_type.value = Bytes(REFUND)
        self.state_box.value = UInt64(CLOSED)

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        self._send_fee_split(
            self.creator_address.value, escrow_amount, asset_id,
            Account(self.mediator_data.value.address.bytes),
            is_dispute=UInt64(1),
        )
        self._send_payout(self.creator_address.value, escrow_amount, asset_id)

        log(Bytes(b"dispute_auto_resolved_creator_win"))

    @arc4.abimethod
    def timeout_dispute(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp

        assert self.state_box.value == DISPUTED

        dispute_ts = self.dispute_timestamp.value
        dispute_timeout = TemplateVar[UInt64]("DISPUTE_TIMEOUT")
        assert Global.latest_timestamp > dispute_ts + dispute_timeout, "Dispute timeout not yet reached"

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        self.payout_type.value = Bytes(SPLIT)
        self.state_box.value = UInt64(CLOSED)

        # Split platform fee; remainder split between creator and agent
        remaining_amount = self._send_fee_split(
            self.creator_address.value, escrow_amount, asset_id,
            Account(self.mediator_data.value.address.bytes),
            is_dispute=UInt64(1),
        )
        half_amount = remaining_amount // 2
        self._send_payout(self.creator_address.value, half_amount, asset_id)
        self._send_payout(self._get_agent_address(), half_amount, asset_id)

        log(Bytes(b"dispute_timeout_split"))

    @arc4.abimethod
    def auto_release(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp

        assert self.state_box.value == SUBMITTED
        assert self._get_is_hitm() == 1

        deadline = self.review_deadline.value
        assert Global.latest_timestamp >= deadline

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        self.payout_type.value = Bytes(PAYOUT)
        self.state_box.value = UInt64(CLOSED)

        # Split platform fee; remainder to agent
        remaining_amount = self._send_fee_split(
            self._get_agent_address(), escrow_amount, asset_id,
            Account(self.mediator_data.value.address.bytes),
        )
        self._send_payout(self._get_agent_address(), remaining_amount, asset_id)

        log(Bytes(b"auto_released_hitm"))

    @arc4.abimethod
    def claim_abandoned(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == REJECTED
        assert self._get_rejection_count() >= MAX_REJECTIONS
        assert Txn.sender == self.creator_address.value

        escrow_amount = self.escrow_amount.value
        asset_id = self._get_asset_id()
        self._verify_escrow_balance(asset_id, escrow_amount)

        self.payout_type.value = Bytes(REFUND)
        self.state_box.value = UInt64(CLOSED)

        # Split platform fee; remainder to creator (deduped)
        remaining_amount = self._send_fee_split(
            self.creator_address.value, escrow_amount, asset_id,
            Account(self.mediator_data.value.address.bytes),
        )
        self._send_payout(self.creator_address.value, remaining_amount, asset_id)

        log(Bytes(b"abandoned_refunded_creator"))

    @arc4.abimethod
    def expire_claim(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp

        assert self.state_box.value == CLAIMED

        claim_deadline = self.claim_deadline.value
        assert Global.latest_timestamp > claim_deadline, "Claim deadline not yet reached"

        # Record claim expiry
        self.state_box.value = UInt64(CLAIM_EXPIRED)
        log(Bytes(b"claim_expired"))
        log(self.bounty_id.value)
        log(self._get_agent_address().bytes)
        log(Bytes(b"karma_penalty_20"))

        # SECURITY FIX: Revert agent address to zero address so someone else can claim
        self.agent_address.value = Account(Bytes(32 * b"\x00"))

        # Revert to OPEN so others can claim
        self.state_box.value = UInt64(OPEN)
        self.rejection_count.value = UInt64(0)

        log(Bytes(b"bounty_reopened"))

    @arc4.abimethod
    def github_verify(self, pr_url: Bytes, test_hash: Bytes, oidc_token: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert self.state_box.value == SUBMITTED

        # Store GitHub verification data
        self.proof_url.value = pr_url
        self.github_status.value = Bytes(b"pending")

        # Store test hash in proof_data
        self.proof_data.value = test_hash

        # Store OIDC token
        self.oidc_token.value = oidc_token

        log(Bytes(b"github_verified"))
        log(self.bounty_id.value)
        log(Bytes(b"pending"))

    @arc4.abimethod
    def set_github_status(self, status: Bytes) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert status == Bytes(b"pass") or status == Bytes(b"fail") or status == Bytes(b"pending")

        self.github_status.value = status

        log(Bytes(b"github_status_updated"))
        log(status)

    @arc4.abimethod
    def get_bounty_info(self) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp

        log(Bytes(b"bounty_info"))
        log(op.itob(self.state_box.value))
        log(self.bounty_id.value)
        log(op.itob(self.escrow_amount.value))
        log(self.creator_address.value.bytes)
        log(self.agent_address.value.bytes)
        log(op.itob(self.rejection_count.value))

    @arc4.abimethod
    def register_arbitrator(self, address: Account) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert Txn.sender == address, "Sender must match address to register"

        # Check if already registered
        key_idx = Bytes(b"cand_idx_") + address.bytes
        dummy, exists = op.Box.get(key_idx)
        assert not exists, "Arbitrator already registered"

        count = self._get_candidate_count()

        # Write to pool
        Box(Account, key=Bytes(b"cand_addr_") + op.itob(count)).value = address
        Box(UInt64, key=key_idx).value = count

        # Increment count
        self.candidate_count.value = count + 1

        log(Bytes(b"arbitrator_registered"))
        log(address.bytes)

    @arc4.abimethod
    def deregister_arbitrator(self, address: Account) -> None:
        assert Txn.type_enum == TransactionType.ApplicationCall
        assert Txn.on_completion == OnCompleteAction.NoOp
        assert Txn.rekey_to == Account(Bytes(32 * b"\x00"))

        assert Txn.sender == address, "Sender must match address to deregister"

        # Check if registered
        key_idx = Bytes(b"cand_idx_") + address.bytes
        dummy, exists = op.Box.get(key_idx)
        assert exists, "Arbitrator not registered"

        idx_box = Box(UInt64, key=key_idx)
        count = self._get_candidate_count()
        remove_idx = idx_box.value
        last_idx = count - 1

        if remove_idx != last_idx:
            # Swap with last element
            last_addr = Box(Account, key=Bytes(b"cand_addr_") + op.itob(last_idx)).value
            Box(Account, key=Bytes(b"cand_addr_") + op.itob(remove_idx)).value = last_addr
            Box(UInt64, key=Bytes(b"cand_idx_") + last_addr.bytes).value = remove_idx

        # Delete last element box and reverse mapping index box
        key_addr = Bytes(b"cand_addr_") + op.itob(last_idx)
        assert op.Box.delete(key_addr), "Failed to delete address box"
        assert op.Box.delete(key_idx), "Failed to delete index box"

        self.candidate_count.value = last_idx

        log(Bytes(b"arbitrator_deregistered"))
        log(address.bytes)

    @arc4.abimethod(allow_actions=["DeleteApplication"])
    def delete_bounty(self) -> None:
        assert Txn.sender == self.creator_address.value, "Only creator can delete application"
        assert self.state_box.value == CLOSED, "Bounty must be fully closed/paid out before deletion"
        
        # Sweep all remaining ALGO and close out the contract account
        app_balance, exists = op.AcctParamsGet.acct_balance(Global.current_application_address)
        if exists and app_balance > 0:
            itxn.Payment(
                receiver=self.creator_address.value,
                amount=UInt64(0),
                fee=0,
                close_remainder_to=self.creator_address.value
            ).submit()
