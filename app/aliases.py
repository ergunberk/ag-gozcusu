import json
import re
from pathlib import Path


class DeviceAliasStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def normalize_mac(mac: str) -> str:
        compact = re.sub(r"[^0-9A-Fa-f]", "", mac).upper()
        if len(compact) != 12:
            raise ValueError("Geçersiz MAC adresi.")
        return "-".join(compact[i:i + 2] for i in range(0, 12, 2))

    def _read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return {str(key): str(value) for key, value in data.items()}
        except (json.JSONDecodeError, OSError):
            return {}

    def get(self, mac: str) -> str | None:
        return self._read().get(self.normalize_mac(mac))

    def set(self, mac: str, name: str) -> str:
        normalized_mac = self.normalize_mac(mac)
        clean_name = " ".join(name.strip().split())
        if not clean_name:
            raise ValueError("Cihaz adı boş olamaz.")
        if len(clean_name) > 40:
            raise ValueError("Cihaz adı en fazla 40 karakter olabilir.")
        aliases = self._read()
        aliases[normalized_mac] = clean_name
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.path)
        return clean_name

