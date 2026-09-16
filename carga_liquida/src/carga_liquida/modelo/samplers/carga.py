"""Sampler de carga v6 (determinístico, sensível à temperatura), como no mini_dessem.

    carga_norm(h) = intercept[tipo_dia, mês, h] + slope[tipo_dia, mês, h] · temp(h)
    perfil(h)     = carga_norm(h) · 24 / Σ carga_norm            (constraint Σ perfil = 24)
    carga(h)      = carga_dia(tipo_dia) · perfil(h)              (média do perfil = 1)

onde carga_dia distribui a média mensal entre dias úteis (DU) e fins de semana/feriados (FDS) pelo
fator FDS/DU do mês e pelo calendário real. temp(h) é a temperatura real hora a hora quando existe
(histórico) ou média mensal + desvio típico da hora (projeção).

Treino: regressão linear por (tipo_dia, mês, hora) da carga normalizada pela média mensal contra a
temperatura; intercepts reescalados para Σ=24 na temperatura típica; depois um ajuste de viés por
(tipo_dia, hora) a partir do backtest in-sample (legado: ajustar_vies_picos_v6), reaplicando o constraint.
"""
import calendar
from datetime import date, datetime

import numpy as np
import pandas as pd
from scipy import stats

from ...config import get_logger, load_config
from ...dados import ons, temperatura
from .. import feriados
from ._base import carregar_json, janela_treino, salvar_json

logger = get_logger("sampler.carga")
NOME = "carga_v6"
TIPOS = ("DU", "FDS")


# ----------------------------------------------------------------------------- dados de treino
def base_treino() -> pd.DataFrame:
    """Horas com carga (balanço SIN), temperatura e tipo de dia; carga normalizada pela média do mês."""
    bal = janela_treino(ons.carregar_balanco())
    if load_config()["modelo"].get("carga_inclui_intercambio", True):
        bal = bal.assign(val_carga=bal["val_carga"] + bal["val_intercambio"].fillna(0.0))
    bal = bal[["din_instante", "val_carga"]].rename(columns={"val_carga": "carga_mw"})
    temp = temperatura.carregar_temperatura().rename(columns={"timestamp": "din_instante"})
    df = bal.merge(temp[["din_instante", "temp_brasil_c"]], on="din_instante", how="inner").dropna()
    df["ano"], df["mes"], df["dia"], df["hora"] = (df["din_instante"].dt.year, df["din_instante"].dt.month,
                                                   df["din_instante"].dt.day, df["din_instante"].dt.hour)
    df["data"] = df["din_instante"].dt.date
    df["tipo_dia"] = df["data"].map(feriados.tipo_dia)
    df["carga_media_mes"] = df.groupby(["ano", "mes"])["carga_mw"].transform("mean")
    df["carga_norm"] = df["carga_mw"] / df["carga_media_mes"]
    return df


# ----------------------------------------------------------------------------- treino
def _regressoes(df: pd.DataFrame, min_obs: int) -> dict:
    reg = {}
    for tipo in TIPOS:
        d = df[df["tipo_dia"] == tipo]
        for mes in range(1, 13):
            for hora in range(24):
                g = d[(d["mes"] == mes) & (d["hora"] == hora)]
                if len(g) >= min_obs and g["temp_brasil_c"].std() > 0:
                    r = stats.linregress(g["temp_brasil_c"], g["carga_norm"])
                    reg[(tipo, mes, hora)] = {"intercept": float(r.intercept), "slope": float(r.slope),
                                              "r2": float(r.rvalue ** 2), "n": int(len(g))}
                else:
                    reg[(tipo, mes, hora)] = {"intercept": float(g["carga_norm"].mean()) if len(g) else 1.0,
                                              "slope": 0.0, "r2": 0.0, "n": int(len(g))}
    return reg


def _perfil_temp(df: pd.DataFrame) -> tuple[dict, dict]:
    """desvio[mes][h] = média da hora − média do mês; temp_ref[mes] = média do mês."""
    temp_ref = df.groupby("mes")["temp_brasil_c"].mean().to_dict()
    por_hora = df.groupby(["mes", "hora"])["temp_brasil_c"].mean()
    desvio = {m: [float(por_hora.get((m, h), temp_ref[m]) - temp_ref[m]) for h in range(24)] for m in temp_ref}
    return desvio, {int(k): float(v) for k, v in temp_ref.items()}


def _aplicar_constraint(reg: dict, desvio: dict, temp_ref: dict) -> dict:
    """Reescala intercepts de cada (tipo, mês) para Σ_h carga_norm(h) = 24 na temperatura típica do mês."""
    for tipo in TIPOS:
        for mes in range(1, 13):
            if mes not in temp_ref:
                continue
            temp_h = [temp_ref[mes] + desvio[mes][h] for h in range(24)]
            soma_slopes = sum(reg[(tipo, mes, h)]["slope"] * temp_h[h] for h in range(24))
            soma_int = sum(reg[(tipo, mes, h)]["intercept"] for h in range(24))
            fator = (24.0 - soma_slopes) / soma_int if soma_int > 0 else 1.0
            for h in range(24):
                reg[(tipo, mes, h)]["intercept"] *= fator
    return reg


def _proporcoes(df: pd.DataFrame) -> dict:
    out = {}
    for mes in range(1, 13):
        d = df[df["mes"] == mes]
        du = d.loc[d["tipo_dia"] == "DU", "carga_mw"].mean()
        fds = d.loc[d["tipo_dia"] == "FDS", "carga_mw"].mean()
        out[mes] = {"DU": 1.0, "FDS": float(fds / du) if du and not np.isnan(fds) else 0.88}
    return out


def _params_para_json(reg, desvio, temp_ref, prop):
    return {"regressoes": {t: {str(m): {str(h): reg[(t, m, h)] for h in range(24)} for m in range(1, 13)} for t in TIPOS},
            "desvio_temp": {str(m): v for m, v in desvio.items()},
            "temp_ref": {str(m): v for m, v in temp_ref.items()},
            "proporcoes": {str(m): v for m, v in prop.items()}}


def _backtest(sampler: "CargaSampler", df: pd.DataFrame) -> pd.DataFrame:
    """Simula cada dia da base com temperatura real e média mensal real; devolve erro por hora."""
    rows = []
    for (ano, mes, dia), g in df.groupby(["ano", "mes", "dia"]):
        if len(g) < 24:
            continue
        temp_h = dict(zip(g["hora"], g["temp_brasil_c"]))
        sim = sampler.gerar_dia(date(int(ano), int(mes), int(dia)), float(g["carga_media_mes"].iloc[0]),
                                float(g["temp_brasil_c"].mean()), temp_h)
        real = g.sort_values("hora")["carga_mw"].values
        rows.append(pd.DataFrame({"ano": ano, "mes": mes, "dia": dia, "hora": range(24), "tipo_dia": g["tipo_dia"].iloc[0],
                                  "real": real, "sim": sim}))
    bt = pd.concat(rows, ignore_index=True)
    bt["erro"] = bt["sim"] - bt["real"]
    bt["erro_pct"] = 100 * bt["erro"] / bt["real"]
    return bt


def _metricas(bt: pd.DataFrame) -> dict:
    return {"mape_pct": float(bt["erro_pct"].abs().mean()), "bias_pct": float(bt["erro_pct"].mean()),
            "r2": float(np.corrcoef(bt["real"], bt["sim"])[0, 1] ** 2),
            "erro_p90_pct": float(100 * (bt["sim"].quantile(0.9) - bt["real"].quantile(0.9)) / bt["real"].quantile(0.9)),
            "n_dias": int(len(bt) // 24)}


def treinar() -> dict:
    cfg = load_config()["modelo"]["treino"]
    df = base_treino()
    logger.info(f"base: {df['din_instante'].min()} a {df['din_instante'].max()}, {len(df):,} horas "
                f"(DU {int((df['tipo_dia'] == 'DU').sum()):,} / FDS {int((df['tipo_dia'] == 'FDS').sum()):,})")
    reg = _regressoes(df, cfg["carga_min_obs_regressao"])
    desvio, temp_ref = _perfil_temp(df)
    reg = _aplicar_constraint(reg, desvio, temp_ref)
    prop = _proporcoes(df)
    r2 = np.mean([v["r2"] for v in reg.values() if v["n"] > 0])
    logger.info(f"regressões: {len(reg)} (R² médio {r2:.3f}); fator FDS/DU médio {np.mean([p['FDS'] for p in prop.values()]):.3f}")

    params = _params_para_json(reg, desvio, temp_ref, prop)
    antes = _metricas(bt := _backtest(CargaSampler(params), df))
    logger.info(f"backtest antes do ajuste de viés: MAPE {antes['mape_pct']:.2f}%  bias {antes['bias_pct']:+.2f}%  R² {antes['r2']:.3f}")

    # ajuste de viés por (tipo_dia, hora): intercept *= 1 - erro_pct/100, depois reaplica constraint
    vies = bt.groupby(["tipo_dia", "hora"])["erro_pct"].mean()
    for (tipo, mes, h), v in reg.items():
        v["intercept"] *= 1 - vies.get((tipo, h), 0.0) / 100
    reg = _aplicar_constraint(reg, desvio, temp_ref)
    params = _params_para_json(reg, desvio, temp_ref, prop)
    depois = _metricas(_backtest(CargaSampler(params), df))
    logger.info(f"backtest após ajuste de viés:    MAPE {depois['mape_pct']:.2f}%  bias {depois['bias_pct']:+.2f}%  "
                f"R² {depois['r2']:.3f}  erro P90 {depois['erro_p90_pct']:+.2f}%")
    params["meta"] = {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}", "n_horas": int(len(df)),
                      "backtest_antes_ajuste": antes, "backtest": depois}
    salvar_json(NOME, params)
    return params


# ----------------------------------------------------------------------------- sampler
class CargaSampler:
    def __init__(self, params: dict | None = None):
        p = params or carregar_json(NOME)
        self.reg = {(t, int(m), int(h)): v for t, meses in p["regressoes"].items() for m, horas in meses.items() for h, v in horas.items()}
        self.desvio = {int(m): v for m, v in p["desvio_temp"].items()}
        self.temp_ref = {int(m): v for m, v in p["temp_ref"].items()}
        self.prop = {int(m): v for m, v in p["proporcoes"].items()}

    def carga_dia(self, d: date, carga_mensal: float, tipo: str) -> float:
        """Média do dia dado o tipo, respeitando a média mensal no calendário real do mês."""
        n = {"DU": 0, "FDS": 0}
        for dia in range(1, calendar.monthrange(d.year, d.month)[1] + 1):
            n[feriados.tipo_dia(date(d.year, d.month, dia))] += 1
        f = self.prop[d.month]
        den = n["DU"] * f["DU"] + n["FDS"] * f["FDS"]
        base = carga_mensal * (n["DU"] + n["FDS"]) / den if den > 0 else carga_mensal
        return base * f[tipo]

    def gerar_dia(self, d: date, carga_mensal: float, temp_media_mensal: float,
                  temp_horaria: dict[int, float] | None = None) -> np.ndarray:
        """24 valores de carga (MW) do dia `d`."""
        if isinstance(d, datetime):
            d = d.date()
        mes, tipo = d.month, feriados.tipo_dia(d)
        if temp_horaria is not None:
            temp_h = np.array([temp_horaria.get(h, temp_media_mensal) for h in range(24)])
        else:
            temp_h = temp_media_mensal + np.array(self.desvio.get(mes, [0.0] * 24))
        norm = np.array([self.reg[(tipo, mes, h)]["intercept"] + self.reg[(tipo, mes, h)]["slope"] * temp_h[h] for h in range(24)])
        perfil = norm * 24 / norm.sum() if norm.sum() > 0 else np.ones(24)
        return self.carga_dia(d, carga_mensal, tipo) * perfil
