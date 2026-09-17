"""Testes de coerência dos perfis diários simulados (eólica e carga) contra o observado.

    python run.py validar --perfis

Eólica: gera, com o sampler treinado, os mesmos meses observados (média do mês = observada, 6 cenários) e compara nove
estatísticas que a validação hora a hora não vê: forma média do dia, forma condicional ao nível do dia, rampas,
salto na meia-noite, limites, autocorrelação intradiária, persistência de D, distribuição de D e variância total.
Foi isto que mostrou que o nível do dia é aditivo (amplitude do perfil por tercil de D) e que o degrau de D à
meia-noite e a demédia por dia-calendário criavam saltos 5x maiores que o observado.
Carga: compara a última simulação (determinística) com o balanço: forma por tipo de dia, std do nível diário, nível por
classe de dia, nível vs temperatura do dia, forma por tercil de temperatura, rampas, meia-noite e o resíduo. Foi isto
que mostrou que a temperatura não movia o nível do dia (Σ perfil = 24 renormalizado no dia) e que sábado, domingo e
feriado tinham o mesmo nível.
Solar: centralizada (potencial COFF) e distribuída (MMGD) vs último cenário: forma por mês (pico, horas de sol, hora do
pico), nível diário, forma condicional ao nível, rampas, correlação com a eólica, limites. Foi isto que mostrou que o
expoente 1,5 do legado dava pico +10 % e dia 1 h mais curto, e que descartar os zeros noturnos no treino (`mw > 0`)
deixava um artefato do ONS (2024-11-10) virar 1,0 de geração noturna no perfil de novembro.
Hidro FD: resíduo da regressão (sim − obs) por ano, persistência diária, nível de FD e ESTADO do sistema (hidro no mínimo,
corte energético, CMO). Mostrou que o erro não é hidrologia (ENA por subsistema em vez do SIN: MAE 1.766 → 1.718 in-sample
e 2.228 → 2.277 fora da amostra; viés por ano igual), e sim despacho: em sobra o ONS reduz a FD (~1 GW abaixo da
regressão), em escassez a espreme (+0,4–0,7 GW); FD > 33 GW fica 1,5 GW abaixo.
"""
import calendar

import numpy as np
import pandas as pd

from ..config import get_logger, load_config
from ..dados import ons, temperatura
from ..modelo import feriados, simulacao
from ..observado import carga_liquida as cl
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


def testar_carga(inicio: str = "2024-01-01") -> pd.DataFrame:
    """Carga observada (balanço + exportação) vs último cenário simulado, mesma bateria de nível/forma."""
    bal = ons.carregar_balanco()
    bal = bal[bal["din_instante"] >= inicio]
    o = pd.DataFrame({"din_instante": bal["din_instante"], "y": bal["val_carga"] + bal["val_intercambio"].fillna(0.0)})
    sim = simulacao.carregar_resultados()
    s = sim[(sim["simulacao"] == 1) & (sim["din_instante"] >= inicio)][["din_instante", "val_carga"]].rename(columns={"val_carga": "y"})
    t = temperatura.carregar_temperatura().rename(columns={"timestamp": "din_instante"})[["din_instante", "temp_brasil_c"]]

    def prep(d):
        d = d.merge(t, on="din_instante", how="left").sort_values("din_instante").copy()
        d["dia"], d["hora"] = d["din_instante"].dt.normalize(), d["din_instante"].dt.hour
        d["ym"], d["dow"] = d["din_instante"].dt.to_period("M"), d["din_instante"].dt.dayofweek
        d["tipo"] = d["dia"].dt.date.map(feriados.tipo_dia)
        d["classe"] = d["dia"].dt.date.map(feriados.classe_dia)
        d["dm"], d["mm"] = d.groupby("dia")["y"].transform("mean"), d.groupby("ym")["y"].transform("mean")
        d["D"], d["f"], d["tm"] = d["dm"] / d["mm"], d["y"] / d["dm"], d.groupby("dia")["temp_brasil_c"].transform("mean")
        return d

    o, s = prep(o), prep(s)
    comum = set(o["dia"]) & set(s["dia"])
    o, s = o[o["dia"].isin(comum)], s[s["dia"].isin(comum)]
    linhas = []

    def add(teste, nome, lab, v):
        linhas.append({"teste": teste, "estatistica": nome, "obs": v if lab == "obs" else np.nan, "sim": v if lab == "sim" else np.nan})

    for tp in ("DU", "FDS"):
        add("1 forma média do dia", f"MAE por hora, {tp}", "sim",
            float(np.abs(o[o["tipo"] == tp].groupby("hora")["f"].mean() - s[s["tipo"] == tp].groupby("hora")["f"].mean()).mean()))
    for lab, d in (("obs", o), ("sim", s)):
        g = d.groupby("dia").agg(D=("D", "first"), tipo=("tipo", "first"), classe=("classe", "first"), tm=("tm", "first"), ym=("ym", "first"))
        for tp in ("DU", "FDS"):
            x = g[g["tipo"] == tp]["D"]
            for nome, v in (("std", x.std()), ("P10", x.quantile(.1)), ("P90", x.quantile(.9))):
                add("2 nível diário D", f"{nome}, {tp}", lab, v)
        for c in feriados.CLASSES:
            add("3 nível por classe de dia", c, lab, g[g["classe"] == c]["D"].mean())
        du = g[g["classe"].isin(["DU", "SEG"])].copy()
        du["dt"] = du["tm"] - du.groupby("ym")["tm"].transform("mean")
        du = du.dropna()
        add("4 nível vs temperatura (dias úteis)", "corr", lab, du["dt"].corr(du["D"]))
        add("4 nível vs temperatura (dias úteis)", "% por °C", lab, 100 * np.polyfit(du["dt"], du["D"], 1)[0])
        dd = d[d["tipo"] == "DU"].copy()
        dd["dt"] = dd["tm"] - dd.groupby("ym")["tm"].transform("mean")
        gd = dd.groupby("dia").agg(dt=("dt", "first"), amp=("f", lambda x: x.max() / x.min())).dropna()
        gd["terc"] = pd.qcut(gd["dt"], 3, labels=["frio", "médio", "quente"])
        for terc, v in gd.groupby("terc", observed=True)["amp"].median().items():
            add("5 amplitude do perfil por tercil de temperatura", terc, lab, v)
        r = (d.groupby("dia")["y"].diff() / d["mm"]).dropna()
        add("6 rampas (fração da média do mês)", "std", lab, r.std())
        add("6 rampas (fração da média do mês)", "P99", lab, r.quantile(.99))
        dy = (d["y"] - d["y"].shift(1)).abs() / d["mm"]
        add("7 salto entre horas vizinhas", "meia-noite", lab, dy[d["hora"] == 0].median())
        add("7 salto entre horas vizinhas", "outras horas", lab, dy[d["hora"] != 0].median())
    m = o[["din_instante", "y", "mm"]].merge(s[["din_instante", "y"]], on="din_instante", suffixes=("_o", "_s"))
    e = ((m["y_s"] - m["y_o"]) / m["mm"]).values
    add("8 resíduo horário sim − obs", "std", "sim", e.std())
    add("8 resíduo horário sim − obs", "autocorr 1 h", "sim", np.corrcoef(e[:-1], e[1:])[0, 1])
    add("8 resíduo horário sim − obs", "autocorr 24 h", "sim", np.corrcoef(e[:-24], e[24:])[0, 1])
    add("8 resíduo horário sim − obs", "MAPE %", "sim", 100 * np.abs(m["y_s"] - m["y_o"]).mean() / m["y_o"].mean())
    out = pd.DataFrame(linhas).groupby(["teste", "estatistica"], sort=False).agg(obs=("obs", "max"), sim=("sim", "max")).reset_index()
    for r in out.itertuples():
        logger.info(f"  {r.teste:<46} {r.estatistica:<16} obs {r.obs:9.3f}   sim {r.sim:9.3f}")
    return out


def testar_solar(inicio: str = "2024-04-01") -> pd.DataFrame:
    """Solar centralizada (potencial COFF) e distribuída (MMGD) observadas vs último cenário simulado."""
    tipo = load_config()["carga_liquida"]["tipo_usina_solar"]
    ger = cl.carregar_geracao_por_tipo()
    sim = simulacao.carregar_resultados()
    sim = sim[sim["simulacao"] == 1]
    w = ons.carregar_coff_horario("eolica")[["din_instante", "potencial_mw"]].rename(columns={"potencial_mw": "y"})
    fontes = {
        "centralizada": (ons.carregar_coff_horario("solar")[["din_instante", "potencial_mw"]].rename(columns={"potencial_mw": "y"}),
                         sim[["din_instante", "val_gersolar_cent"]].rename(columns={"val_gersolar_cent": "y"})),
        "distribuida": (ger[["din_instante", f"{tipo} - MMGD"]].rename(columns={f"{tipo} - MMGD": "y"}).dropna(),
                        sim[["din_instante", "val_gersolar_dist"]].rename(columns={"val_gersolar_dist": "y"})),
    }

    def prep(d):
        d = d[d["din_instante"] >= inicio].sort_values("din_instante").copy()
        d["dia"], d["hora"], d["mes"] = d["din_instante"].dt.normalize(), d["din_instante"].dt.hour, d["din_instante"].dt.month
        d["ym"] = d["din_instante"].dt.to_period("M")
        d["dm"], d["mm"] = d.groupby("dia")["y"].transform("mean"), d.groupby("ym")["y"].transform("mean")
        d["D"], d["f"] = d["dm"] / d["mm"], d["y"] / d["dm"].replace(0, np.nan)
        return d

    Dw = {"obs": prep(w).groupby("dia")["D"].first().rename("Dw"),                      # eólica observada para a solar observada
          "sim": prep(sim[["din_instante", "val_gereolica"]].rename(columns={"val_gereolica": "y"})).groupby("dia")["D"].first().rename("Dw")}
    linhas = []

    def add(fonte, teste, nome, lab, v):
        linhas.append({"fonte": fonte, "teste": teste, "estatistica": nome, "obs": v if lab == "obs" else np.nan, "sim": v if lab == "sim" else np.nan})

    for fonte, (o, s) in fontes.items():
        o, s = prep(o), prep(s)
        comum = set(o["dia"]) & set(s["dia"])
        o, s = o[o["dia"].isin(comum)], s[s["dia"].isin(comum)]
        po, ps = o.groupby(["mes", "hora"])["f"].mean().unstack(), s.groupby(["mes", "hora"])["f"].mean().unstack()
        add(fonte, "1 forma média do dia", "MAE por hora (média dos meses)", "sim", float(np.abs(po - ps).mean().mean()))
        for lab, pp in (("obs", po), ("sim", ps)):
            add(fonte, "1 forma média do dia", "pico (fração da média do dia), média dos meses", lab, float(pp.max(axis=1).mean()))
            add(fonte, "1 forma média do dia", "horas > 5 % do pico, média dos meses", lab, float((pp > 0.05 * pp.max(axis=1).values[:, None]).sum(axis=1).mean()))
        for lab, d in (("obs", o), ("sim", s)):
            D = d.groupby("dia")["D"].first()
            for nome, v in (("std", D.std()), ("P10", D.quantile(.1)), ("P90", D.quantile(.9))):
                add(fonte, "2 nível diário D", nome, lab, v)
            add(fonte, "2 nível diário D", "autocorr lag 1", lab, D.autocorr(1) if D.std() > 1e-9 else 0.0)
            g = d[d["hora"].between(7, 16)].groupby("dia").agg(D=("D", "first"), pico=("f", "max"))
            g["terc"] = pd.qcut(g["D"].rank(method="first"), 3, labels=["nublado", "médio", "limpo"])
            for terc, v in g.groupby("terc", observed=True)["pico"].median().items():
                add(fonte, "3 pico por tercil do nível", terc, lab, v)
            r = (d.groupby("dia")["y"].diff() / d["mm"]).dropna()
            add(fonte, "4 rampas (fração da média do mês)", "std", lab, r.std())
            add(fonte, "4 rampas (fração da média do mês)", "P99", lab, r.quantile(.99))
            pm = d.groupby(["mes", "hora"])["f"].transform("mean")
            z = (d["f"] - pm)[d["hora"].between(7, 16)]
            add(fonte, "5 resíduo intradiário (horas de sol)", "std", lab, z.std())
            j = D.reset_index().merge(Dw[lab].reset_index(), on="dia")                # sim x sim: mesmo cenário
            add(fonte, "6 correlação do nível com a eólica", "corr", lab, j["D"].corr(j["Dw"]) if j["D"].std() > 1e-9 else 0.0)
            add(fonte, "7 limites", "máx MW", lab, d["y"].max())
            add(fonte, "7 limites", "% horas noturnas > 1 MW", lab, 100 * (d[d["hora"].isin([22, 23, 0, 1, 2, 3, 4])]["y"] > 1).mean())
    out = pd.DataFrame(linhas).groupby(["fonte", "teste", "estatistica"], sort=False).agg(obs=("obs", "max"), sim=("sim", "max")).reset_index()
    for r in out.itertuples():
        logger.info(f"  {r.fonte:<13} {r.teste:<38} {r.estatistica:<44} obs {r.obs:10.3f}   sim {r.sim:10.3f}")
    return out


def testar_hidro_fd(inicio: str = "2022-01-01") -> pd.DataFrame:
    """Resíduo da regressão hidro FD na última simulação (média dos cenários − observado), por estado do sistema."""
    from . import comparar
    df = comparar.montar_comparacao()
    df = df[df["din_instante"] >= inicio].copy()
    df["ano"], df["dia"] = df["din_instante"].dt.year, df["din_instante"].dt.normalize()
    e = df["erro_hidro_fd"]
    linhas = []

    def add(teste, nome, v, n=np.nan):
        linhas.append({"teste": teste, "estatistica": nome, "valor": v, "n": n})

    add("1 global", "MAE", e.abs().mean(), len(e)); add("1 global", "viés", e.mean(), len(e))
    for a, v in e.groupby(df["ano"]).mean().items():
        add("2 viés por ano", str(a), v, int((df["ano"] == a).sum()))
    d = e.groupby(df["dia"]).mean().dropna()
    for k in (1, 7, 30):
        add("3 persistência do erro diário", f"autocorr {k} d", d.autocorr(k))
    add("3 persistência do erro diário", "std", d.std())
    for terc, v in e.groupby(pd.qcut(df["FD"], 3, labels=["baixo", "médio", "alto"]), observed=True).mean().items():
        add("4 viés por tercil de FD observada", terc, v)
    condicoes = [("R obs < 15 GW (hidro no mínimo)", df["R"] < 15000), ("R obs > 35 GW", df["R"] > 35000),
                 ("ENE obs > 1 GW", df["curtailment_ene_obs"] > 1000), ("ENE obs = 0", df["curtailment_ene_obs"] == 0),
                 ("CMO obs < 10", df["cmo_obs"] < 10), ("CMO obs > 200", df["cmo_obs"] > 200), ("FD obs > 33 GW", df["FD"] > 33000)]
    for nome, m in condicoes:
        add("5 viés por estado do sistema", nome, e[m].mean(), int(m.sum()))
    out = pd.DataFrame(linhas)
    for r in out.itertuples():
        logger.info(f"  {r.teste:<34} {r.estatistica:<32} {r.valor:9.3f}" + (f"   n={int(r.n)}" if pd.notna(r.n) else ""))
    return out
