import threading
import time
from test_features import fixture_client

def test_backend_shutdown_stops_database_pollers_and_voice_workers(tmp_path):
    app,_,_,client=fixture_client(tmp_path)
    with client:
        workers=[*app.state.voice_loop.threads,*app.state.speaker.threads,app.state.pc_alerts.thread]
        assert all(t.is_alive() for t in workers)
    assert all(not t.is_alive() for t in workers)
    assert app.state.voice_loop.closed.is_set() and app.state.speaker.closed.is_set()
    # A late caller gets a Python exception rather than racing native sqlite.close.
    import sqlite3,pytest
    with pytest.raises(sqlite3.ProgrammingError):app.state.store.settings()
