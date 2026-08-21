import asyncio
import base64
import random
import re
import time
from abc import ABC, abstractmethod
from urllib.parse import quote

import httpx
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .config import Settings
from .models import DeviceTraffic


class TrafficProvider(ABC):
    @abstractmethod
    async def snapshot(self) -> list[DeviceTraffic]:
        raise NotImplementedError


class DemoProvider(TrafficProvider):
    def __init__(self) -> None:
        self.started = time.monotonic()
        self.devices = [
            ["192.168.1.101", "9C-6B-00-A8-7B-39", "BERK-PC", 2_400_000_000, 340_000_000],
            ["192.168.1.110", "6A-89-B9-2E-C6-91", "Telefon", 1_180_000_000, 92_000_000],
            ["192.168.1.25", "8C-85-90-AA-12-44", "Salon TV", 4_900_000_000, 24_000_000],
        ]

    async def snapshot(self) -> list[DeviceTraffic]:
        elapsed = time.monotonic() - self.started
        result = []
        for index, device in enumerate(self.devices):
            ip, mac, name, down_total, up_total = device
            wave = max(0.03, (1 + __import__("math").sin(elapsed / 3 + index * 1.7)) / 2)
            down = round((0.4 + wave * (11 - index * 2)) + random.uniform(-0.25, 0.25), 2)
            up = round(max(0.02, down * (0.06 + index * 0.02)), 2)
            device[3] += int(down * 125_000)
            device[4] += int(up * 125_000)
            result.append(DeviceTraffic(ip, mac, name, True, round(down + up, 2), device[3] + device[4], max(1, int((down + up) * 80))))
        return result


class RouterError(RuntimeError):
    pass


class TDW9970Provider(TrafficProvider):
    """TD-W9970 V3 web arayuzu icin oturum ve istatistik baglayicisi.

    Firmware istatistik URL'si kurulumda tarayici Network panelinden bir kez
    belirlenerek ROUTER_STATS_PATH'e yazilir. Parola loglanmaz.
    """

    def __init__(self, config: Settings) -> None:
        self.config = config
        self.client = httpx.AsyncClient(
            base_url=config.router_url,
            timeout=5,
            headers={"User-Agent": "AgDashboard/1.0", "Referer": f"{config.router_url}/"},
        )
        self.logged_in = False

    @staticmethod
    def _read_js_var(text: str, name: str) -> str:
        match = re.search(rf'var\s+{re.escape(name)}\s*=\s*["\']([^"\']+)', text)
        if not match:
            raise RouterError(f"Modem yanitinda {name} bulunamadi.")
        return match.group(1)

    @staticmethod
    def _rsa_hex(value: str, modulus_hex: str, exponent_hex: str) -> str:
        public_key = rsa.RSAPublicNumbers(
            int(exponent_hex, 16), int(modulus_hex, 16)
        ).public_key()
        encrypted = public_key.encrypt(value.encode("utf-8"), padding.PKCS1v15())
        return encrypted.hex()

    async def login(self) -> None:
        if not self.config.router_password:
            raise RouterError("ROUTER_PASSWORD .env dosyasinda ayarlanmamis.")
        await self.client.get("/")
        parm = await self.client.post("/cgi/getParm")
        parm.raise_for_status()
        modulus = self._read_js_var(parm.text, "nn")
        exponent = self._read_js_var(parm.text, "ee")
        username = self._rsa_hex(self.config.router_username, modulus, exponent)
        encoded_password = base64.b64encode(self.config.router_password.encode()).decode()
        password = self._rsa_hex(encoded_password, modulus, exponent)
        path = (
            "/cgi/login?UserName=" + quote(username)
            + "&Passwd=" + quote(password)
            + "&Action=1&LoginStatus=0"
        )
        response = await self.client.post(path)
        response.raise_for_status()
        if re.search(r"\$\.ret\s*=\s*[1-9]", response.text):
            raise RouterError("Modem girisi reddedildi. Kullanici adi veya sifreyi kontrol et.")
        self.logged_in = True

    @staticmethod
    def parse_statistics(text: str, interval: int) -> list[DeviceTraffic]:
        """TD-W9970 CGI bloklarını birleşik cihaz trafiğine dönüştürür."""
        rows = []
        blocks = re.split(r"^\[[^\]]+\]1\s*$", text, flags=re.MULTILINE)[1:]
        for block in blocks:
            values = dict(re.findall(r"^(\w+)=(.*)$", block, flags=re.MULTILINE))
            if not {"ipAddress", "macAddress", "totalBytes", "currBytes"} <= values.keys():
                continue
            ip_number = int(values["ipAddress"])
            ip = ".".join(str((ip_number >> shift) & 255) for shift in (24, 16, 8, 0))
            rows.append(DeviceTraffic(
                ip=ip, mac=values["macAddress"].strip().upper().replace(":", "-"),
                name=ip, online=True,
                traffic_mbps=round(int(values["currBytes"]) * 8 / interval / 1_000_000, 4),
                total_bytes=int(values["totalBytes"]), current_packets=int(values.get("currPkts", "0")),
            ))
        return rows

    async def snapshot(self) -> list[DeviceTraffic]:
        if not self.logged_in:
            await self.login()
        body = ("[STAT_CFG#0,0,0,0,0,0#0,0,0,0,0,0]0,0\r\n"
                "[STAT_ENTRY#0,0,0,0,0,0#0,0,0,0,0,0]1,0\r\n")
        response = await self.client.post("/cgi?1&5", content=body, headers={"Content-Type": "text/plain", "Referer": f"{self.config.router_url}/main/stat.htm"})
        if response.status_code in {401, 403}:
            self.logged_in = False
            await self.login()
            response = await self.client.post("/cgi?1&5", content=body)
        response.raise_for_status()
        rows = self.parse_statistics(response.text, self.config.poll_interval)
        if not rows:
            raise RouterError("Istatistik yaniti alindi ancak cihaz satirlari ayrıştırılamadi.")
        return rows


class TrafficService:
    def __init__(self, provider: TrafficProvider, interval: int) -> None:
        self.provider = provider
        self.interval = interval
        self.devices: list[DeviceTraffic] = []
        self.error: str | None = None
        self.updated_at: float | None = None
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if not self._task:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run(self) -> None:
        while True:
            try:
                self.devices = await self.provider.snapshot()
                self.updated_at = time.time()
                self.error = None
            except Exception as exc:
                self.error = str(exc)
            await asyncio.sleep(self.interval)

    def payload(self) -> dict:
        devices = [device.to_dict() for device in self.devices]
        return {
            "devices": devices, "error": self.error, "updated_at": self.updated_at,
            "totals": {
                "traffic_mbps": round(sum(item["traffic_mbps"] for item in devices), 3),
                "total_bytes": sum(item["total_bytes"] for item in devices),
                "online": sum(1 for item in devices if item["online"]),
            },
        }
