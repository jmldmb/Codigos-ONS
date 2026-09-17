"""Pilha térmica (merit order) SEMANAL montada dos dados abertos do ONS.

    CVU por usina   : dataset `cvu` (semana operativa sábado-sexta, PMO + revisões; usa a revisão mais alta da semana)
    capacidade      : capacidade flexível da usina na semana = máximo gerado nas K semanas anteriores (≈ 12 meses)
                      − inflexibilidade média (dataset termica_despacho). Proxy causal: só usa o passado. A disponibilidade
                      operacional declarada do ONS (disponibilidade_usina_ho) foi testada como alternativa e não mudou as
                      métricas — o sub-despacho residual é restrição de combustível, invisível nos dois (ver README).
    mínimo técnico  : menor nível sustentado da parcela flexível quando a usina está ligada = quantil
                      `pilha_minimo_quantil` (P10) da geração flexível nas horas ligadas com vizinhas ligadas (sem
                      rampas), mediana das K semanas anteriores. Na sobra, a usina comprometida reduz até aqui, não até
                      zero: o ONS não desliga ciclo combinado grande nem carvão no vale solar (Sergipe, Pecém, Itaqui
                      ficam a 65–85 %); quem desliga são motores e ciclos abertos pequenos. Ver README.
    nuclear         : inflexível por definição (CEG 'UTN'), fora da pilha
    subsistema      : id_subsistema da usina — a térmica é despachada contra o preço do SEU subsistema
    chave           : cod_usinaplanejamento (presente nos dois datasets)

Resultado por semana: DataFrame ordenado por CVU com `cvu`, `capacidade` (MW flexíveis da usina), `minimo` (MW,
piso da redução intradiária), `potencia` (acumulada), `subsistema`, `cod`, `nom_usina`. `pilha(ano, mes)` devolve a última semana do mês (compatibilidade).
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


FLEX = ["val_verifordemdemeritoacimadainflex", "val_verifunitcommitment"]
MIN_HORAS_SUSTENTADAS = 24  # semana só contribui para o mínimo técnico com pelo menos isto de horas ligadas sem rampa


def _geracao_semanal() -> pd.DataFrame:
    """Por (semana, cod): gmax = máximo da geração verificada; inflex = média da inflexibilidade; subsistema; nuclear;
    q_on = quantil da geração flexível nas horas sustentadas (ligada, com a anterior e a seguinte ligadas); n_on = horas."""
    q = load_config()["modelo"]["pilha_minimo_quantil"]
    partes = []
    for df in ons.iterar_termica_despacho(["val_verifgeracao", "val_verifinflexibilidade", *FLEX],
                                          colunas_extra=["cod_usinaplanejamento", "id_subsistema", "ceg"]):
        df = df.dropna(subset=["cod_usinaplanejamento"])
        df["cod"] = df["cod_usinaplanejamento"].astype(int)
        df["semana"] = semana_operativa(df["din_instante"])
        df["flex"] = df[FLEX].fillna(0.0).sum(axis=1)
        df = df.sort_values(["cod", "din_instante"])
        limiar = 0.05 * df.groupby(["semana", "cod"])["flex"].transform("max")
        on = df["flex"] > limiar.clip(lower=1.0)
        g_cod = on.groupby(df["cod"])
        sustentada = on & g_cod.shift(1, fill_value=False) & g_cod.shift(-1, fill_value=False)
        df["flex_on"] = df["flex"].where(sustentada)
        g = df.groupby(["semana", "cod"]).agg(
            gmax=("val_verifgeracao", "max"), inflex=("val_verifinflexibilidade", "mean"), subsistema=("id_subsistema", "first"),
            nuclear=("ceg", lambda s: bool(s.astype(str).str.startswith("UTN").any())),
            q_on=("flex_on", lambda s: s.quantile(q)), n_on=("flex_on", "count"))
        partes.append(g)
    return pd.concat(partes).groupby(level=[0, 1]).agg(gmax=("gmax", "max"), inflex=("inflex", "mean"), subsistema=("subsistema", "first"),
                                                        nuclear=("nuclear", "max"), q_on=("q_on", "mean"), n_on=("n_on", "sum")).reset_index()


def _capacidade(ger: pd.DataFrame, semana: pd.Timestamp, k: int) -> pd.DataFrame:
    """Capacidade flexível = max(gmax) − mean(inflex) nas k semanas anteriores (exclui nuclear); mínimo técnico =
    mediana do quantil semanal q_on nas semanas com horas sustentadas suficientes (0 quando não há estimativa)."""
    jan = ger[(ger["semana"] < semana) & (ger["semana"] >= semana - pd.Timedelta(weeks=k)) & ~ger["nuclear"].astype(bool)]
    d = jan.groupby("cod").agg(gmax=("gmax", "max"), inflex=("inflex", "mean"), subsistema=("subsistema", "last"))
    d["capacidade"] = (d["gmax"] - d["inflex"]).clip(lower=0)
    minimo = jan[jan["n_on"] >= MIN_HORAS_SUSTENTADAS].groupby("cod")["q_on"].median()
    d["minimo"] = minimo.reindex(d.index).fillna(0.0).clip(lower=0.0)
    d["minimo"] = d[["minimo", "capacidade"]].min(axis=1)
    return d



def montar_todas(rebuild: bool = False) -> dict[pd.Timestamp, pd.DataFrame]:
    """Pilha de cada semana operativa com CVU. Cache em memória e em Output/modelo/pilhas_termicas.csv
    (lido quando existe; `python run.py treinar pilha` reconstrói dos brutos, ~25 s)."""
    global _CACHE
    if _CACHE is not None and not rebuild:
        return _CACHE
    csv = output_dir("modelo") / ARQ
    if csv.exists() and not rebuild:
        df = pd.read_csv(csv, parse_dates=["semana"])
        if "minimo" not in df.columns:
            raise FileNotFoundError(f"{csv} sem a coluna 'minimo' (mínimo técnico). Rode: python run.py treinar pilha")
        _CACHE = {s: g.drop(columns=["semana"]).reset_index(drop=True) for s, g in df.groupby("semana")}
        logger.info(f"pilhas térmicas: {len(_CACHE)} semanas lidas de {csv.name}")
        return _CACHE
    cfg = load_config()["modelo"]
    cvu = ons.carregar_cvu()
    ger = _geracao_semanal()
    k = cfg["pilha_capacidade_semanas"]
    pilhas, linhas = {}, []
    for semana, g in cvu.groupby("dat_iniciosemana"):
        ultima = g.sort_values("num_revisao").groupby("cod_usinaplanejamento").tail(1)
        jan = _capacidade(ger, semana, k)
        if jan.empty:
            continue
        p = ultima.merge(jan[["capacidade", "minimo", "subsistema"]], left_on="cod_usinaplanejamento", right_index=True, how="inner")
        p = p[(p["val_cvu"] > 0) & (p["capacidade"] >= cfg["pilha_min_flex_mw"])].sort_values(["val_cvu", "capacidade"])
        if p.empty:
            continue
        pilha = pd.DataFrame({"cvu": p["val_cvu"].values, "capacidade": p["capacidade"].values, "minimo": p["minimo"].values,
                              "potencia": p["capacidade"].cumsum().values, "subsistema": p["subsistema"].values,
                              "cod": p["cod_usinaplanejamento"].values, "nom_usina": p["nom_usina"].values})
        pilhas[semana] = pilha
        linhas.append(pilha.assign(semana=semana))
    if not pilhas:
        raise FileNotFoundError("Sem dados para montar a pilha térmica (datasets cvu e termica_despacho)")
    pd.concat(linhas, ignore_index=True).to_csv(csv, index=False)
    ult = max(pilhas)
    logger.info(f"pilhas térmicas: {len(pilhas)} semanas ({min(pilhas):%Y-%m-%d} a {ult:%Y-%m-%d}); última: {len(pilhas[ult])} usinas, "
                f"{pilhas[ult]['potencia'].iloc[-1]:,.0f} MW flexíveis (mínimo técnico {pilhas[ult]['minimo'].sum():,.0f} MW), "
                f"CVU {pilhas[ult]['cvu'].min():.0f}–{pilhas[ult]['cvu'].max():.0f}")
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
