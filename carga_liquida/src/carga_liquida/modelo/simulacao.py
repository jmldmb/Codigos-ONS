"""Simulação Monte Carlo horária (porte de mini_dessem/simulation.py).

Para cada (ano, mês) das premissas e cada cenário: amostra o mês inteiro de eólica (perfil × fator diário
AR(1) × ruído horário) e de solar (cent + dist; fator diário opcional), depois percorre os dias, amostra a carga
(v6 com temperatura real quando existe), despacha hora a hora e precifica. Antes do despacho, subtrai da eólica e da solar centralizada o curtailment de REDE
(premissa mensal exógena, samplers/curtailment_rede.py); o despacho só decide o corte energético.
Saída: um registro por (cenário, dia, hora) com todas as componentes, incluindo

    carga_liquida = carga − eólica_pós − solar_pós − inflexterm − FD   (≡ R + térmica_flex)

que é a mesma grandeza medida em observado/ e comparada em validacao/.
"""
import calendar
import time
from datetime import date

import numpy as np
import pandas as pd

from ..config import get_logger, load_config, output_dir
from ..dados import temperatura
from . import feriados, pilha_termica, premissas, valor_agua
from .despacho import despachar, despachar_va
from .hidro_fd import parametros as params_fd
from .preco import Precificador
from .samplers.carga import CargaSampler
from .samplers.curtailment_rede import CurtailmentRedeSampler
from .samplers.eolica import EolicaSampler
from .samplers.solar import SolarSampler
from .samplers.temperatura import TemperaturaSampler
from .samplers.termica import TermicaSampler

logger = get_logger("simulacao")
SAIDA = "modelo"


def _temperatura_mensal(ano: int, mes: int, climatologia: dict, mensal: pd.DataFrame) -> float:
    r = mensal[(mensal["ano"] == ano) & (mensal["mes"] == mes)]
    return float(r["temp_media_c"].iloc[0]) if len(r) else float(climatologia.get(mes, 22.0))


def simular(anos=None, meses=None, num_simulacoes: int | None = None, seed: int | None = None,
            pilha=None, salvar: bool = True, verbose: bool = True) -> pd.DataFrame:
    cfg = load_config()["modelo"]
    anos = list(anos) if anos is not None else cfg["anos"]
    meses = list(meses) if meses is not None else cfg["meses"]
    n_sim = num_simulacoes or cfg["num_simulacoes"]
    rng = np.random.default_rng(seed)

    prem = premissas.montar(anos, meses)
    prem = prem.dropna(subset=["carga", "eolica", "solar_centralizada", "solar_distribuida", "ena_armazenavel", "inflexterm"])
    s_carga, s_eol = CargaSampler(), EolicaSampler()
    s_cent, s_dist = SolarSampler("centralizada"), SolarSampler("distribuida")
    s_rede = CurtailmentRedeSampler() if cfg.get("curtailment_rede", True) else None
    s_temp = TemperaturaSampler()
    modo_va = cfg.get("termica_flexivel") == "valor_agua"
    s_term = TermicaSampler() if not modo_va else None
    va_dia = valor_agua.serie_diaria(anos, meses) if modo_va else None
    pfd = params_fd()
    precos = Precificador(pilha)
    try:
        clim, temp_mensal = temperatura.climatologia_mensal(), temperatura.temperatura_mensal()
    except FileNotFoundError:
        clim, temp_mensal = {}, pd.DataFrame(columns=["ano", "mes", "temp_media_c"])

    total_h = int(sum(n_sim * calendar.monthrange(int(r.ano), int(r.mes))[1] * 24 for r in prem.itertuples()))
    logger.info(f"simulando {len(prem)} meses × {n_sim} cenários = {total_h:,} horas; hidro FD {pfd['origem']}; "
                f"inflexterm = {cfg['inflexterm']}; térmica flexível = {cfg.get('termica_flexivel', 'residual')}"
                + (f" (perfil {s_term.modo})" if s_term else f" (fonte {cfg['valor_agua_fonte']})"))
    t0, feitas, registros = time.time(), 0, []

    for r in prem.itertuples():
        ano, mes = int(r.ano), int(r.mes)
        temp_mes = _temperatura_mensal(ano, mes, clim, temp_mensal)
        n_dias = calendar.monthrange(ano, mes)[1]
        dias = [date(ano, mes, dia) for dia in range(1, n_dias + 1)]
        temps_reais = {dia: temperatura.temperaturas_dia(ano, mes, dia) if clim else None for dia in range(1, n_dias + 1)}
        completo = all(v is not None for v in temps_reais.values())
        carga_mes = s_carga.gerar_dias(dias, r.carga, temp_mes, temps_reais) if completo else None   # determinística com temperatura real
        for sim in range(1, n_sim + 1):
            if not completo:                                   # dias sem temperatura real: anomalia diária amostrada
                temps = {**s_temp.gerar_mes(mes, temp_mes, n_dias, rng), **{d: v for d, v in temps_reais.items() if v is not None}}
                carga_mes = s_carga.gerar_dias(dias, r.carga, temp_mes, temps)
            else:
                temps = temps_reais
            eol_mes = s_eol.gerar_mes(mes, r.eolica, n_dias, rng, teto=float(r.eolica_capacidade))
            cent_mes, dist_mes = s_cent.gerar_mes(mes, r.solar_centralizada, n_dias, rng), s_dist.gerar_mes(mes, r.solar_distribuida, n_dias, rng)
            for dia in range(1, n_dias + 1):
                d = date(ano, mes, dia)
                tipo = feriados.tipo_dia(d)
                temp_h = temps[dia]
                carga = carga_mes[dia - 1]
                eol, cent, dist = eol_mes[dia - 1], cent_mes[dia - 1], dist_mes[dia - 1]
                if s_rede is not None:                     # corte de rede (CNF/REL) sai antes do despacho
                    rede_eol = s_rede.gerar_dia("eolica", mes, r.curtailment_rede_eolica, eol)
                    rede_cent = s_rede.gerar_dia("solar", mes, r.curtailment_rede_solar, cent)
                else:
                    rede_eol, rede_cent = np.zeros(24), np.zeros(24)
                eol_liq, cent_liq = eol - rede_eol, cent - rede_cent
                if modo_va:
                    va = va_dia.loc[pd.Timestamp(d)].to_dict() if pd.Timestamp(d) in va_dia.index else {}
                    if not va or np.isnan(va.get("SE", np.nan)):
                        continue
                    p = pilha_termica.pilha_semana(d)
                    pilha_arr = {"cvu": p["cvu"].values.astype(float), "capacidade": p["capacidade"].values.astype(float),
                                 "minimo": p["minimo"].values.astype(float) if cfg["pilha_minimo_quantil"] > 0 else np.zeros(len(p)),
                                 "subsistema": p["subsistema"].values}
                else:
                    base = s_term.gerar_dia(mes, tipo, float(r.termica_flex_base))
                if np.isnan(carga).any() or np.isnan(eol).any():
                    continue
                for h in range(24):
                    if modo_va:
                        res = despachar_va(carga[h], eol_liq[h], cent_liq[h], dist[h], r.inflexterm, r.ena_armazenavel,
                                           mes, h, tipo == "DU", va, pilha_arr, pfd)
                    else:
                        res = despachar(carga[h], eol_liq[h], cent_liq[h], dist[h], r.inflexterm, r.ena_armazenavel,
                                        mes, h, tipo == "DU", pfd, termica_base=base[h])
                    if res is None:
                        continue
                    # curtailment: energético (despacho) + rede (premissa); val_gereolica/solar_cent = potencial bruto
                    res = {**res, "curtailment_ene": res["curtailment"], "curtailment_rede_eolica": rede_eol[h],
                           "curtailment_rede_solar": rede_cent[h], "curtailment_rede": rede_eol[h] + rede_cent[h],
                           "curtailment": res["curtailment"] + rede_eol[h] + rede_cent[h],
                           "curtailment_eolica": res["curtailment_eolica"] + rede_eol[h],
                           "curtailment_solar_cent": res["curtailment_solar_cent"] + rede_cent[h]}
                    # carga líquida = R + térmica flexível (base + extra) = carga − renováveis pós − inflexível − FD
                    cl_ = carga[h] - res["val_gereolica_depois_corte"] - res["val_gersolar_depois_corte"] - r.inflexterm - res["val_gerhidro_fd"]
                    registros.append({
                        "ano": ano, "mes": mes, "dia": dia, "hora": h, "simulacao": sim, "tipo_dia": tipo,
                        "historico": bool(r.historico), "val_carga": carga[h], "val_gereolica": eol[h],
                        "val_gersolar_cent": cent[h], "val_gersolar_dist": dist[h], "val_gersolar": cent[h] + dist[h],
                        "val_inflexterm": r.inflexterm, "ENA_arm": r.ena_armazenavel, "temp_c": temp_h[h] if temp_h else np.nan,
                        **res, "val_gerhidro_total": res["val_gerhidro_reservatorio"] + res["val_gerhidro_fd"],
                        "carga_liquida": cl_, "valor_agua": va.get("SE") if modo_va else np.nan,
                    })
                    if "pld" not in res:
                        registros[-1]["pld"] = precos.pld(res["val_term_despacho"], ano, mes)
                feitas += 24
            if verbose and sim == n_sim:
                el = time.time() - t0
                logger.info(f"  {ano}-{mes:02d} ok  [{feitas:,}/{total_h:,} h, {el:.0f}s, ~{(total_h - feitas) / max(feitas / el, 1):.0f}s restantes]")

    df = pd.DataFrame(registros)
    if df.empty:
        logger.warning("nenhum resultado gerado")
        return df
    df["din_instante"] = pd.to_datetime(df[["ano", "mes", "dia", "hora"]].rename(columns={"ano": "year", "mes": "month", "dia": "day", "hora": "hour"}))
    logger.info(f"concluído: {len(df):,} registros em {time.time() - t0:.0f}s; erros de balanço: {int(df['val_erro'].sum())}; "
                f"carga líquida média {df['carga_liquida'].mean():,.0f} MW; curtailment médio {df['curtailment'].mean():,.0f} MW "
                f"(energético {df['curtailment_ene'].mean():,.0f} + rede {df['curtailment_rede'].mean():,.0f})")
    if "regime" in df.columns:
        logger.info("regimes: " + ", ".join(f"{k} {100 * v:.1f}%" for k, v in df["regime"].value_counts(normalize=True).items()))
    if salvar:
        out = output_dir(SAIDA)
        df.to_parquet(out / "resultados_simulacao.parquet", index=False, compression="snappy")
        resumo = df.groupby(["ano", "mes"]).agg(carga=("val_carga", "mean"), carga_liquida=("carga_liquida", "mean"),
                                                hidro_r=("val_gerhidro_reservatorio", "mean"), hidro_fd=("val_gerhidro_fd", "mean"),
                                                termica_flex=("val_term_despacho", "mean"), curtailment=("curtailment", "mean"),
                                                curtailment_ene=("curtailment_ene", "mean"), curtailment_rede=("curtailment_rede", "mean"),
                                                pld=("pld", "mean")).round(1)
        resumo.to_csv(out / "resumo_mensal.csv")
        logger.info(f"salvo em {out}")
    return df


def carregar_resultados() -> pd.DataFrame:
    p = output_dir(SAIDA) / "resultados_simulacao.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} não existe. Rode: python run.py simular")
    df = pd.read_parquet(p)
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    return df
