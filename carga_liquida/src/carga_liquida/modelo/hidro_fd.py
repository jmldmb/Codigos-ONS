"""Geração hidrelétrica fio d'água (FD) por regressão linear múltipla.

    FD = intercept + ghr·R + ena·ENA + peso_mes[mês] + peso_hora[hora] + peso_dia(DU|FDS)

R = geração das UHEs de reservatório (MW), ENA = ENA armazenável do SIN (MWmed). Os parâmetros
padrão (config.modelo.hidro_fd) são os do mini_dessem; `calibrar()` reestima todos por OLS nos dados
observados (FD/R do carga_liquida histórico, ENA diária) e grava em params_dir/hidro_fd.json, que
passa a ter precedência.
"""
import json

import numpy as np
import pandas as pd

from ..config import get_logger, load_config
from ..dados import ons
from ..observado import carga_liquida as cl
from . import feriados
from .samplers._base import params_dir

logger = get_logger("hidro_fd")
_PARAMS = None


def parametros(recarregar: bool = False) -> dict:
    """Calibrados (se existirem) ou os do config; chaves de peso_mes/peso_hora como int."""
    global _PARAMS
    if _PARAMS is None or recarregar:
        p = params_dir() / "hidro_fd.json"
        if p.exists():
            with open(p, encoding="utf-8") as f:
                raw = json.load(f)
            origem = f"calibrado ({raw.get('meta', {}).get('periodo', '?')})"
        else:
            raw = load_config()["modelo"]["hidro_fd"]
            origem = "config (legado)"
        _PARAMS = {"intercept": float(raw["intercept"]), "ghr": float(raw["ghr"]), "ena": float(raw["ena"]),
                   "peso_mes": {int(k): float(v) for k, v in raw["peso_mes"].items()},
                   "peso_hora": {int(k): float(v) for k, v in raw["peso_hora"].items()},
                   "peso_weekday": float(raw["peso_weekday"]), "peso_fds": float(raw["peso_fds"]), "origem": origem}
        logger.info(f"parâmetros hidro FD: {origem}")
    return _PARAMS


def calcular_fd(mes: int, hora: int, is_weekday: bool, R: float, ena: float, p: dict | None = None) -> float:
    p = p or parametros()
    return (p["intercept"] + p["ghr"] * R + p["ena"] * ena + p["peso_mes"][mes] + p["peso_hora"][hora]
            + (p["peso_weekday"] if is_weekday else p["peso_fds"]))


def base_observada() -> pd.DataFrame:
    """Horas com FD, R (histórico) e ENA armazenável do dia."""
    h = cl.carregar_historico()[["din_instante", "FD", "R", "mes", "hora"]].copy()
    ena = ons.carregar_ena()[["ena_data", "ena_armazenavel_mwmed"]].rename(columns={"ena_armazenavel_mwmed": "ena"})
    h["ena_data"] = h["din_instante"].dt.normalize()
    df = h.merge(ena, on="ena_data", how="inner").dropna(subset=["FD", "R", "ena"])
    df["is_weekday"] = df["din_instante"].dt.date.map(feriados.tipo_dia) == "DU"
    return df.reset_index(drop=True)


def avaliar(df: pd.DataFrame, p: dict) -> dict:
    fd_hat = (p["intercept"] + p["ghr"] * df["R"] + p["ena"] * df["ena"] + df["mes"].map(p["peso_mes"])
              + df["hora"].map(p["peso_hora"]) + np.where(df["is_weekday"], p["peso_weekday"], p["peso_fds"]))
    erro = fd_hat - df["FD"]
    return {"mae_mw": float(erro.abs().mean()), "bias_mw": float(erro.mean()),
            "mape_pct": float((erro.abs() / df["FD"]).mean() * 100),
            "r2": float(1 - (erro ** 2).sum() / ((df["FD"] - df["FD"].mean()) ** 2).sum()), "n": int(len(df))}


def calibrar(salvar: bool = True) -> dict:
    """OLS com dummies de mês (ref. dezembro), hora (ref. 23h) e FDS; grava hidro_fd.json."""
    df = base_observada()
    X = pd.DataFrame({"const": 1.0, "R": df["R"], "ena": df["ena"], "fds": (~df["is_weekday"]).astype(float)})
    for m in range(1, 12):
        X[f"m{m}"] = (df["mes"] == m).astype(float)
    for h in range(23):
        X[f"h{h}"] = (df["hora"] == h).astype(float)
    beta, *_ = np.linalg.lstsq(X.values, df["FD"].values, rcond=None)
    b = dict(zip(X.columns, beta))
    p = {"intercept": b["const"], "ghr": b["R"], "ena": b["ena"],
         "peso_mes": {m: b.get(f"m{m}", 0.0) for m in range(1, 13)},
         "peso_hora": {h: b.get(f"h{h}", 0.0) for h in range(24)},
         "peso_weekday": 0.0, "peso_fds": b["fds"]}
    legado = load_config()["modelo"]["hidro_fd"]
    legado = {**legado, "peso_mes": {int(k): v for k, v in legado["peso_mes"].items()},
              "peso_hora": {int(k): v for k, v in legado["peso_hora"].items()}}
    m_novo, m_leg = avaliar(df, p), avaliar(df, legado)
    logger.info(f"base: {df['din_instante'].min():%Y-%m-%d} a {df['din_instante'].max():%Y-%m-%d}, {len(df):,} horas")
    logger.info(f"legado   : MAE {m_leg['mae_mw']:,.0f} MW  viés {m_leg['bias_mw']:+,.0f}  MAPE {m_leg['mape_pct']:.2f}%  R² {m_leg['r2']:.3f}")
    logger.info(f"calibrado: MAE {m_novo['mae_mw']:,.0f} MW  viés {m_novo['bias_mw']:+,.0f}  MAPE {m_novo['mape_pct']:.2f}%  R² {m_novo['r2']:.3f}")
    logger.info(f"           intercept {p['intercept']:,.0f}  ghr {p['ghr']:.3f}  ena {p['ena']:.3f}  fds {p['peso_fds']:+,.0f}")
    if salvar:
        out = {**p, "peso_mes": {str(k): v for k, v in p["peso_mes"].items()},
               "peso_hora": {str(k): v for k, v in p["peso_hora"].items()},
               "meta": {"periodo": f"{df['din_instante'].min():%Y-%m-%d} a {df['din_instante'].max():%Y-%m-%d}",
                        "metricas": m_novo, "metricas_legado": m_leg}}
        with open(params_dir() / "hidro_fd.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        parametros(recarregar=True)
    return {**p, "metricas": m_novo, "metricas_legado": m_leg}
