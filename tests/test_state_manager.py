import time

from core.state_manager import StateManager


def test_state_manager_updates_snapshot():
    manager = StateManager()
    payload = {"slots": [1, 0, 1], "gate": "open"}
    manager.update(payload)
    snapshot = manager.snapshot()

    assert snapshot["slots"] == [1, 0, 1]
    assert snapshot["free"] == 1
    assert snapshot["gate"] == "open"
    before = snapshot["last_update"]
    time.sleep(0.01)
    manager.update({"slots": [0, 0, 0], "gate": "closed"})
    snapshot2 = manager.snapshot()
    assert snapshot2["free"] == 3
    assert snapshot2["gate"] == "closed"
    assert snapshot2["last_update"] >= before

