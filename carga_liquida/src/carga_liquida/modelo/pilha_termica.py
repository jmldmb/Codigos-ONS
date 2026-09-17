"""Pilha térmica (merit order) SEMANAL montada dos dados abertos do ONS.

    CVU por usina   : dataset `cvu` (semana operativa sábado-sexta, PMO + revisões; usa a revisão mais alta da semana)
    disponibilidade : capacidade flexível da usina na semana = disponibilidade operacional DECLARADA (dataset
                      disponibilidade_usina_ho, média da semana, casada por CEG) − inflexibilidade média da semana anterior
                      (dataset termica_despacho). Sem proxy: é a mesma informação que o operador usa no PMO. Nas projeções
                      vale a última disponibilidade observada (premissa de persistência, editável).
                      Fallback (config pilha_fonte_capacidade: geracao): máximo gerado nas K semanas anteriores − inflex.
    nuclear         : inflexível por definição (CEG 'UTN'), fora da pilha
    subsistema      : id_subsistema da usina — a térmica é despachada contra o preço do SEU subsistema
    chave           : cod_usinaplanejamento (presente nos dois datasets)

Resultado por semana: DataFrame ordenado por CVU com `cvu`, `capacidade` (MW flexíveis da usina), `potencia`
(acumulada), `subsistema`, `cod`, `nom_usina`. `pilha(ano, mes)` devolve a última semana do mês (compatibilidade).
"""
import pandas as pd

from ..config import get_logger, load_config, output_dir
from ..dados import ons

logger = get_logger("pilha")
_CACHE = None
ARQ = "pilhas_termicas.csv"


def semana_operativa(ts: pd.Series) -> pd.Series:
    """Sábado que inicia a semana operativa de cada instante."""
    return (ts - pd.to_timedelta((ts.dt.weekday + 2) % 7, unit="D")).dt.normalize()


def _geracao_semanal() -> pd.DataFrame:
    """Por (semana, cod): gmax = máximo da geração verificada; inflex = média da inflexibilidade; subsistema; nuclear."""
    partes = []
    for df in ons.iterar_termica_despacho(["val_verifgeracao", "val_verifinflexibilidade"],
                                          colunas_extra=["cod_usinaplanejamento", "id_subsistema", "ceg"]):
        df = df.dropna(subset=["cod_usinaplanejamento"])
        df["semana"] = semana_operativa(df["din_instante"])
        g = df.groupby(["semana", df["cod_usinaplanejamento"].astype(int).rename("cod")]).agg(
            gmax=("val_verifgeracao", "max"), inflex=("val_verifinflexibilidade", "mean"), subsistema=("id_subsistema", "first"),
            ceg=("ceg", "first"), nuclear=("ceg", lambda s: bool(s.astype(str).str.startswith("UTN").any())))
        partes.append(g)
    return pd.concat(partes).groupby(level=[0, 1]).agg(gmax=("gmax", "max"), inflex=("inflex", "mean"), subsistema=("subsistema", "first"),
                                                        ceg=("ceg", "first"), nuclear=("nuclear", "max")).reset_index()


def _disponibilidade_geracao(ger: pd.DataFrame, semana: pd.Timestamp, k: int) -> pd.DataFrame:
    """Fallback: capacidade flexível = max(gmax) − mean(inflex) nas k semanas anteriores (exclui nuclear)."""
    jan = ger[(ger["semana"] < semana) & (ger["semana"] >= semana - pd.Timedelta(weeks=k)) & ~ger["nuclear"].astype(bool)]
    d = jan.groupby("cod").agg(gmax=("gmax", "max"), inflex=("inflex", "mean"), subsistema=("subsistema", "last"))
    d["capacidade"] = (d["gmax"] - d["inflex"]).clip(lower=0)
    return d


def _disponibilidade_declarada(ger: pd.DataFrame, disp: pd.DataFrame, semana: pd.Timestamp) -> pd.DataFrame:
    """Capacidade flexível = disponibilidade operacional declarada da semana (ou a última anterior disponível)
    − inflexibilidade média da semana anterior; casada por CEG; exclui nuclear."""
    ult = ger[(ger["semana"] < semana) & ~ger["nuclear"].astype(bool)].sort_values("semana").groupby("cod").tail(1).set_index("cod")
    d_ok = disp[disp["semana"] <= semana]
    if d_ok.empty or ult.empty:
        return pd.DataFrame(columns=["capacidade", "subsistema"])
    # última declaração de cada usina até a semana (usinas ausentes numa semana herdam a anterior)
    d = d_ok.sort_values("semana").groupby("ceg")["disp_operacional_mw"].last()
    ult["disp"] = ult["ceg"].map(d)
    ult = ult.dropna(subset=["disp"])
    ult["capacidade"] = (ult["disp"] - ult["inflex"]).clip(lower=0)
    return ult[["capacidade", "subsistema"]]


def montar_todas(rebuild: bool = False) -> dict[pd.Timestamp, pd.DataFrame]:
    """Pilha de cada semana operativa com CVU. Cache em memória e em Output/modelo/pilhas_termicas.csv
    (lido quando existe; `python run.py treinar pilha` reconstrói dos brutos, ~25 s)."""
    global _CACHE
    if _CACHE is not None and not rebuild:
        return _CACHE
    csv = output_dir("modelo") / ARQ
    if csv.exists() and not rebuild:
        df = pd.read_csv(csv, parse_dates=["semana"])
        _CACHE = {s: g.drop(columns=["semana"]).reset_index(drop=True) for s, g in df.groupby("semana")}
        logger.info(f"pilhas térmicas: {len(_CACHE)} semanas lidas de {csv.name}")
        return _CACHE
    cfg = load_config()["modelo"]
    cvu = ons.carregar_cvu()
    ger = _geracao_semanal()
    fonte = cfg.get("pilha_fonte_capacidade", "disponibilidade")
    disp = ons.carregar_disponibilidade_termica() if fonte == "disponibilidade" else None
    k = cfg["pilha_disponibilidade_semanas"]
    pilhas, linhas = {}, []
    for semana, g in cvu.groupby("dat_iniciosemana"):
        ultima = g.sort_values("num_revisao").groupby("cod_usinaplanejamento").tail(1)
        jan = _disponibilidade_declarada(ger, disp, semana) if disp is not None else _disponibilidade_geracao(ger, semana, k)
        if jan.empty:
            continue
        p = ultima.merge(jan[["capacidade", "subsistema"]], left_on="cod_usinaplanejamento", right_index=True, how="inner")
        p = p[(p["val_cvu"] > 0) & (p["capacidade"] >= cfg["pilha_min_flex_mw"])].sort_values(["val_cvu", "capacidade"])
        if p.empty:
            continue
        pilha = pd.DataFrame({"cvu": p["val_cvu"].values, "capacidade": p["capacidade"].values,
                              "potencia": p["capacidade"].cumsum().values, "subsistema": p["subsistema"].values,
                              "cod": p["cod_usinaplanejamento"].values, "nom_usina": p["nom_usina"].values})
        pilhas[semana] = pilha
        linhas.append(pilha.assign(semana=semana))
    if not pilhas:
        raise FileNotFoundError("Sem dados para montar a pilha térmica (datasets cvu e termica_despacho)")
    pd.concat(linhas, ignore_index=True).to_csv(csv, index=False)
    ult = max(pilhas)
    logger.info(f"pilhas térmicas: {len(pilhas)} semanas ({min(pilhas):%Y-%m-%d} a {ult:%Y-%m-%d}); última: {len(pilhas[ult])} usinas, "
                f"{pilhas[ult]['potencia'].iloc[-1]:,.0f} MW flexíveis, CVU {pilhas[ult]['cvu'].min():.0f}–{pilhas[ult]['cvu'].max():.0f}")
    _CACHE = pilhas
    return pilhas


def pilha_semana(data) -> pd.DataFrame:
    """Pilha da semana operativa de `data`, ou a mais recente anterior (projeções)."""
    pilhas = montar_todas()
    s = semana_operativa(pd.Series([pd.Timestamp(data)])).iloc[0]
    if s not in pilhas:
        anteriores = [k for k in pilhas if k <= s]
        s = max(anteriores) if anteriores else min(pilhas)
    return pilhas[s]


def pilha(ano: int, mes: int) -> pd.DataFrame:
    """Pilha da última semana operativa iniciada no mês (ou a mais recente anterior)."""
    return pilha_semana(pd.Timestamp(ano, mes, 1) + pd.offsets.MonthEnd(0))
