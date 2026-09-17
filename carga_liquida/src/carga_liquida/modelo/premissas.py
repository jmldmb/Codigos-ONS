"""Premissas mensais do simulador: uma linha por (ano, mês) com as médias que alimentam os samplers.

Colunas (MW médios; ENA em MWmed):
    carga, eolica, solar_centralizada, solar_distribuida, ena_armazenavel, termica_total,
    termica_flexivel, curtailment_rede_eolica, curtailment_rede_solar, eolica_capacidade, inflexterm, historico (bool)

eolica e solar_centralizada são POTENCIAL (geração + corte); curtailment_rede_* é o corte de rede (CNF/REL) que
se subtrai antes do despacho (o energético o despacho decide). Antes do COFF (2023-10) a eólica é a geração
do balanço, já pós-corte, e o corte de rede é 0.

Anos com dado observado vêm dos brutos (BALANCO_ENERGIA, COFF, geração por usina, ENA, térmica
despacho) — o legado tinha esses números copiados à mão em data.py. Anos sem dado vêm de
config/projecoes.yaml.
"""
import calendar
from datetime import date

import pandas as pd
import yaml

from ..config import ROOT, get_logger, load_config, periodo
from ..dados import ons
from ..observado import carga_liquida as cl

logger = get_logger("premissas")

COLS = ["carga", "eolica", "solar_centralizada", "solar_distribuida", "ena_armazenavel", "termica_total", "termica_flexivel",
        "curtailment_rede_eolica", "curtailment_rede_solar", "eolica_capacidade"]


def _mensal(df: pd.DataFrame, col_tempo: str, cols: dict) -> pd.DataFrame:
    g = df.groupby([df[col_tempo].dt.year.rename("ano"), df[col_tempo].dt.month.rename("mes")])
    return g[list(cols)].mean().rename(columns=cols)


def _mes_completo(ano: int, mes: int, ultimo: pd.Timestamp) -> bool:
    return pd.Timestamp(ano, mes, calendar.monthrange(ano, mes)[1], 23) <= ultimo


def historico() -> pd.DataFrame:
    """Premissas observadas por (ano, mês) — só meses completos no balanço."""
    cfg = load_config()["modelo"]
    bal = ons.carregar_balanco()
    ultimo = bal["din_instante"].max()
    if cfg.get("carga_inclui_intercambio", True):
        bal = bal.assign(val_carga=bal["val_carga"] + bal["val_intercambio"].fillna(0.0))
    out = _mensal(bal, "din_instante", {"val_carga": "carga", "val_gereolica": "eolica_balanco",
                                        "val_gersolar": "solar_balanco", "val_gertermica": "termica_total"})

    # eólica: potencial (geração + corte) do COFF quando existe; antes disso, geração do balanço
    try:
        w = ons.carregar_coff_horario("eolica")
        out = out.join(_mensal(w, "din_instante", {"potencial_mw": "eolica_potencial", "corte_rede_mw": "curtailment_rede_eolica"}))
    except FileNotFoundError:
        out["eolica_potencial"] = out["curtailment_rede_eolica"] = float("nan")
    out["eolica"] = out["eolica_potencial"].fillna(out["eolica_balanco"])

    # solar: centralizada = potencial COFF FV (>= 2024-04) ou geração por usina não-MMGD; distribuída = MMGD
    ger = cl.carregar_geracao_por_tipo()
    tipo_solar = load_config()["carga_liquida"]["tipo_usina_solar"]
    cols = {tipo_solar: "solar_cent_usina"}
    if f"{tipo_solar} - MMGD" in ger.columns:
        cols[f"{tipo_solar} - MMGD"] = "solar_distribuida"
    out = out.join(_mensal(ger.fillna({c: 0.0 for c in cols}), "din_instante", cols))
    try:
        s = ons.carregar_coff_horario("solar")
        out = out.join(_mensal(s, "din_instante", {"potencial_mw": "solar_cent_potencial", "corte_rede_mw": "curtailment_rede_solar"}))
    except FileNotFoundError:
        out["solar_cent_potencial"] = out["curtailment_rede_solar"] = float("nan")
    out["solar_centralizada"] = out["solar_cent_potencial"].fillna(out["solar_cent_usina"])
    if "solar_distribuida" not in out.columns:
        out["solar_distribuida"] = float("nan")
    sem_mmgd = out["solar_distribuida"].isna() | (out["solar_distribuida"] <= 0)
    share = cfg["solar_share_centralizada_default"]
    out.loc[sem_mmgd, "solar_centralizada"] = out.loc[sem_mmgd, "solar_balanco"] * share
    out.loc[sem_mmgd, "solar_distribuida"] = out.loc[sem_mmgd, "solar_balanco"] * (1 - share)

    ena = ons.carregar_ena()
    out = out.join(_mensal(ena, "ena_data", {"ena_armazenavel_mwmed": "ena_armazenavel"}))

    hist = cl.carregar_historico()
    out = out.join(_mensal(hist, "din_instante", {"termica_flexivel": "termica_flexivel"}))

    try:                                                   # teto físico da eólica horária (cadastro ONS)
        cap = ons.carregar_capacidade_mensal("EOLIELÉTRICA")
        out = out.join(pd.Series(cap.values, index=pd.MultiIndex.from_arrays([cap.index.year, cap.index.month], names=["ano", "mes"]),
                                 name="eolica_capacidade"))
    except FileNotFoundError as e:
        logger.warning(str(e))
        out["eolica_capacidade"] = float("nan")

    out[["curtailment_rede_eolica", "curtailment_rede_solar"]] = out[["curtailment_rede_eolica", "curtailment_rede_solar"]].fillna(0.0)
    out = out.reset_index()
    out = out[[_mes_completo(a, m, ultimo) for a, m in zip(out["ano"], out["mes"])]]
    out["historico"] = True
    return out[["ano", "mes", *COLS, "historico"]].reset_index(drop=True)


def projecoes() -> pd.DataFrame:
    """Premissas de config/projecoes.yaml (todos os anos/meses lá presentes)."""
    path = ROOT / load_config()["modelo"]["projecoes"]
    with open(path, encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    chave = {"carga_mwmed": "carga", "eolica_mwmed": "eolica", "solar_centralizada_mwmed": "solar_centralizada",
             "solar_distribuida_mwmed": "solar_distribuida", "ena_armazenavel_mwmed": "ena_armazenavel",
             "termica_total_mwmed": "termica_total", "termica_flexivel_mwmed": "termica_flexivel",
             "curtailment_rede_eolica_mwmed": "curtailment_rede_eolica", "curtailment_rede_solar_mwmed": "curtailment_rede_solar",
             "eolica_capacidade_mw": "eolica_capacidade"}
    rows = {}
    for k, col in chave.items():
        for ano, meses in (proj.get(k) or {}).items():
            for mes, v in meses.items():
                rows.setdefault((int(ano), int(mes)), {})[col] = float(v)
    df = pd.DataFrame([{"ano": a, "mes": m, **v} for (a, m), v in sorted(rows.items())])
    for c in ("termica_flexivel", "curtailment_rede_eolica", "curtailment_rede_solar", "eolica_capacidade"):
        if c not in df.columns:
            df[c] = float("nan")
    df["historico"] = False
    return df[["ano", "mes", *COLS, "historico"]]


def montar(anos=None, meses=None) -> pd.DataFrame:
    """Histórico (prioridade) + projeções, com a coluna `inflexterm` já resolvida conforme config.modelo.inflexterm."""
    cfg = load_config()["modelo"]
    h = historico()
    p = projecoes()
    p = p[~p.set_index(["ano", "mes"]).index.isin(h.set_index(["ano", "mes"]).index)]
    df = pd.concat([h, p], ignore_index=True).sort_values(["ano", "mes"]).reset_index(drop=True)
    if cfg["inflexterm"] == "termica_forcada":
        df["inflexterm"] = df["termica_total"] - df["termica_flexivel"].fillna(0.0)
    else:
        df["inflexterm"] = df["termica_total"]
    proj = ~df["historico"] & df["mes"].isin(cfg["inflexterm_adicional_meses"])
    df.loc[proj, "inflexterm"] += cfg["inflexterm_adicional_mw"]
    # térmica flexível base (premissa exógena): observada no histórico, yaml nas projeções; 0 no modo residual
    if cfg.get("termica_flexivel", "residual") == "exogena":
        sem = ~df["historico"] & df["termica_flexivel"].isna()
        if sem.any():
            logger.warning(f"Projeções sem termica_flexivel_mwmed em projecoes.yaml (base = 0): "
                           f"{[(int(a), int(m)) for a, m in zip(df.loc[sem, 'ano'], df.loc[sem, 'mes'])]}")
        df["termica_flex_base"] = df["termica_flexivel"].fillna(0.0)
    else:
        df["termica_flex_base"] = 0.0
    # curtailment de rede (premissa exógena): observado no histórico, yaml nas projeções (0 se ausente)
    for c in ("curtailment_rede_eolica", "curtailment_rede_solar"):
        sem = ~df["historico"] & df[c].isna()
        if sem.any() and cfg.get("curtailment_rede", True):
            logger.warning(f"Projeções sem {c}_mwmed em projecoes.yaml (corte de rede = 0): "
                           f"{[(int(a), int(m)) for a, m in zip(df.loc[sem, 'ano'], df.loc[sem, 'mes'])]}")
        df[c] = df[c].fillna(0.0) if cfg.get("curtailment_rede", True) else 0.0
    if not cfg.get("eolica_teto_capacidade", True):
        df["eolica_capacidade"] = float("nan")             # NaN = sem teto
    elif (~df["historico"] & df["eolica_capacidade"].isna()).any():
        logger.warning("Projeções sem eolica_capacidade_mw em projecoes.yaml: eólica horária sem teto nesses meses")
    if anos is not None:
        df = df[df["ano"].isin(list(anos))]
    if meses is not None:
        df = df[df["mes"].isin(list(meses))]
    faltando = df[df[["carga", "eolica", "solar_centralizada", "solar_distribuida", "ena_armazenavel", "inflexterm"]].isna().any(axis=1)]
    if not faltando.empty:
        logger.warning(f"Premissas incompletas (serão puladas): {[(int(a), int(m)) for a, m in zip(faltando['ano'], faltando['mes'])]}")
    return df.reset_index(drop=True)
