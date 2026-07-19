from gateway.supabase_migration import _normalize_db_url
from gateway.database import Bounty


def test_normalize_db_url():
    # "postgres://" URL is converted to "postgresql://"
    assert _normalize_db_url("postgres://user:pass@host/db") == "postgresql://user:pass@host/db"

    # "postgresql://" URL remains unchanged
    assert _normalize_db_url("postgresql://user:pass@host/db") == "postgresql://user:pass@host/db"

    # "sqlite:///" URL remains unchanged
    assert _normalize_db_url("sqlite:///algobounty.db") == "sqlite:///algobounty.db"

    # empty string "" remains unchanged
    assert _normalize_db_url("") == ""

    # None returns None
    assert _normalize_db_url(None) is None


def test_bounty_columns_and_defaults(db_session):
    # Test that platform_fee and treasury_address columns exist on the Bounty model and database table
    bounty = Bounty(
        bounty_id="test-migration-bounty",
        creator="CREATOR_ADDR",
        amount=1000000,
        repo_url="https://github.com/test/repo"
    )
    db_session.add(bounty)
    db_session.commit()

    retrieved = db_session.query(Bounty).filter_by(bounty_id="test-migration-bounty").first()
    assert retrieved is not None
    assert retrieved.platform_fee == 200
    assert retrieved.treasury_address == "RTCed54abc91f37d8d2d2cb2cf69ce60b0021fd67e5"

