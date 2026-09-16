"""Despacho horário simplificado (porte de mini_dessem/dispatch.py).

Dado carga, renováveis disponíveis, térmica inflexível e ENA, resolve o balanço:

    carga = eólica_pós + solar_pós + inflexterm + FD(R) + R + térmica_flex

1. R no máximo (limite_hidro_reservatorio); FD segue R pela regressão.
2. Sobra? reduz R até min_hidro_reservatorio (brentq, porque FD depende de R).
3. Ainda sobra? curtailment em cascata: eólica + solar centralizada pro rata; só depois a distribuída.
4. Falta? sobe R até o limite; o resto vira térmica flexível (val_term_despacho).
"""
from scipy.optimize import brentq

from ..config import load_config
from .hidro_fd import calcular_fd


def _cfg():
    return load_config()["modelo"]


def despachar(carga: float, eolica: float, solar_cent: float, solar_dist: float, inflexterm: float, ena: float,
              mes: int, hora: int, is_weekday: bool, params_fd: dict | None = None) -> dict | None:
    cfg = _cfg()
    lim, mn = cfg["limite_hidro_reservatorio"], cfg["min_hidro_reservatorio"]
    fd = lambda r: calcular_fd(mes, hora, is_weekday, r, ena, params_fd)  # noqa: E731
    solar = solar_cent + solar_dist

    R = lim
    excesso = eolica + solar + inflexterm + fd(R) + R - carga
    eol_pos, cent_pos, dist_pos = eolica, solar_cent, solar_dist
    corte_eol = corte_cent = corte_dist = 0.0

    if excesso > 0:
        erro = lambda r: eolica + solar + inflexterm + fd(r) + r - carga  # noqa: E731
        try:
            R = brentq(erro, mn, lim, xtol=cfg["solver_xtol"])
        except ValueError:  # sem raiz no intervalo: excesso persiste mesmo no mínimo
            R = mn
        excesso = erro(R)
        if excesso > 0:
            p1 = eol_pos + cent_pos
            if excesso <= p1 and p1 > 0:
                corte_eol, corte_cent = excesso * eol_pos / p1, excesso * cent_pos / p1
            else:
                corte_eol, corte_cent = eol_pos, cent_pos
                corte_dist = min(excesso - p1, dist_pos)
            eol_pos, cent_pos, dist_pos = max(eol_pos - corte_eol, 0), max(cent_pos - corte_cent, 0), max(dist_pos - corte_dist, 0)

    deficit = carga - (eol_pos + cent_pos + dist_pos + inflexterm + fd(R) + R)
    if deficit > 0:
        R += min(deficit, lim - R)
        deficit = carga - (eol_pos + cent_pos + dist_pos + inflexterm + fd(R) + R)
    termica_flex = max(deficit, 0.0)
    FD = fd(R)
    if min(termica_flex, R, FD, eol_pos, cent_pos, dist_pos) < 0:
        return None
    balanco = eol_pos + cent_pos + dist_pos + inflexterm + FD + R + termica_flex
    return {"val_term_despacho": termica_flex, "val_gerhidro_reservatorio": R, "val_gerhidro_fd": FD,
            "curtailment": corte_eol + corte_cent + corte_dist, "curtailment_eolica": corte_eol,
            "curtailment_solar_cent": corte_cent, "curtailment_solar_dist": corte_dist,
            "val_gereolica_depois_corte": eol_pos, "val_gersolar_cent_depois_corte": cent_pos,
            "val_gersolar_dist_depois_corte": dist_pos, "val_gersolar_depois_corte": cent_pos + dist_pos,
            "val_erro": int(abs(balanco - carga) > cfg["balance_tolerance"])}
