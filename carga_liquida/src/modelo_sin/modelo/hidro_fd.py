"""Geração hidrelétrica fio d'água (FD) por regressão linear múltipla.

    FD = intercept + ghr[hora]·R + r2·(R/1000)² + ena·ENA + peso_mes[mês] + peso_hora[hora] + peso_dia(DU|FDS)

R = geração das UHEs de reservatório (MW), ENA = ENA armazenável do SIN (MWmed). A resposta da FD ao R
varia com a hora (dFD/dR ≈ 0,54 ao meio-dia, 0,27 na ponta) e satura em R alto (cascata no limite):
`ghr` por hora e o termo quadrático capturam isso. Os parâmetros padrão (config.modelo.hidro_fd) são os
do mini_dessem (ghr único, sem R²); `calibrar()` reestima tudo por OLS nos dados observados e grava em
params_dir/hidro_fd.json, que passa a ter precedência.

A regressão é a FD "natural" (vazão): é treinada FORA das horas de sobra (corte energético > 0 no COFF; antes do COFF,
CMO < 10 com R < 17 GW). Na sobra o operador verte água turbinável e a FD fica abaixo disso — em média
`reducao_sobra_mw` (~1,8 GW) nas horas com corte > 1 GW; a redução cresce com a sobra e satura (~0,5 GW quando o corte
é < 0,5 GW, ~2,2 GW quando é 4–8 GW; a FD absorve 73 % da sobra pequena e 10 % da grande). O despacho usa isso como
recurso: R no mínimo e base térmica no piso -> reduz a FD até `reducao_sobra_mw` -> só então corta renovável
(config.modelo.fd_reducao_sobra). Na escassez não há efeito mensurável (coeficiente −0,2 GW, n.s.).
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
        ghr = float(raw["ghr"])
        _PARAMS = {"intercept": float(raw["intercept"]), "ghr": ghr, "ena": float(raw["ena"]),
                   "reducao_sobra_mw": float(raw.get("reducao_sobra_mw", 0.0)),
                   "ghr_hora": {int(k): float(v) for k, v in raw.get("ghr_hora", {h: ghr for h in range(24)}).items()},
                   "r2": float(raw.get("r2", 0.0)),
                   "peso_mes": {int(k): float(v) for k, v in raw["peso_mes"].items()},
                   "peso_hora": {int(k): float(v) for k, v in raw["peso_hora"].items()},
                   "peso_weekday": float(raw["peso_weekday"]), "peso_fds": float(raw["peso_fds"]), "origem": origem}
        logger.info(f"parâmetros hidro FD: {origem}")
    return _PARAMS


def calcular_fd(mes: int, hora: int, is_weekday: bool, R: float, ena: float, p: dict | None = None) -> float:
    p = p or parametros()
    return (p["intercept"] + p["ghr_hora"][hora] * R + p["r2"] * (R / 1000.0) ** 2 + p["ena"] * ena
            + p["peso_mes"][mes] + p["peso_hora"][hora] + (p["peso_weekday"] if is_weekday else p["peso_fds"]))


def base_observada() -> pd.DataFrame:
    """Horas com FD, R (histórico), ENA armazenável do dia e o rótulo de sobra: `ene` (corte energético observado, MW;
    NaN antes do COFF) e `sobra` (ene > 0; antes do COFF, CMO < 10 com R < 17 GW)."""
    h = cl.carregar_historico()[["din_instante", "FD", "R", "mes", "hora"]].copy()
    ena = ons.carregar_ena()[["ena_data", "ena_armazenavel_mwmed"]].rename(columns={"ena_armazenavel_mwmed": "ena"})
    h["ena_data"] = h["din_instante"].dt.normalize()
    df = h.merge(ena, on="ena_data", how="inner").dropna(subset=["FD", "R", "ena"])
    df["is_weekday"] = df["din_instante"].dt.date.map(feriados.tipo_dia) == "DU"
    try:
        c = ons.carregar_curtailment()[["din_instante", "curtailment_ene_mw"]].rename(columns={"curtailment_ene_mw": "ene"})
        df = df.merge(c, on="din_instante", how="left")
    except FileNotFoundError:
        df["ene"] = np.nan
    cmo = ons.carregar_cmo()
    cmo["din_instante"] = cmo["din_instante"].dt.floor("h")
    df = df.merge(cmo.groupby("din_instante", as_index=False)["val_cmo"].mean(), on="din_instante", how="left")
    df["sobra"] = np.where(df["ene"].notna(), df["ene"] > 0, (df["val_cmo"] < 10) & (df["R"] < 17000))
    return df.reset_index(drop=True)


def avaliar(df: pd.DataFrame, p: dict) -> dict:
    ghr_h = p.get("ghr_hora") or {h: p["ghr"] for h in range(24)}
    fd_hat = (p["intercept"] + df["hora"].map(ghr_h) * df["R"] + p.get("r2", 0.0) * (df["R"] / 1000.0) ** 2
              + p["ena"] * df["ena"] + df["mes"].map(p["peso_mes"])
              + df["hora"].map(p["peso_hora"]) + np.where(df["is_weekday"], p["peso_weekday"], p["peso_fds"]))
    erro = fd_hat - df["FD"]
    return {"mae_mw": float(erro.abs().mean()), "bias_mw": float(erro.mean()),
            "mape_pct": float((erro.abs() / df["FD"]).mean() * 100),
            "r2": float(1 - (erro ** 2).sum() / ((df["FD"] - df["FD"].mean()) ** 2).sum()), "n": int(len(df))}


def _matriz(df: pd.DataFrame) -> pd.DataFrame:
    X = pd.DataFrame({"const": 1.0, "ena": df["ena"], "fds": (~df["is_weekday"]).astype(float), "Rq": (df["R"] / 1000.0) ** 2})
    for h in range(24):
        X[f"R{h}"] = df["R"] * (df["hora"] == h)
    for m in range(1, 12):
        X[f"m{m}"] = (df["mes"] == m).astype(float)
    for h in range(23):
        X[f"h{h}"] = (df["hora"] == h).astype(float)
    return X


def calibrar(salvar: bool = True) -> dict:
    """OLS com R por hora (24 inclinações), R², ENA, dummies de mês (ref. dezembro), hora (ref. 23h) e FDS, treinada
    fora das horas de sobra; `reducao_sobra_mw` = FD média abaixo da regressão nas horas com corte energético > 1 GW."""
    todos = base_observada()
    df = todos[~todos["sobra"]].reset_index(drop=True)
    X = _matriz(df)
    beta, *_ = np.linalg.lstsq(X.values, df["FD"].values, rcond=None)
    b = dict(zip(X.columns, beta))
    ghr_hora = {h: b[f"R{h}"] for h in range(24)}
    p = {"intercept": b["const"], "ghr": float(np.mean(list(ghr_hora.values()))), "ghr_hora": ghr_hora, "r2": b["Rq"], "ena": b["ena"],
         "peso_mes": {m: b.get(f"m{m}", 0.0) for m in range(1, 13)},
         "peso_hora": {h: b.get(f"h{h}", 0.0) for h in range(24)},
         "peso_weekday": 0.0, "peso_fds": b["fds"]}
    corte = todos[todos["ene"] > 1000]
    red = float((_matriz(corte).values @ beta - corte["FD"].values).mean()) if len(corte) else 0.0
    p["reducao_sobra_mw"] = max(red, 0.0)
    logger.info(f"treino fora da sobra: {len(df):,} de {len(todos):,} horas ({100 * todos['sobra'].mean():.1f}% em sobra); "
                f"redução da FD nas {len(corte):,} horas com corte > 1 GW: {red:,.0f} MW")
    legado = load_config()["modelo"]["hidro_fd"]
    legado = {**legado, "peso_mes": {int(k): v for k, v in legado["peso_mes"].items()},
              "peso_hora": {int(k): v for k, v in legado["peso_hora"].items()}}
    m_novo, m_leg = avaliar(df, p), avaliar(df, legado)
    logger.info(f"base: {df['din_instante'].min():%Y-%m-%d} a {df['din_instante'].max():%Y-%m-%d}, {len(df):,} horas")
    logger.info(f"legado   : MAE {m_leg['mae_mw']:,.0f} MW  viés {m_leg['bias_mw']:+,.0f}  MAPE {m_leg['mape_pct']:.2f}%  R² {m_leg['r2']:.3f}")
    logger.info(f"calibrado: MAE {m_novo['mae_mw']:,.0f} MW  viés {m_novo['bias_mw']:+,.0f}  MAPE {m_novo['mape_pct']:.2f}%  R² {m_novo['r2']:.3f}")
    logger.info(f"           intercept {p['intercept']:,.0f}  ghr médio {p['ghr']:.3f} (meio-dia {p['ghr_hora'][12]:.2f}, 19h {p['ghr_hora'][19]:.2f})  "
                f"R² {p['r2']:+.1f} MW/GW²  ena {p['ena']:.3f}  fds {p['peso_fds']:+,.0f}")
    if salvar:
        out = {**p, "peso_mes": {str(k): v for k, v in p["peso_mes"].items()},
               "ghr_hora": {str(k): v for k, v in p["ghr_hora"].items()},
               "peso_hora": {str(k): v for k, v in p["peso_hora"].items()},
               "meta": {"periodo": f"{df['din_instante'].min():%Y-%m-%d} a {df['din_instante'].max():%Y-%m-%d}",
                        "metricas": m_novo, "metricas_legado": m_leg}}
        with open(params_dir() / "hidro_fd.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        parametros(recarregar=True)
    return {**p, "metricas": m_novo, "metricas_legado": m_leg}
