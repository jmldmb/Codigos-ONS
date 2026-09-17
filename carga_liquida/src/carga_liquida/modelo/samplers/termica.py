"""Modulação horária da térmica flexível "base" (premissa mensal exógena).

A quantidade mensal de térmica flexível é decisão energética do operador e entra como premissa
(observada no histórico; cenário do usuário em config/projecoes.yaml). Aqui só se distribui
essa média nas 24 horas:

    flat       perfil constante (= média mensal em todas as horas)
    observado  perfil médio por (mês, tipo de dia, hora) da térmica flexível observada, normalizado
               a média 1; meses com pouca térmica caem para flat

Treino: `python run.py treinar termica` -> params_dir/termica_flex.json
"""
import numpy as np

from ...config import get_logger, load_config
from ...observado import carga_liquida as cl
from .. import feriados
from ._base import carregar_json, janela_treino, salvar_json

logger = get_logger("sampler.termica")
NOME = "termica_flex"
MIN_MW_PERFIL = 300  # abaixo desta média mensal o perfil observado é ruído -> flat


def treinar() -> dict:
    df = janela_treino(cl.carregar_historico())
    df["tipo_dia"] = df["din_instante"].dt.date.map(feriados.tipo_dia)
    df["media_mes"] = df.groupby(["ano", "mes"])["termica_flexivel"].transform("mean")
    d = df[df["media_mes"] >= MIN_MW_PERFIL].copy()
    d["norm"] = d["termica_flexivel"] / d["media_mes"]
    perfis = {}
    for (mes, tipo), g in d.groupby(["mes", "tipo_dia"]):
        p = g.groupby("hora")["norm"].mean().reindex(range(24)).fillna(1.0).values
        perfis[f"{mes}|{tipo}"] = {"perfil": (p / p.mean()).tolist(), "n_meses": int(g["din_instante"].dt.to_period("M").nunique())}
    faltantes = [(m, t) for m in range(1, 13) for t in ("DU", "FDS") if f"{m}|{t}" not in perfis]
    logger.info(f"perfis treinados: {len(perfis)} (mês×tipo); sem dado suficiente (ficam flat): {faltantes}")
    meta = {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}", "min_mw_perfil": MIN_MW_PERFIL,
            "amplitude_media": float(np.mean([max(v["perfil"]) - min(v["perfil"]) for v in perfis.values()])) if perfis else 0.0}
    salvar_json(NOME, {"meta": meta, "perfis": perfis})
    return perfis


class TermicaSampler:
    def __init__(self, modo: str | None = None, params: dict | None = None):
        self.modo = modo or load_config()["modelo"]["termica_flexivel_perfil"]
        self.perfis = {}
        if self.modo == "observado":
            self.perfis = (params or carregar_json(NOME))["perfis"]

    def gerar_dia(self, mes: int, tipo_dia: str, mw_medios: float) -> np.ndarray:
        """24 valores (MW) com média = mw_medios."""
        if mw_medios <= 0:
            return np.zeros(24)
        p = self.perfis.get(f"{mes}|{tipo_dia}")
        if self.modo != "observado" or p is None:
            return np.full(24, float(mw_medios))
        return mw_medios * np.array(p["perfil"])
