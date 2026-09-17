"""Despacho horário simplificado (porte de mini_dessem/dispatch.py).

Dado carga, renováveis disponíveis, térmica inflexível e ENA, resolve o balanço:

    carga = eólica_pós + solar_pós + inflexterm + FD(R) + R + térmica_flex

1. R no máximo (limite_hidro_reservatorio); FD segue R pela regressão.
2. Sobra? reduz R até min_hidro_reservatorio (brentq, porque FD depende de R).
3. Ainda sobra? curtailment em cascata: eólica + solar centralizada pro rata; só depois a distribuída.
4. Falta? sobe R até o limite; o resto vira térmica flexível (val_term_despacho).
"""
import numpy as np
from scipy.optimize import brentq

from ..config import load_config
from .hidro_fd import calcular_fd


def _cfg():
    return load_config()["modelo"]


def despachar(carga: float, eolica: float, solar_cent: float, solar_dist: float, inflexterm: float, ena: float,
              mes: int, hora: int, is_weekday: bool, params_fd: dict | None = None, termica_base: float = 0.0) -> dict | None:
    """`termica_base` = térmica flexível decidida por fins energéticos (premissa); entra no balanço como dada,
    junto com a inflexível. A térmica "extra" só aparece quando a hidro R satura."""
    cfg = _cfg()
    lim, mn = cfg["limite_hidro_reservatorio"], cfg["min_hidro_reservatorio"]
    fd = lambda r: calcular_fd(mes, hora, is_weekday, r, ena, params_fd)  # noqa: E731
    solar = solar_cent + solar_dist
    inflexterm = inflexterm + termica_base

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
    termica_extra = max(deficit, 0.0)
    FD = fd(R)
    if min(termica_extra, R, FD, eol_pos, cent_pos, dist_pos) < 0:
        return None
    balanco = eol_pos + cent_pos + dist_pos + inflexterm + FD + R + termica_extra
    return {"val_term_despacho": termica_base + termica_extra, "val_term_base": termica_base, "val_term_extra": termica_extra,
            "val_gerhidro_reservatorio": R, "val_gerhidro_fd": FD, "val_fd_reduzida": fd_red,
            "curtailment": corte_eol + corte_cent + corte_dist, "curtailment_eolica": corte_eol,
            "curtailment_solar_cent": corte_cent, "curtailment_solar_dist": corte_dist,
            "val_gereolica_depois_corte": eol_pos, "val_gersolar_cent_depois_corte": cent_pos,
            "val_gersolar_dist_depois_corte": dist_pos, "val_gersolar_depois_corte": cent_pos + dist_pos,
            "val_erro": int(abs(balanco - carga) > cfg["balance_tolerance"])}


def _curtailment_cascata(excesso, eol, cent, dist):
    """Corta eólica + solar centralizada pro rata; só depois a distribuída. Devolve (eol, cent, dist, cortes)."""
    p1 = eol + cent
    if excesso <= p1 and p1 > 0:
        c_eol, c_cent, c_dist = excesso * eol / p1, excesso * cent / p1, 0.0
    else:
        c_eol, c_cent, c_dist = eol, cent, min(max(excesso - p1, 0.0), dist)
    return max(eol - c_eol, 0), max(cent - c_cent, 0), max(dist - c_dist, 0), (c_eol, c_cent, c_dist)


def despachar_va(carga: float, eolica: float, solar_cent: float, solar_dist: float, inflexterm: float, ena: float,
                 mes: int, hora: int, is_weekday: bool, va: dict, pilha, params_fd: dict | None = None) -> dict | None:
    """Despacho com valor da água (modo `termica_flexivel: valor_agua`), como DECOMP -> DESSEM.

    `va` = {subsistema: preço-base}; `pilha` = dict de arrays da semana (cvu, capacidade, minimo, subsistema).
    Base comprometida = usinas com CVU <= VA do seu subsistema, ligadas o dia inteiro (no vale solar o ONS
    rotula essas MW como "unit commitment", à noite como "ordem de mérito"; a máquina não desliga).
    A hidro R fecha o balanço entre o mínimo e o máximo; o preço horário é o recurso marginal (`cmo`, como o CMO do ONS):
        hidro marginal                 -> cmo = VA[SE]
        R no máximo, ainda falta       -> térmica extra por mérito (fora da base); cmo = CVU da última chamada
        R no mínimo, ainda sobra       -> base reduzida da mais cara para a mais barata, cada usina até o seu MÍNIMO
                                          TÉCNICO (pilha["minimo"]); cmo = CVU da usina parcialmente reduzida
        base toda no mínimo, sobra     -> FD reduzida (vertimento turbinável) até params_fd["reducao_sobra_mw"]; cmo = 0
        ainda sobra                    -> curtailment em cascata; cmo = 0
    `pld` = clip(cmo, pld_minimo, pld_maximo) — piso e teto regulatórios.
    A usina comprometida não desliga na hora da sobra: o ONS a reduz ao mínimo e re-rotula como unit commitment
    (2025-26: térmica flexível 1,7 GW nas horas com corte energético > 1 GW; o modelo zerava). Ver README.
    """
    cfg = _cfg()
    lim, mn, piso, teto = cfg["limite_hidro_reservatorio"], cfg["min_hidro_reservatorio"], cfg["pld_minimo"], cfg.get("pld_maximo", np.inf)
    fd = lambda r: calcular_fd(mes, hora, is_weekday, r, ena, params_fd)  # noqa: E731
    cvu, cap, subs = pilha["cvu"], pilha["capacidade"], pilha["subsistema"]
    va_usina = np.array([va.get(s_, va.get("SE", 0.0)) for s_ in subs])
    na_base = cvu <= va_usina
    base_cheia = float(cap[na_base].sum())
    cvu_base, cap_base = cvu[na_base], cap[na_base]          # ordenados por CVU (pilha já vem ordenada)
    red_base = np.maximum(cap_base - pilha.get("minimo", np.zeros_like(cap))[na_base], 0.0)  # redutível até o mínimo técnico
    cvu_fora, cap_fora = cvu[~na_base], cap[~na_base]
    va_se = float(va.get("SE", 0.0))

    eol, cent, dist = eolica, solar_cent, solar_dist
    cortes = (0.0, 0.0, 0.0)
    fd_red = 0.0
    termica_base, termica_extra = base_cheia, 0.0
    folga = lambda r, t: carga - (eol + cent + dist + inflexterm + t + fd(r) + r)  # noqa: E731  >0 falta, <0 sobra

    if folga(lim, termica_base) > 0:                       # R no máximo, falta -> térmica extra por mérito
        R = lim
        deficit = folga(R, termica_base)
        acum = np.cumsum(cap_fora)
        termica_extra = float(min(deficit, acum[-1])) if len(acum) else 0.0
        j = int(np.searchsorted(acum, termica_extra, side="left")) if termica_extra > 0 else -1
        pld = float(cvu_fora[min(j, len(cvu_fora) - 1)]) if j >= 0 else va_se
        regime = "extra"
    elif folga(mn, termica_base) < 0:                      # R no mínimo, sobra -> reduz base (cara -> barata) até o mínimo, depois corta
        R = mn
        sobra = -folga(R, termica_base)
        reduzivel = float(red_base.sum())
        if sobra < reduzivel:
            termica_base = base_cheia - sobra
            acum = np.cumsum(red_base[::-1])               # da mais cara para a mais barata: a parcialmente reduzida faz o preço
            j = int(np.searchsorted(acum, sobra, side="right"))
            pld = float(cvu_base[::-1][min(j, len(cvu_base) - 1)])
            regime = "base_reduzida"
        else:
            termica_base = base_cheia - reduzivel           # toda a base no mínimo técnico
            excesso = -folga(R, termica_base)
            fd_red = min(excesso, (params_fd or {}).get("reducao_sobra_mw", 0.0)) if cfg.get("fd_reducao_sobra", True) else 0.0
            excesso -= fd_red                              # a FD verte antes do corte de renovável
            if excesso > 0:
                eol, cent, dist, cortes = _curtailment_cascata(excesso, eol, cent, dist)
            pld = 0.0                                      # sobra: custo marginal zero (o PLD fica no piso)
            regime = "curtailment" if excesso > 0 else "fd_reduzida"
    else:                                                  # hidro marginal
        R = brentq(lambda r: folga(r, termica_base), mn, lim, xtol=cfg["solver_xtol"])
        pld = va_se
        regime = "hidro"

    FD = fd(R) - fd_red
    balanco = eol + cent + dist + inflexterm + FD + R + termica_base + termica_extra
    return {"val_term_despacho": termica_base + termica_extra, "val_term_base": termica_base, "val_term_extra": termica_extra,
            "val_gerhidro_reservatorio": R, "val_gerhidro_fd": FD, "val_fd_reduzida": fd_red,
            "curtailment": sum(cortes), "curtailment_eolica": cortes[0], "curtailment_solar_cent": cortes[1],
            "curtailment_solar_dist": cortes[2],
            "val_gereolica_depois_corte": eol, "val_gersolar_cent_depois_corte": cent, "val_gersolar_dist_depois_corte": dist,
            "val_gersolar_depois_corte": cent + dist, "cmo": pld, "pld": float(np.clip(pld, piso, teto)), "regime": regime,
            "val_erro": int(abs(balanco - carga) > cfg["balance_tolerance"])}  # em "extra", erro = déficit sem capacidade
