"""Pilha térmica (merit order) SEMANAL montada dos dados abertos do ONS.

    CVU por usina   : dataset `cvu` (semana operativa sábado-sexta, PMO + revisões; usa a revisão mais alta da semana)
    capacidade      : capacidade flexível = máximo da geração verificada − inflexibilidade média da usina, na janela de
                      N meses (dataset termica_despacho); a parte inflexível já está no inflexterm. Sem isso a nuclear
                      (~2 GW, CVU 20-31) ficaria na base da pilha e distorceria o preço (o legado somava 3.500 MW ao despacho)
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


def _capacidade_mensal() -> pd.DataFrame:
    """Por (ano, mes, cod): pmax = máximo da geração verificada; inflex = média da inflexibilidade; subsistema."""
    partes = []
    for df in ons.iterar_termica_despacho(["val_verifgeracao", "val_verifinflexibilidade"],
                                          colunas_extra=["cod_usinaplanejamento", "id_subsistema"]):
        df = df.dropna(subset=["cod_usinaplanejamento"])
        g = df.groupby([df["din_instante"].dt.year.rename("ano"), df["din_instante"].dt.month.rename("mes"),
                        df["cod_usinaplanejamento"].astype(int).rename("cod")]).agg(
            pmax=("val_verifgeracao", "max"), inflex=("val_verifinflexibilidade", "mean"), subsistema=("id_subsistema", "first"))
        partes.append(g)
    cap = pd.concat(partes).groupby(level=[0, 1, 2]).agg(pmax=("pmax", "max"), inflex=("inflex", "mean"), subsistema=("subsistema", "first"))
    return cap.reset_index()


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
    cap = _capacidade_mensal()
    cap["t"] = pd.PeriodIndex.from_fields(year=cap["ano"], month=cap["mes"], freq="M")
    n = cfg["pilha_capacidade_meses"]
    pilhas, linhas = {}, []
    for semana, g in cvu.groupby("dat_iniciosemana"):
        ultima = g.sort_values("num_revisao").groupby("cod_usinaplanejamento").tail(1)
        per = semana.to_period("M")
        jan = cap[(cap["t"] <= per) & (cap["t"] > per - n)].groupby("cod").agg(pmax=("pmax", "max"), inflex=("inflex", "mean"),
                                                                                subsistema=("subsistema", "last"))
        jan["capacidade"] = (jan["pmax"] - jan["inflex"]).clip(lower=0)
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
