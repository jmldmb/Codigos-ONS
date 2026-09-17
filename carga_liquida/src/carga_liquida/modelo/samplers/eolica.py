"""Sampler eólico: perfil horário médio por mês × fator diário × ruído AR(1) horário (ver _diario.py).

    Y_{d,h} = μ_h(mês) · D_d · (1 + Z_{d,h})

Treino: μ_h por mês vem do POTENCIAL eólico do SIN (geração + corte, dataset COFF), pois o corte de rede sai
antes do despacho e o energético o despacho decide. D (fator diário: cópula gaussiana AR(1), ρ ≈ 0,4–0,8, sobre a distribuição empírica do mês, std 0,13–0,40) e Z (AR(1) horário, φ ≈ 0,95, σ ≈ 0,08) são estimados nos dias observados. O legado renormalizava
cada dia à média do mês (D ≡ 1) e estimava φ/σ nos perfis médios mês a mês (σ ≈ 0,02).
"""
import numpy as np

from ...config import get_logger, load_config
from ...dados import ons
from . import _diario
from ._base import carregar_json, interpolar_meses_faltantes, janela_treino, perfil_proporcional_por_mes, salvar_json

logger = get_logger("sampler.eolica")
NOME = "eolica"


def treinar() -> dict:
    df = janela_treino(ons.carregar_coff_horario("eolica"))
    perfis = perfil_proporcional_por_mes(df, "potencial_mw")
    din = _diario.estimar(df, "potencial_mw", perfis)
    params = {}
    for mes, p in perfis.items():
        params[mes] = {**p, **din.get(mes, {})}
        d = params[mes]
        logger.info(f"  mês {mes:2d}: {p['n_meses']} meses, pico {int(np.argmax(p['perfil_absoluto'])):2d}h, "
                    f"D: std {d.get('std_d', 0):.2f} ρ {d.get('rho_d', 0):.2f} | "
                    f"Z: φ {d.get('phi_z', 0):.2f} σ {d.get('sigma_z', 0):.3f}")
    params = interpolar_meses_faltantes(params)
    for k in ("rho_d", "std_d", "phi_z", "sigma_z"):
        media = float(np.mean([v[k] for v in params.values() if k in v]))
        for mes in params:
            params[mes].setdefault(k, media)
    for mes in params:                                   # meses interpolados: quantis do mês vizinho com dado
        params[mes].setdefault("quantis_d", next(v["quantis_d"] for v in params.values() if "quantis_d" in v))
    meta = {"fonte": "COFF eólica: potencial = geração + corte (SIN)", "periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}"}
    salvar_json(NOME, {"meta": meta, "meses": {str(k): v for k, v in params.items()}})
    return params


class EolicaSampler:
    def __init__(self, params: dict | None = None, fator_diario: bool | None = None):
        p = params or carregar_json(NOME)["meses"]
        self.p = {int(k): v for k, v in p.items()}
        if "quantis_d" not in next(iter(self.p.values())):
            raise FileNotFoundError("Parâmetros eólicos sem fator diário. Rode: python run.py treinar eolica")
        cfg = load_config()["modelo"]
        self.fator_diario = cfg.get("eolica_fator_diario", True) if fator_diario is None else fator_diario

    def gerar_mes(self, mes: int, mw_medios: float, n_dias: int, rng: np.random.Generator | None = None,
                  teto: float | None = None, retornar_eps: bool = False):
        """Matriz (n_dias, 24) em MW com média do mês = mw_medios; `teto` = capacidade instalada (MW), opcional.
        `retornar_eps=True` devolve (y, eps) — as inovações do fator diário, para o choque comum com a solar."""
        p = self.p[mes]
        return _diario.gerar_mes(p["perfil_proporcional"], p, mw_medios, n_dias, rng or np.random.default_rng(),
                                 fator_diario=self.fator_diario, teto=teto, retornar_eps=retornar_eps)

    def rho(self, mes: int) -> float:
        return float(self.p[mes]["rho_d"])

    def gerar_dia(self, mes: int, mw_medios: float, rng: np.random.Generator | None = None,
                  deterministico: bool = False) -> np.ndarray:
        """24 valores (MW) com média = mw_medios (um dia isolado, sem fator diário)."""
        p = self.p[mes]
        if deterministico:
            return np.array(p["perfil_proporcional"]) * mw_medios * 24
        return _diario.gerar_mes(p["perfil_proporcional"], p, mw_medios, 1, rng or np.random.default_rng(), fator_diario=False)[0]
