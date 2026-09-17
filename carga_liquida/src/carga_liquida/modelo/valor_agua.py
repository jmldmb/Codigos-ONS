"""Valor da água (preço-base semanal por subsistema, R$/MWh) — premissa do modo `termica_flexivel: valor_agua`.

Faz o papel do preço de patamar do DECOMP: define quais térmicas entram na base comprometida da semana
(CVU <= VA do subsistema da usina) e é o preço das horas em que a hidro de reservatório é o recurso
marginal. A modulação horária fica por conta do despacho (modelo/despacho.despachar_va).

O preço-base é por PATAMAR: semana × tipo de dia (DU | FDS), como no DECOMP. A base térmica é comprometida por
dia: no fim de semana o preço cai abaixo do CVU das usinas próximas da margem e elas desligam (observado: utilização
0,66 em DU vs 0,50 em FDS, liga/desliga e não carga parcial).

Histórico (config.modelo.valor_agua_fonte):
    cmo    mediana do CMO observado nas horas DU e nas horas FDS de cada semana operativa, por subsistema
    pilha  CVU da pilha da semana no ponto da térmica de mérito média observada (um valor, aplicado a todos)
Projeção: `valor_agua_rs_mwh[ano][mês]` em config/projecoes.yaml — número (todos os subsistemas e patamares),
{SE: .., S: .., NE: .., N: ..} ou {DU: {...}, FDS: {...}}. Se ausente mas houver `termica_flexivel_mwmed`,
VA = CVU da pilha nesse ponto.
"""
import numpy as np
import pandas as pd
import yaml

from ..config import ROOT, get_logger, load_config
from ..dados import ons
from ..observado import carga_liquida as cl
from . import feriados, pilha_termica

logger = get_logger("valor_agua")
SUBSISTEMAS = ("SE", "S", "NE", "N")


def cvu_no_ponto(data, mw: float) -> float:
    p = pilha_termica.pilha_semana(data)
    if mw <= 0:
        return float(load_config()["modelo"]["pld_minimo"])
    i = np.searchsorted(p["potencia"].values, mw, side="left")
    return float(p["cvu"].values[min(i, len(p) - 1)])


def historico_semanal(fonte: str | None = None) -> pd.DataFrame:
    """index = (semana operativa, tipo_dia DU|FDS); colunas SE, S, NE, N."""
    fonte = fonte or load_config()["modelo"]["valor_agua_fonte"]
    if fonte == "cmo":
        cmo = ons.carregar_cmo(subsistema=None)
        cmo["semana"] = pilha_termica.semana_operativa(cmo["din_instante"])
        cmo["tipo_dia"] = cmo["din_instante"].dt.date.map(feriados.tipo_dia)
        va = cmo.groupby(["semana", "tipo_dia", "id_subsistema"])["val_cmo"].median().unstack()
        return va.reindex(columns=SUBSISTEMAS)
    if fonte == "pilha":
        t = cl.carregar_termica_componentes()[["din_instante", "val_verifordemdemeritoacimadainflex"]]
        t["semana"] = pilha_termica.semana_operativa(t["din_instante"])
        t["tipo_dia"] = t["din_instante"].dt.date.map(feriados.tipo_dia)
        w = t.groupby(["semana", "tipo_dia"])["val_verifordemdemeritoacimadainflex"].mean()
        vals = [cvu_no_ponto(s, m) for (s, _), m in w.items()]
        return pd.DataFrame({sub: vals for sub in SUBSISTEMAS}, index=w.index)
    raise ValueError(f"valor_agua_fonte inválida: {fonte}")


def _por_subsistema(v) -> dict[str, float]:
    return {s: float(v) for s in SUBSISTEMAS} if not isinstance(v, dict) else {s: float(v.get(s, v.get("SE"))) for s in SUBSISTEMAS}


def projecoes_mensais() -> dict[tuple[int, int, str], dict[str, float]]:
    """{(ano, mes, tipo_dia): {subsistema: VA}}."""
    path = ROOT / load_config()["modelo"]["projecoes"]
    with open(path, encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    out = {}
    for ano, meses in (proj.get("valor_agua_rs_mwh") or {}).items():
        for mes, v in meses.items():
            if isinstance(v, dict) and ("DU" in v or "FDS" in v):
                for tipo in ("DU", "FDS"):
                    out[(int(ano), int(mes), tipo)] = _por_subsistema(v.get(tipo, v.get("DU", v.get("FDS"))))
            else:
                for tipo in ("DU", "FDS"):
                    out[(int(ano), int(mes), tipo)] = _por_subsistema(v)
    for ano, meses in (proj.get("termica_flexivel_mwmed") or {}).items():  # dual: térmica base -> VA pela pilha
        for mes, mw in meses.items():
            for tipo in ("DU", "FDS"):
                k = (int(ano), int(mes), tipo)
                if k not in out:
                    v = cvu_no_ponto(pd.Timestamp(k[0], k[1], 15), float(mw))
                    out[k] = {s: v for s in SUBSISTEMAS}
    return out


def serie_diaria(anos, meses) -> pd.DataFrame:
    """VA por dia (index = data) e subsistema: histórico semanal onde existe, projeção mensal no resto."""
    hist = historico_semanal()
    proj = projecoes_mensais()
    dias = pd.DatetimeIndex([d for a in anos for m in meses
                             for d in pd.date_range(f"{a}-{m:02d}-01", periods=31, freq="D") if d.month == m])
    sem = pilha_termica.semana_operativa(pd.Series(dias)).values
    tipos = [feriados.tipo_dia(d.date()) for d in dias]
    va = hist.reindex(pd.MultiIndex.from_arrays([sem, tipos]))
    va.index = dias
    faltam = va["SE"].isna()
    for d, tipo in zip(dias[faltam], np.array(tipos)[faltam.values]):
        p = proj.get((d.year, d.month, tipo))
        if p:
            va.loc[d] = [p[s] for s in SUBSISTEMAS]
    sem_valor = sorted({(d.year, d.month) for d in dias[va["SE"].isna()]})
    if sem_valor:
        logger.warning(f"Sem valor da água (histórico nem projeção) para {sem_valor}; esses meses serão pulados")
    logger.info(f"valor da água: {int((~faltam).sum())} dias do histórico ({load_config()['modelo']['valor_agua_fonte']}), "
                f"{int(faltam.sum())} dias de projeção; média SE {va['SE'].mean():.0f} R$/MWh")
    return va
