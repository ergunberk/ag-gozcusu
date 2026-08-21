from fastapi.testclient import TestClient

from app.main import app
from app.aliases import DeviceAliasStore
from app.providers import TDW9970Provider


def test_status_endpoint():
    with TestClient(app) as client:
        response = client.get("/api/status")
        assert response.status_code == 200
        assert "devices" in response.json()


def test_js_variable_parser():
    assert TDW9970Provider._read_js_var('var ee="010001";', "ee") == "010001"


def test_statistics_parser():
    sample = """[1,0,0,0,0,0]1
ipAddress=3232235886
macAddress=6A:89:B9:2E:C6:91
totalBytes=1000000
currPkts=45
currBytes=625000
[error]0
"""
    rows = TDW9970Provider.parse_statistics(sample, 5)
    assert rows[0].ip == "192.168.1.110"
    assert rows[0].traffic_mbps == 1.0
    assert rows[0].current_packets == 45


def test_alias_store(tmp_path):
    store = DeviceAliasStore(tmp_path / "names.json")
    store.set("9c:6b:00:a8:7b:39", "BERK-PC")
    assert store.get("9C-6B-00-A8-7B-39") == "BERK-PC"
