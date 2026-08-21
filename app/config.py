import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("APP_MODE", "demo").lower()
    router_url: str = os.getenv("ROUTER_URL", "http://192.168.1.1").rstrip("/")
    router_username: str = os.getenv("ROUTER_USERNAME", "admin")
    router_password: str = os.getenv("ROUTER_PASSWORD", "")
    router_stats_path: str = os.getenv("ROUTER_STATS_PATH", "")
    poll_interval: int = max(2, int(os.getenv("POLL_INTERVAL", "5")))


settings = Settings()

