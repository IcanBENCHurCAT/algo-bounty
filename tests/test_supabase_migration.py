from gateway.supabase_migration import _normalize_db_url

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
