"""Simulação Monte Carlo horária (porte de mini_dessem/simulation.py).

Para cada (ano, mês) das premissas e cada cenário: percorre os dias do mês, amostra carga (v6 com
temperatura real quando existe), eólica (AR(1)) e solar (determinística, cent + dist), despacha hora a
hora e precifica. Saída: um registro por (cenário, dia, hora) com todas as componentes, incluindo

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
from . import feriados, premissas
from .despacho import despachar
from .hidro_fd import parametros as params_fd
from .preco import Precificador
from .samplers.carga import CargaSampler
from .samplers.eolica import EolicaSampler
from .samplers.solar import SolarSampler

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
    pfd = params_fd()
    precos = Precificador(pilha)
    try:
        clim, temp_mensal = temperatura.climatologia_mensal(), temperatura.temperatura_mensal()
    except FileNotFoundError:
        clim, temp_mensal = {}, pd.DataFrame(columns=["ano", "mes", "temp_media_c"])

    total_h = int(sum(n_sim * calendar.monthrange(int(r.ano), int(r.mes))[1] * 24 for r in prem.itertuples()))
    logger.info(f"simulando {len(prem)} meses × {n_sim} cenários = {total_h:,} horas; hidro FD {pfd['origem']}; "
                f"inflexterm = {cfg['inflexterm']}")
    t0, feitas, registros = time.time(), 0, []

    for r in prem.itertuples():
        ano, mes = int(r.ano), int(r.mes)
        temp_mes = _temperatura_mensal(ano, mes, clim, temp_mensal)
        n_dias = calendar.monthrange(ano, mes)[1]
        for sim in range(1, n_sim + 1):
            for dia in range(1, n_dias + 1):
                d = date(ano, mes, dia)
                tipo = feriados.tipo_dia(d)
                temp_h = temperatura.temperaturas_dia(ano, mes, dia) if clim else None
                carga = s_carga.gerar_dia(d, r.carga, temp_mes, temp_h)
                eol = s_eol.gerar_dia(mes, r.eolica, rng)
                cent, dist = s_cent.gerar_dia(mes, r.solar_centralizada), s_dist.gerar_dia(mes, r.solar_distribuida)
                if np.isnan(carga).any() or np.isnan(eol).any():
                    continue
                for h in range(24):
                    res = despachar(carga[h], eol[h], cent[h], dist[h], r.inflexterm, r.ena_armazenavel,
                                    mes, h, tipo == "DU", pfd)
                    if res is None:
                        continue
                    cl_ = carga[h] - res["val_gereolica_depois_corte"] - res["val_gersolar_depois_corte"] - r.inflexterm - res["val_gerhidro_fd"]
                    registros.append({
                        "ano": ano, "mes": mes, "dia": dia, "hora": h, "simulacao": sim, "tipo_dia": tipo,
                        "historico": bool(r.historico), "val_carga": carga[h], "val_gereolica": eol[h],
                        "val_gersolar_cent": cent[h], "val_gersolar_dist": dist[h], "val_gersolar": cent[h] + dist[h],
                        "val_inflexterm": r.inflexterm, "ENA_arm": r.ena_armazenavel, "temp_c": temp_h[h] if temp_h else np.nan,
                        **res, "val_gerhidro_total": res["val_gerhidro_reservatorio"] + res["val_gerhidro_fd"],
                        "carga_liquida": cl_, "pld": precos.pld(res["val_term_despacho"], ano, mes),
                    })
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
                f"carga líquida média {df['carga_liquida'].mean():,.0f} MW; curtailment médio {df['curtailment'].mean():,.0f} MW")
    if salvar:
        out = output_dir(SAIDA)
        df.to_parquet(out / "resultados_simulacao.parquet", index=False, compression="snappy")
        resumo = df.groupby(["ano", "mes"]).agg(carga=("val_carga", "mean"), carga_liquida=("carga_liquida", "mean"),
                                                hidro_r=("val_gerhidro_reservatorio", "mean"), hidro_fd=("val_gerhidro_fd", "mean"),
                                                termica_flex=("val_term_despacho", "mean"), curtailment=("curtailment", "mean"),
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
