"""Download incremental dos dados abertos do ONS registrados em config.datasets.

Só baixa o que falta; o(s) mês(es) mais recente(s) são sempre re-baixados porque o ONS
ainda os atualiza (download.overwrite_last_n_months).
"""
from datetime import date
from pathlib import Path

import requests
import urllib3

from ..config import dataset_dir, get_logger, load_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("download")


def month_range(start: str, end: date):
    """Gera (ano, mês) de 'AAAA-MM' até o mês de `end`, inclusive."""
    y, m = (int(x) for x in start.split("-"))
    while (y, m) <= (end.year, end.month):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


class OnsDownloader:
    def __init__(self):
        cfg = load_config()
        self.base = cfg["ons_base"]
        self.datasets = cfg["datasets"]
        self.verify_ssl = cfg["download"].get("verify_ssl", True)
        self.timeout = cfg["download"].get("timeout", 300)
        self.refresh_months = cfg["download"].get("overwrite_last_n_months", 1)

    def plan(self, name: str, today: date | None = None) -> list[tuple[str, Path, bool]]:
        """Lista (url, destino, deve_sobrescrever) para um dataset."""
        today = today or date.today()
        spec = self.datasets[name]
        dest_dir = dataset_dir(name)
        items = []
        if spec["freq"] == "monthly":
            months = list(month_range(spec["start"], today))
            recent = set(months[-self.refresh_months:]) if self.refresh_months else set()
            for y, m in months:
                rel = spec["path"].format(y=y, m=f"{m:02d}")
                items.append((self.base + rel, dest_dir / Path(rel).name, (y, m) in recent))
        elif spec["freq"] == "yearly":
            for y in range(int(spec["start"]), today.year + 1):
                rel = spec["path"].format(y=y)
                items.append((self.base + rel, dest_dir / Path(rel).name, y == today.year))
        else:  # static
            rel = spec["path"]
            items.append((self.base + rel, dest_dir / Path(rel).name, True))
        return items

    def fetch(self, url: str, dest: Path) -> bool:
        try:
            r = requests.get(url, verify=self.verify_ssl, timeout=self.timeout)
        except requests.RequestException as e:
            logger.error(f"Erro ao baixar {url}: {e}")
            return False
        if r.status_code != 200:
            logger.warning(f"Indisponível ({r.status_code}): {url}")
            return False
        tmp = dest.with_suffix(dest.suffix + ".part")
        tmp.write_bytes(r.content)
        tmp.replace(dest)
        logger.info(f"OK {dest.name} ({len(r.content) / 1e6:.1f} MB)")
        return True

    def download(self, names: list[str] | None = None, force: bool = False) -> dict:
        names = names or list(self.datasets)
        resumo = {}
        for name in names:
            ok = skip = fail = 0
            for url, dest, refresh in self.plan(name):
                if dest.exists() and not (force or refresh):
                    skip += 1
                    continue
                if self.fetch(url, dest):
                    ok += 1
                else:
                    fail += 1
            resumo[name] = {"baixados": ok, "existentes": skip, "falhas": fail}
            logger.info(f"[{name}] baixados={ok} existentes={skip} falhas={fail}")
        return resumo
