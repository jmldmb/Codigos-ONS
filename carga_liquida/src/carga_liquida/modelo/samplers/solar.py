"""Sampler solar determinístico: perfil horário médio por mês, separado em centralizada e distribuída.

    centralizada: potencial (geração + corte) do COFF fotovoltaico (>= 2024-04); antes, geração das
                  usinas FOTOVOLTAICA não-MMGD do dataset de geração por usina
    distribuída : geração 'FOTOVOLTAICA - MMGD' do dataset de geração por usina (>= 2023)

Um expoente de forma (config.modelo.solar_*_shape) acentua o pico: p_h ∝ p_h^k, renormalizado.
"""
import numpy as np
import pandas as pd

from ...config import get_logger, load_config
from ...dados import ons
from ...observado import carga_liquida as cl
from ._base import carregar_json, interpolar_meses_faltantes, janela_treino, perfil_proporcional_por_mes, salvar_json

logger = get_logger("sampler.solar")


def _serie_centralizada() -> pd.DataFrame:
    ger = cl.carregar_geracao_por_tipo()
    tipo = load_config()["carga_liquida"]["tipo_usina_solar"]
    usina = ger[["din_instante", tipo]].rename(columns={tipo: "mw"})
    try:
        coff = ons.carregar_coff_horario("solar")[["din_instante", "potencial_mw"]].rename(columns={"potencial_mw": "mw"})
        usina = usina[usina["din_instante"] < coff["din_instante"].min()]
        return pd.concat([usina, coff], ignore_index=True)
    except FileNotFoundError:
        return usina


def _serie_distribuida() -> pd.DataFrame:
    ger = cl.carregar_geracao_por_tipo()
    col = load_config()["carga_liquida"]["tipo_usina_solar"] + " - MMGD"
    if col not in ger.columns:
        raise FileNotFoundError("Sem coluna de solar MMGD no processado; rode `python run.py processar`")
    df = ger[["din_instante", col]].rename(columns={col: "mw"}).dropna()
    return df[df["mw"] > 0]


def treinar() -> dict:
    out = {}
    for nome, serie in (("solar_centralizada", _serie_centralizada), ("solar_distribuida", _serie_distribuida)):
        df = janela_treino(serie())
        perfis = interpolar_meses_faltantes(perfil_proporcional_por_mes(df, "mw"))
        for mes, p in sorted(perfis.items()):
            prop = np.array(p["perfil_proporcional"])
            logger.info(f"  {nome} mês {mes:2d}: {p['n_meses']} meses, pico {int(np.argmax(prop)):2d}h ({100 * prop.max():.1f}%)")
        salvar_json(nome, {"meta": {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}"},
                           "meses": {str(k): v for k, v in perfis.items()}})
        out[nome] = perfis
    return out


class SolarSampler:
    def __init__(self, tipo: str = "centralizada", params: dict | None = None):
        cfg = load_config()["modelo"]
        self.tipo = tipo
        self.shape = cfg[f"solar_{tipo}_shape"]
        p = params or carregar_json(f"solar_{tipo}")["meses"]
        self.p = {int(k): v for k, v in p.items()}

    def perfil(self, mes: int) -> np.ndarray:
        prop = np.array(self.p[mes]["perfil_proporcional"])
        if self.shape != 1.0:
            prop = prop ** self.shape
            prop = prop / prop.sum()
        return prop

    def gerar_dia(self, mes: int, mw_medios: float) -> np.ndarray:
        """24 valores (MW) com média = mw_medios (determinístico)."""
        return self.perfil(mes) * mw_medios * 24
