from gateway.dependencies import get_db

def test_get_db():
    gen = get_db()
    db = next(gen)
    assert db is not None
    # Verify close is called in finally by finishing generator
    try:
        next(gen)
    except StopIteration:
        pass
