"""Sampler eólico: perfil horário médio por mês × ruído AR(1) multiplicativo.

    Y_h = μ_h · (1 + Z_h),   Z_h = φ·Z_{h-1} + ε_h,  ε ~ N(0, σ²)

Treino (como no legado): μ_h por mês vem do POTENCIAL eólico do SIN (geração + corte, dataset COFF),
pois o despacho aplica o curtailment depois. φ e σ por mês são estimados nos resíduos normalizados
dos perfis de cada mês-ano em relação ao perfil médio do mês.
"""
import numpy as np
import pandas as pd

from ...config import get_logger
from ...dados import ons
from ._base import carregar_json, interpolar_meses_faltantes, janela_treino, perfil_proporcional_por_mes, salvar_json

logger = get_logger("sampler.eolica")
NOME = "eolica"


def _estimar_ar1(x: np.ndarray) -> tuple[float, float]:
    x = x - x.mean()
    if len(x) < 3:
        return 0.0, float(np.std(x)) if len(x) else 0.0
    phi = float(np.clip(np.corrcoef(x[:-1], x[1:])[0, 1], -0.99, 0.99))
    res = x[1:] - phi * x[:-1] if abs(phi) > 0.01 else x
    return phi, float(np.std(res))


def treinar() -> dict:
    df = janela_treino(ons.carregar_coff_horario("eolica"))
    perfis = perfil_proporcional_por_mes(df, "potencial_mw")
    df["mes"], df["hora"], df["ym"] = df["din_instante"].dt.month, df["din_instante"].dt.hour, df["din_instante"].dt.to_period("M")
    params = {}
    for mes, p in perfis.items():
        mu = np.array(p["perfil_absoluto"])
        res = []
        for _, g in df[df["mes"] == mes].groupby("ym"):
            perfil_ym = g.groupby("hora")["potencial_mw"].mean().reindex(range(24)).fillna(0.0).values
            res.extend(((perfil_ym - mu) / (mu + 1e-10)).tolist())
        phi, sigma = _estimar_ar1(np.array(res))
        params[mes] = {**p, "phi": phi, "sigma_epsilon": sigma}
        logger.info(f"  mês {mes:2d}: {p['n_meses']} meses, pico {int(np.argmax(mu)):2d}h, φ={phi:.3f} σ={sigma:.4f}")
    params = interpolar_meses_faltantes(params)
    for mes in params:
        params[mes].setdefault("phi", float(np.mean([v["phi"] for v in params.values() if "phi" in v])))
        params[mes].setdefault("sigma_epsilon", float(np.mean([v["sigma_epsilon"] for v in params.values() if "sigma_epsilon" in v])))
    meta = {"fonte": "COFF eólica: potencial = geração + corte (SIN)", "periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}"}
    salvar_json(NOME, {"meta": meta, "meses": {str(k): v for k, v in params.items()}})
    return params


class EolicaSampler:
    def __init__(self, params: dict | None = None):
        p = params or carregar_json(NOME)["meses"]
        self.p = {int(k): v for k, v in p.items()}

    def ruido_ar1(self, phi: float, sigma: float, n: int, rng: np.random.Generator) -> np.ndarray:
        z = np.zeros(n)
        z[0] = rng.normal(0, sigma / np.sqrt(1 - phi ** 2) if abs(phi) < 1 else sigma)
        for t in range(1, n):
            z[t] = phi * z[t - 1] + rng.normal(0, sigma)
        return z

    def gerar_dia(self, mes: int, mw_medios: float, rng: np.random.Generator | None = None,
                  deterministico: bool = False) -> np.ndarray:
        """24 valores (MW) com média = mw_medios."""
        p = self.p[mes]
        base = np.array(p["perfil_proporcional"]) * mw_medios * 24
        if deterministico:
            return base
        rng = rng or np.random.default_rng()
        y = np.maximum(base * (1 + self.ruido_ar1(p["phi"], p["sigma_epsilon"], 24, rng)), 0)
        return y * (mw_medios * 24 / y.sum()) if y.sum() > 0 else base
