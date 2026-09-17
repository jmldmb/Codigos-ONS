"""Valor da água (preço-base, R$/MWh) — a premissa do modo `termica_flexivel: valor_agua`.

Faz o papel do preço de patamar do DECOMP: define quais térmicas entram na base (CVU <= VA) e é o
preço das horas em que a hidro de reservatório é o recurso marginal. A modulação horária fica por
conta do despacho (modelo/despacho.despachar_va).

Histórico (config.modelo.valor_agua_fonte):
    cmo    mediana semanal do CMO observado (semana operativa sábado-sexta)   — preço observado
    pilha  CVU da pilha do mês no ponto da térmica flexível média da semana — dual da térmica observada
Projeção: `valor_agua_rs_mwh[ano][mês]` em config/projecoes.yaml; se ausente mas houver
`termica_flexivel_mwmed`, VA = CVU da pilha nesse ponto (as duas premissas são duais via a pilha).
"""
import numpy as np
import pandas as pd
import yaml

from ..config import ROOT, get_logger, load_config
from ..dados import ons
from ..observado import carga_liquida as cl
from . import pilha_termica

logger = get_logger("valor_agua")


def _semana(ts: pd.Series) -> pd.Series:
    """Sábado que inicia a semana operativa de cada instante."""
    return (ts - pd.to_timedelta((ts.dt.weekday + 2) % 7, unit="D")).dt.normalize()


def cvu_no_ponto(ano: int, mes: int, mw: float) -> float:
    p = pilha_termica.pilha(ano, mes)
    if mw <= 0:
        return float(load_config()["modelo"]["pld_minimo"])
    i = np.searchsorted(p["potencia"].values, mw, side="left")
    return float(p["cvu"].values[min(i, len(p) - 1)])


def historico_semanal(fonte: str | None = None) -> pd.DataFrame:
    """(semana, valor_agua) para o período observado."""
    fonte = fonte or load_config()["modelo"]["valor_agua_fonte"]
    if fonte == "cmo":
        cmo = ons.carregar_cmo()
        cmo["semana"] = _semana(cmo["din_instante"])
        va = cmo.groupby("semana")["val_cmo"].median().rename("valor_agua")
    elif fonte == "pilha":
        h = cl.carregar_historico()
        h["semana"] = _semana(h["din_instante"])
        w = h.groupby("semana").agg(flex=("termica_flexivel", "mean"), ano=("ano", "first"), mes=("mes", "first"))
        va = pd.Series([cvu_no_ponto(int(a), int(m), f) for f, a, m in zip(w["flex"], w["ano"], w["mes"])],
                       index=w.index, name="valor_agua")
    else:
        raise ValueError(f"valor_agua_fonte inválida: {fonte}")
    return va.reset_index()


def projecoes_mensais() -> dict[tuple[int, int], float]:
    path = ROOT / load_config()["modelo"]["projecoes"]
    with open(path, encoding="utf-8") as f:
        proj = yaml.safe_load(f)
    out = {}
    for ano, meses in (proj.get("valor_agua_rs_mwh") or {}).items():
        for mes, v in meses.items():
            out[(int(ano), int(mes))] = float(v)
    # dual: térmica base declarada -> VA pela pilha
    for ano, meses in (proj.get("termica_flexivel_mwmed") or {}).items():
        for mes, mw in meses.items():
            out.setdefault((int(ano), int(mes)), cvu_no_ponto(int(ano), int(mes), float(mw)))
    return out


def serie_diaria(anos, meses) -> pd.Series:
    """valor_agua por dia (index = data) para os anos/meses pedidos: histórico semanal onde existe, projeção mensal no resto."""
    hist = historico_semanal().set_index("semana")["valor_agua"]
    proj = projecoes_mensais()
    dias = pd.DatetimeIndex([d for a in anos for m in meses for d in pd.date_range(f"{a}-{m:02d}-01", periods=31, freq="D") if d.month == m])
    sem = _semana(pd.Series(dias))
    va = pd.Series(hist.reindex(sem.values).values, index=dias, name="valor_agua")
    faltam = va.isna()
    for d in dias[faltam]:
        va[d] = proj.get((d.year, d.month), np.nan)
    sem_valor = sorted({(d.year, d.month) for d in dias[va.isna()]})
    if sem_valor:
        logger.warning(f"Sem valor da água (histórico nem projeção) para {sem_valor}; esses meses serão pulados")
    logger.info(f"valor da água: {int((~faltam).sum())} dias do histórico ({load_config()['modelo']['valor_agua_fonte']}), "
                f"{int(faltam.sum())} dias de projeção; média {va.mean():.0f} R$/MWh")
    return va
