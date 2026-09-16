"""Configuração, caminhos e logging compartilhados pelo pacote."""
import logging
import os
from datetime import date
from pathlib import Path

import yaml

# src/carga_liquida/config.py -> raiz do projeto = parents[2]
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "config.yaml"

MESES_PT = {1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"}
DIAS_SEMANA_PT = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sab", 6: "Dom"}

_config = None


def load_config() -> dict:
    """Carrega config.yaml (uma vez). Variáveis de ambiente sobrescrevem paths.*."""
    global _config
    if _config is None:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            _config = yaml.safe_load(f)
        for env, key in (("CARGA_LIQUIDA_DATA_DIR", "data_dir"), ("CARGA_LIQUIDA_OUTPUT_DIR", "output_dir")):
            if os.environ.get(env):
                _config["paths"][key] = os.environ[env]
    return _config


def _resolve(p: str) -> Path:
    p = Path(p)
    return p if p.is_absolute() else ROOT / p


def data_dir() -> Path:
    p = _resolve(load_config()["paths"]["data_dir"])
    p.mkdir(parents=True, exist_ok=True)
    return p


def output_dir(sub: str | None = None) -> Path:
    p = _resolve(load_config()["paths"]["output_dir"])
    if sub:
        p = p / sub
    p.mkdir(parents=True, exist_ok=True)
    return p


def dataset_dir(name: str) -> Path:
    """Pasta local de um dataset ONS registrado em config.datasets."""
    d = Path(load_config()["datasets"][name]["dir"])
    p = d if d.is_absolute() else data_dir() / d
    p.mkdir(parents=True, exist_ok=True)
    return p


def periodo() -> tuple[str, str]:
    """(inicio, fim) como 'AAAA-MM-DD'; fim null vira hoje."""
    per = load_config()["periodo"]
    fim = per.get("fim") or date.today().isoformat()
    return str(per["inicio"]), str(fim)


def get_logger(name: str) -> logging.Logger:
    cfg = load_config()["logging"]
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(cfg.get("level", "INFO"))
    fmt = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    log_file = ROOT / cfg.get("file", "logs/carga_liquida.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger
