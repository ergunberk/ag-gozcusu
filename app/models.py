from dataclasses import asdict, dataclass


@dataclass
class DeviceTraffic:
    ip: str
    mac: str
    name: str
    online: bool
    traffic_mbps: float
    total_bytes: int
    current_packets: int

    def to_dict(self) -> dict:
        return asdict(self)
