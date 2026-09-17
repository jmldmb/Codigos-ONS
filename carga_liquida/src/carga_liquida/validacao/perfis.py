"""Testes de coerência dos perfis diários eólicos simulados contra o potencial observado (COFF).

    python run.py validar --perfis

Gera, com o sampler treinado, os mesmos meses observados (média do mês = observada, 6 cenários) e compara nove
estatísticas que a validação hora a hora não vê: forma média do dia, forma condicional ao nível do dia, rampas,
salto na meia-noite, limites, autocorrelação intradiária, persistência de D, distribuição de D e variância total.
Foi isto que mostrou que o nível do dia é aditivo (amplitude do perfil por tercil de D) e que o degrau de D à
meia-noite e a demédia por dia-calendário criavam saltos 5x maiores que o observado.
"""
import calendar

import numpy as np
import pandas as pd

from ..config import get_logger
from ..dados import ons
from ..modelo.samplers.eolica import EolicaSampler

logger = get_logger("perfis")


def _prep(d: pd.DataFrame) -> pd.DataFrame:
    d = d.sort_values(["cen", "din_instante"]).copy()
    d["dia"], d["hora"], d["mes"] = d["din_instante"].dt.normalize(), d["din_instante"].dt.hour, d["din_instante"].dt.month
    d["ym"] = d["din_instante"].dt.to_period("M")
    d["key"] = d["dia"].astype(str) + "_" + d["cen"].astype(str)
    d["dm"] = d.groupby("key")["y"].transform("mean")
    d["mm"] = d.groupby(["ym", "cen"])["y"].transform("mean")
    d["D"], d["f"] = d["dm"] / d["mm"], d["y"] / d["dm"]
    return d


def _simular_como_observado(w: pd.DataFrame, n_cen: int, seed: int) -> pd.DataFrame:
    s_eol, rng, rows = EolicaSampler(), np.random.default_rng(seed), []
    for ym, g in w.groupby(w["din_instante"].dt.to_period("M")):
        n = calendar.monthrange(ym.year, ym.month)[1]
        for cen in range(1, n_cen + 1):
            y = s_eol.gerar_mes(ym.month, float(g["y"].mean()), n, rng)
            rows.append(pd.DataFrame({"din_instante": pd.date_range(ym.start_time, periods=n * 24, freq="h"), "y": y.ravel(), "cen": cen}))
    return pd.concat(rows, ignore_index=True)


def testar_eolica(inicio: str = "2024-01-01", n_cen: int = 6, seed: int = 7) -> pd.DataFrame:
    w = ons.carregar_coff_horario("eolica")
    w = w[w["din_instante"] >= inicio].rename(columns={"potencial_mw": "y"}).assign(cen=0)[["din_instante", "y", "cen"]]
    w, s = _prep(w), _prep(_simular_como_observado(w, n_cen, seed))
    linhas = []

    def add(teste, nome, o, sm):
        linhas.append({"teste": teste, "estatistica": nome, "obs": o, "sim": sm})

    for lab, ms in (("verão", [1, 2, 3]), ("inverno", [7, 8, 9])):
        po, ps = w[w["mes"].isin(ms)].groupby("hora")["f"].mean(), s[s["mes"].isin(ms)].groupby("hora")["f"].mean()
        add("1 forma média do dia", f"MAE por hora, {lab}", 0.0, float(np.abs(po - ps).mean()))
    for lab, d in (("obs", w), ("sim", s)):
        g = d.groupby("key").agg(D=("D", "first"), amp=("f", lambda x: x.max() / max(x.min(), 1e-6)), std=("f", "std"))
        g["terc"] = pd.qcut(g["D"], 3, labels=["baixo", "médio", "alto"])
        for terc, v in g.groupby("terc", observed=True)["amp"].median().items():
            add("2 amplitude do perfil por tercil de D", f"max/min, D {terc}", *((v, np.nan) if lab == "obs" else (np.nan, v)))
        r = (d.groupby("key")["y"].diff() / d["mm"]).dropna()
        for nome, v in (("std", r.std()), ("P99", r.quantile(.99)), ("|Δ| máx do dia (mediana)", r.abs().groupby(d["key"]).max().median())):
            add("3 rampas hora a hora (fração da média do mês)", nome, *((v, np.nan) if lab == "obs" else (np.nan, v)))
        dy = (d["y"] - d.groupby("cen")["y"].shift(1)).abs() / d["mm"]
        for nome, v in (("meia-noite", dy[d["hora"] == 0].median()), ("outras horas", dy[d["hora"] != 0].median())):
            add("4 salto entre horas vizinhas", nome, *((v, np.nan) if lab == "obs" else (np.nan, v)))
        for nome, v in (("zeros %", 100 * (d["y"] <= 0).mean()), ("P99,5 MW", d["y"].quantile(.995)), ("máx MW", d["y"].max()), ("mín MW", d["y"].min())):
            add("5 limites", nome, *((v, np.nan) if lab == "obs" else (np.nan, v)))
        z = (d["f"] - 1).values
        for k in (1, 3, 6):
            add("6 autocorr. intradiária", f"lag {k} h", *((np.corrcoef(z[:-k], z[k:])[0, 1], np.nan) if lab == "obs" else (np.nan, np.corrcoef(z[:-k], z[k:])[0, 1])))
        g = d.groupby("key").agg(D=("D", "first"), t=("din_instante", "first"), c=("cen", "first")).sort_values(["c", "t"])
        for k in (1, 2, 3):
            v = g.groupby("c")["D"].apply(lambda x: x.autocorr(k)).mean()
            add("7 persistência de D", f"lag {k} dia(s)", *((v, np.nan) if lab == "obs" else (np.nan, v)))
        D = g["D"]
        for nome, v in (("std", D.std()), ("P10", D.quantile(.1)), ("P90", D.quantile(.9)), ("P1", D.quantile(.01)), ("P99", D.quantile(.99))):
            add("8 distribuição de D", nome, *((v, np.nan) if lab == "obs" else (np.nan, v)))
        st = (d["y"] / d["mm"]).groupby(d["mes"]).std()
        for m, v in st.items():
            add("9 std horário total / média do mês", f"mês {m}", *((v, np.nan) if lab == "obs" else (np.nan, v)))
    out = pd.DataFrame(linhas).groupby(["teste", "estatistica"], sort=False).agg(obs=("obs", "max"), sim=("sim", "max")).reset_index()
    for r in out.itertuples():
        logger.info(f"  {r.teste:<44} {r.estatistica:<28} obs {r.obs:10.3f}   sim {r.sim:10.3f}")
    return out
