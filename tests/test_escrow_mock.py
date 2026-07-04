# Constants representing contract states
OPEN = 0
CLAIMED = 1
SUBMITTED = 2
REJECTED = 3
DISPUTED = 4
CLOSED = 5

class MockEscrowState:
    def __init__(self, bounty_id: str, amount: int, hitm: bool, creator: str, worker: str = None):
        self.bounty_id = bounty_id
        self.amount = amount
        self.hitm = hitm
        self.creator = creator
        self.worker = worker
        self.state = OPEN
        self.rejections = 0
        self.payout_type = None

    def claim(self, worker: str):
        if self.state != OPEN:
            raise ValueError("Bounty not open")
        if worker == self.creator:
            raise ValueError("Creator cannot claim own bounty")
        self.state = CLAIMED
        self.worker = worker

    def submit_work(self, worker: str, pr_url: str):
        if self.state not in [CLAIMED, REJECTED]:
            raise ValueError("Bounty not in claimed or rejected state")
        if worker != self.worker:
            raise ValueError("Only claiming worker can submit work")
        self.state = SUBMITTED

    def approve_work(self, sender: str):
        if self.state != SUBMITTED:
            raise ValueError("Bounty not in submitted state")
        if sender != self.creator:
            raise ValueError("Only creator can approve work")
        self.state = CLOSED
        self.payout_type = "PAYOUT"

    def reject_work(self, sender: str):
        if self.state != SUBMITTED:
            raise ValueError("Bounty not in submitted state")
        if sender != self.creator:
            raise ValueError("Only creator can reject work")
        self.state = REJECTED
        self.rejections += 1

    def dispute(self, sender: str):
        if self.state not in [SUBMITTED, REJECTED]:
            raise ValueError("Cannot open dispute at this state")
        if sender not in [self.creator, self.worker]:
            raise ValueError("Only participants can open a dispute")
        self.state = DISPUTED

    def resolve_dispute(self, mediator: str, resolution: str):
        if self.state != DISPUTED:
            raise ValueError("Bounty not in disputed state")
        # Simulator assumes mediator is valid
        self.state = CLOSED
        if resolution == "agent_win":
            self.payout_type = "PAYOUT"
        elif resolution == "creator_win":
            self.payout_type = "REFUND"
        elif resolution == "split":
            self.payout_type = "SPLIT"

# Test state machine transitions
def test_happy_path_trustless():
    escrow = MockEscrowState("b_1", 10000000, False, "creator1")
    assert escrow.state == OPEN
    
    # Claim
    escrow.claim("worker1")
    assert escrow.state == CLAIMED
    assert escrow.worker == "worker1"
    
    # Submit
    escrow.submit_work("worker1", "https://github.com/vantage-labs/repo/pull/1")
    assert escrow.state == SUBMITTED
    
    # Approve
    escrow.approve_work("creator1")
    assert escrow.state == CLOSED
    assert escrow.payout_type == "PAYOUT"

def test_rejection_path():
    escrow = MockEscrowState("b_2", 20000000, True, "creator1")
    escrow.claim("worker1")
    escrow.submit_work("worker1", "https://github.com/vantage-labs/repo/pull/1")
    
    # Reject
    escrow.reject_work("creator1")
    assert escrow.state == REJECTED
    assert escrow.rejections == 1
    
    # Resubmit & Approve
    escrow.submit_work("worker1", "https://github.com/vantage-labs/repo/pull/1")
    assert escrow.state == SUBMITTED
    escrow.approve_work("creator1")
    assert escrow.state == CLOSED
    assert escrow.payout_type == "PAYOUT"

def test_dispute_path():
    escrow = MockEscrowState("b_3", 10000000, True, "creator1")
    escrow.claim("worker1")
    escrow.submit_work("worker1", "https://github.com/vantage-labs/repo/pull/1")
    escrow.reject_work("creator1")
    
    # Worker disputes
    escrow.dispute("worker1")
    assert escrow.state == DISPUTED
    
    # Mediator resolves split
    escrow.resolve_dispute("mediator1", "split")
    assert escrow.state == CLOSED
    assert escrow.payout_type == "SPLIT"

def test_mock_escrow_error_paths():
    import pytest
    escrow = MockEscrowState("b_err", 100, False, "creator")
    
    with pytest.raises(ValueError, match="Creator cannot claim own bounty"):
        escrow.claim("creator")
        
    with pytest.raises(ValueError, match="Bounty not in claimed or rejected state"):
        escrow.submit_work("worker", "url")
        
    escrow.claim("worker")
    with pytest.raises(ValueError, match="Bounty not open"):
        escrow.claim("worker")
        
    with pytest.raises(ValueError, match="Only claiming worker can submit work"):
        escrow.submit_work("stranger", "url")
        
    with pytest.raises(ValueError, match="Bounty not in submitted state"):
        escrow.approve_work("creator")
        
    with pytest.raises(ValueError, match="Bounty not in submitted state"):
        escrow.reject_work("creator")
        
    with pytest.raises(ValueError, match="Cannot open dispute at this state"):
        escrow.dispute("worker")
        
    escrow.submit_work("worker", "url")
    
    with pytest.raises(ValueError, match="Only creator can approve work"):
        escrow.approve_work("stranger")
        
    with pytest.raises(ValueError, match="Only creator can reject work"):
        escrow.reject_work("stranger")
        
    with pytest.raises(ValueError, match="Only participants can open a dispute"):
        escrow.dispute("stranger")
        
    escrow.reject_work("creator")
    escrow.dispute("worker")
    
    escrow2 = MockEscrowState("b_err2", 100, False, "creator")
    with pytest.raises(ValueError, match="Bounty not in disputed state"):
        escrow2.resolve_dispute("mediator", "agent_win")
