from unittest.mock import patch, MagicMock
from gateway.dependencies import get_db

@patch("gateway.dependencies.SessionLocal")
def test_get_db(mock_session_local):
    mock_db = MagicMock()
    mock_session_local.return_value = mock_db

    gen = get_db()

    # First iteration should yield the mock db
    db = next(gen)
    assert db == mock_db

    # SessionLocal should have been called to create the db
    mock_session_local.assert_called_once()

    # Verify close is called in finally by finishing generator
    try:
        next(gen)
    except StopIteration:
        pass

    # close should have been called exactly once
    mock_db.close.assert_called_once()
