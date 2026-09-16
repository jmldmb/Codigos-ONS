"""Pilha térmica (merit order) mensal montada dos dados abertos do ONS.

    CVU por usina   : dataset `cvu` (semanal, PMO + revisões), última semana <= fim do mês, revisão mais alta
    capacidade      : máximo da geração verificada da usina nos últimos N meses (dataset termica_despacho)
    chave           : cod_usinaplanejamento (presente nos dois datasets)

Resultado por (ano, mês): DataFrame ordenado por CVU com `potencia` (capacidade acumulada, MW) e `cvu`
(R$/MWh), o mesmo formato da aba 'pilha_term' do xlsx do módulo CVU térmicas. Usinas com CVU = 0
(inflexíveis/contratuais) ficam fora da pilha flexível.
"""
import pandas as pd

from ..config import get_logger, load_config, output_dir
from ..dados import ons

logger = get_logger("pilha")
_CACHE = None


def _capacidade_mensal() -> pd.DataFrame:
    """Máximo mensal da geração verificada por usina: (ano, mes, cod) -> pmax."""
    partes = []
    for df in ons.iterar_termica_despacho(["val_verifgeracao"], colunas_extra=["cod_usinaplanejamento"]):
        df = df.dropna(subset=["cod_usinaplanejamento"])
        g = df.groupby([df["din_instante"].dt.year.rename("ano"), df["din_instante"].dt.month.rename("mes"),
                        df["cod_usinaplanejamento"].astype(int).rename("cod")])["val_verifgeracao"].max()
        partes.append(g)
    return pd.concat(partes).groupby(level=[0, 1, 2]).max().rename("pmax").reset_index()


ARQ = "pilhas_termicas.csv"


def montar_todas(rebuild: bool = False) -> dict[tuple[int, int], pd.DataFrame]:
    """Pilha de cada mês com CVU disponível. Cache em memória e em Output/modelo/pilhas_termicas.csv
    (lido quando existe; `python run.py treinar pilha` reconstrói dos brutos, ~25 s)."""
    global _CACHE
    if _CACHE is not None and not rebuild:
        return _CACHE
    csv = output_dir("modelo") / ARQ
    if csv.exists() and not rebuild:
        df = pd.read_csv(csv)
        _CACHE = {(int(a), int(m)): g.drop(columns=["ano", "mes"]).reset_index(drop=True) for (a, m), g in df.groupby(["ano", "mes"])}
        logger.info(f"pilhas térmicas: {len(_CACHE)} meses lidos de {csv.name}")
        return _CACHE
    cfg = load_config()["modelo"]
    cvu = ons.carregar_cvu()
    cap = _capacidade_mensal()
    cap["t"] = pd.PeriodIndex.from_fields(year=cap["ano"], month=cap["mes"], freq="M")
    n = cfg["pilha_capacidade_meses"]
    pilhas, linhas = {}, []
    for per, g in cvu.groupby(cvu["dat_iniciosemana"].dt.to_period("M")):
        ultima = g[g["dat_iniciosemana"] == g["dat_iniciosemana"].max()]
        ultima = ultima.sort_values("num_revisao").groupby("cod_usinaplanejamento").tail(1)
        janela = cap[(cap["t"] <= per) & (cap["t"] > per - n)].groupby("cod")["pmax"].max()
        p = ultima.merge(janela.rename("potencia_usina"), left_on="cod_usinaplanejamento", right_index=True, how="inner")
        p = p[(p["val_cvu"] > 0) & (p["potencia_usina"] > 0)].sort_values(["val_cvu", "potencia_usina"])
        if p.empty:
            continue
        pilha = pd.DataFrame({"potencia": p["potencia_usina"].cumsum().values, "cvu": p["val_cvu"].values,
                              "cod": p["cod_usinaplanejamento"].values, "nom_usina": p["nom_usina"].values})
        pilhas[(per.year, per.month)] = pilha
        linhas.append(pilha.assign(ano=per.year, mes=per.month))
    if not pilhas:
        raise FileNotFoundError("Sem dados para montar a pilha térmica (datasets cvu e termica_despacho)")
    pd.concat(linhas, ignore_index=True).to_csv(csv, index=False)
    ult = max(pilhas)
    logger.info(f"pilhas térmicas: {len(pilhas)} meses ({min(pilhas)} a {ult}); última: {len(pilhas[ult])} usinas, "
                f"{pilhas[ult]['potencia'].iloc[-1]:,.0f} MW flexíveis, CVU {pilhas[ult]['cvu'].min():.0f}–{pilhas[ult]['cvu'].max():.0f}")
    _CACHE = pilhas
    return pilhas


def pilha(ano: int, mes: int) -> pd.DataFrame:
    """Pilha do mês, ou a mais recente anterior (projeções)."""
    pilhas = montar_todas()
    chave = (ano, mes)
    if chave not in pilhas:
        anteriores = [k for k in pilhas if k <= chave]
        chave = max(anteriores) if anteriores else min(pilhas)
    return pilhas[chave]
