"""Temperatura horária "Brasil": média ponderada pela carga de estações WMO (bulk do Meteostat).

Substitui o `temperatura_processada.parquet` (fonte desconhecida) do mini_dessem. É usada só pelo
sampler de carga v6: temperatura real hora a hora no histórico, climatologia mensal nas projeções.

    python run.py baixar temperatura      -> Data/raw/temperatura/{id}.csv.gz (um por estação)
    processar_temperatura()               -> Data/processed/temperatura_brasil.parquet (timestamp, temp_brasil_c)
"""
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import urllib3

from ..config import data_dir, get_logger, load_config

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = get_logger("temperatura")

# formato do bulk hourly do Meteostat (sem cabeçalho)
_COLS = ["date", "hour", "temp", "dwpt", "rhum", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun", "coco"]


def _cfg() -> dict:
    return load_config()["temperatura"]


def _raw_dir() -> Path:
    p = data_dir() / _cfg()["dir"]
    p.mkdir(parents=True, exist_ok=True)
    return p


def _processado() -> Path:
    p = data_dir() / _cfg()["arquivo_processado"]
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def baixar(force: bool = False) -> dict:
    """Baixa o CSV histórico de cada estação (o arquivo cobre toda a série; re-baixar atualiza)."""
    cfg = _cfg()
    resumo = {"baixados": 0, "existentes": 0, "falhas": 0}
    for est in cfg["estacoes"]:
        dest = _raw_dir() / f"{est['id']}.csv.gz"
        if dest.exists() and not force:
            resumo["existentes"] += 1
            continue
        url = cfg["fonte_url"].format(id=est["id"])
        try:
            r = requests.get(url, timeout=120, verify=False)
            r.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"{est['nome']} ({est['id']}): {e}")
            resumo["falhas"] += 1
            continue
        dest.write_bytes(r.content)
        logger.info(f"OK {est['nome']} ({est['id']}) {len(r.content) / 1e6:.1f} MB")
        resumo["baixados"] += 1
    logger.info(f"[temperatura] {resumo}")
    return resumo


def _serie_estacao(path: Path, inicio: str, fim: str) -> pd.Series:
    """Série horária (fuso local) de uma estação, com lacunas curtas interpoladas."""
    cfg = _cfg()
    df = pd.read_csv(path, names=_COLS, compression="gzip", usecols=["date", "hour", "temp"])
    ts = pd.to_datetime(df["date"]) + pd.to_timedelta(df["hour"], unit="h") + pd.Timedelta(hours=cfg["fuso_horas"])
    s = pd.Series(pd.to_numeric(df["temp"], errors="coerce").values, index=ts).sort_index()
    s = s[~s.index.duplicated()]
    grade = pd.date_range(inicio, pd.Timestamp(fim) + pd.Timedelta(hours=23), freq="h")
    s = s.reindex(grade)
    return s.interpolate(limit=cfg["max_lacuna_interp_h"], limit_area="inside")


def processar_temperatura(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Média ponderada das estações -> parquet (timestamp, temp_brasil_c, n_estacoes)."""
    from ..config import periodo
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    cfg = _cfg()
    series, pesos = [], []
    for est in cfg["estacoes"]:
        path = _raw_dir() / f"{est['id']}.csv.gz"
        if not path.exists():
            logger.warning(f"Estação {est['nome']} ({est['id']}) não baixada; ignorada")
            continue
        s = _serie_estacao(path, inicio, fim)
        logger.info(f"  {est['nome']:<32} peso {est['peso']:.2f}  cobertura {100 * s.notna().mean():5.1f}%")
        series.append(s.rename(est["id"]))
        pesos.append(est["peso"])
    if not series:
        raise FileNotFoundError("Nenhuma estação baixada. Rode: python run.py baixar temperatura")
    m = pd.concat(series, axis=1)
    w = np.array(pesos, dtype=float)
    valid = m.notna().values
    num = np.nansum(m.values * w, axis=1)
    den = (valid * w).sum(axis=1)
    out = pd.DataFrame({"timestamp": m.index, "temp_brasil_c": np.where(den > 0, num / np.where(den > 0, den, 1), np.nan),
                        "n_estacoes": valid.sum(axis=1)})
    out = out[out["n_estacoes"] > 0].reset_index(drop=True)
    out.to_parquet(_processado(), index=False)
    logger.info(f"temperatura_brasil: {out['timestamp'].min()} -> {out['timestamp'].max()}, {len(out):,} horas, "
                f"média {out['temp_brasil_c'].mean():.1f} °C -> {_processado()}")
    return out


_CACHE = None


def carregar_temperatura() -> pd.DataFrame:
    """Série horária processada (timestamp, temp_brasil_c). Cache em memória."""
    global _CACHE
    if _CACHE is None:
        p = _processado()
        if not p.exists():
            raise FileNotFoundError(f"{p} não existe. Rode: python run.py baixar temperatura && python run.py processar")
        df = pd.read_parquet(p)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        _CACHE = df
    return _CACHE


def temperatura_mensal() -> pd.DataFrame:
    """Média mensal observada (ano, mes, temp_media_c)."""
    df = carregar_temperatura()
    g = df.groupby([df["timestamp"].dt.year.rename("ano"), df["timestamp"].dt.month.rename("mes")])["temp_brasil_c"].mean()
    return g.rename("temp_media_c").reset_index()


def climatologia_mensal() -> dict[int, float]:
    """Média histórica por mês (fallback para projeções)."""
    df = carregar_temperatura()
    return df.groupby(df["timestamp"].dt.month)["temp_brasil_c"].mean().to_dict()


def temperaturas_dia(ano: int, mes: int, dia: int) -> dict[int, float] | None:
    """{hora: temp} do dia, ou None se não há dado real (projeção)."""
    df = carregar_temperatura()
    d = df[(df["timestamp"] >= pd.Timestamp(ano, mes, dia)) & (df["timestamp"] < pd.Timestamp(ano, mes, dia) + pd.Timedelta(days=1))]
    if len(d) < 24 or d["temp_brasil_c"].isna().any():
        return None
    return dict(zip(d["timestamp"].dt.hour, d["temp_brasil_c"]))
