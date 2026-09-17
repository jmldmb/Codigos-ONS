"""Sampler solar: perfil horário médio por mês, separado em centralizada e distribuída; opcionalmente um fator
diário D (nebulosidade; _diario.py, `solar_fator_diario`) — std de D 0,06–0,16 (verão) na centralizada, 0,06–0,09 na
distribuída, contra 0,13–0,40 na eólica. Sem ruído intradiário.

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
from . import _diario
from ._base import carregar_json, interpolar_meses_faltantes, janela_treino, perfil_proporcional_por_mes, salvar_json

logger = get_logger("sampler.solar")


def _serie_centralizada() -> pd.DataFrame:
    ger = cl.carregar_geracao_por_tipo()
    tipo = load_config()["carga_liquida"]["tipo_usina_solar"]
    usina = ger[["din_instante", tipo]].rename(columns={tipo: "mw"})
    try:
        coff = ons.carregar_coff_horario("solar")[["din_instante", "potencial_mw"]].rename(columns={"potencial_mw": "mw"})
        usina = usina[usina["din_instante"] < coff["din_instante"].min()]
        return _sem_dias_ruins(pd.concat([usina, coff], ignore_index=True).dropna())
    except FileNotFoundError:
        return _sem_dias_ruins(usina.dropna())


def _serie_distribuida() -> pd.DataFrame:
    ger = cl.carregar_geracao_por_tipo()
    col = load_config()["carga_liquida"]["tipo_usina_solar"] + " - MMGD"
    if col not in ger.columns:
        raise FileNotFoundError("Sem coluna de solar MMGD no processado; rode `python run.py processar`")
    df = ger[["din_instante", col]].rename(columns={col: "mw"}).dropna()
    return _sem_dias_ruins(df[df.groupby(df["din_instante"].dt.normalize())["mw"].transform("max") > 0])


def _sem_dias_ruins(df: pd.DataFrame) -> pd.DataFrame:
    """Remove dias com geração 'à noite' (0–3h acima de 1 % do máximo do dia): artefatos de preenchimento do ONS
    (ex.: MMGD 2024-11-10, 7.949 MW constantes de 0h a 7h). Os zeros noturnos legítimos FICAM na série — descartá-los
    (legado: `mw > 0`) fazia a média noturna virar a média dos poucos artefatos e o perfil de novembro ganhar 1,0 à noite."""
    dia = df["din_instante"].dt.normalize()
    noite = df[df["din_instante"].dt.hour <= 3].groupby(dia[df["din_instante"].dt.hour <= 3])["mw"].max()
    mx = df.groupby(dia)["mw"].max()
    ruins = noite.index[noite > 0.01 * mx.reindex(noite.index)]
    if len(ruins):
        logger.info(f"  {len(ruins)} dia(s) com geração noturna descartado(s): {[d.strftime('%Y-%m-%d') for d in ruins[:5]]}")
    return df[~dia.isin(ruins)]


def treinar() -> dict:
    out = {}
    for nome, serie in (("solar_centralizada", _serie_centralizada), ("solar_distribuida", _serie_distribuida)):
        df = janela_treino(serie())
        perfis = perfil_proporcional_por_mes(df, "mw")
        din = _diario.estimar(df, "mw", perfis)
        perfis = interpolar_meses_faltantes({m: {**p, **din.get(m, {})} for m, p in perfis.items()})
        for k in ("rho_d", "std_d"):
            media = float(np.mean([v[k] for v in perfis.values() if k in v]))
            for m in perfis:
                perfis[m].setdefault(k, media)
        for m in perfis:
            perfis[m].setdefault("quantis_d", next(v["quantis_d"] for v in perfis.values() if "quantis_d" in v))
        for mes, p in sorted(perfis.items()):
            prop = np.array(p["perfil_proporcional"])
            logger.info(f"  {nome} mês {mes:2d}: {p['n_meses']} meses, pico {int(np.argmax(prop)):2d}h ({100 * prop.max():.1f}%), "
                        f"D: std {p['std_d']:.2f} ρ {p['rho_d']:.2f}")
        salvar_json(nome, {"meta": {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}"},
                           "meses": {str(k): v for k, v in perfis.items()}})
        out[nome] = perfis
    return out


class SolarSampler:
    def __init__(self, tipo: str = "centralizada", params: dict | None = None):
        cfg = load_config()["modelo"]
        self.tipo = tipo
        self.shape = cfg[f"solar_{tipo}_shape"]
        self.fator_diario = cfg.get("solar_fator_diario", False)
        p = params or carregar_json(f"solar_{tipo}")["meses"]
        self.p = {int(k): v for k, v in p.items()}
        if self.fator_diario and "quantis_d" not in next(iter(self.p.values())):
            raise FileNotFoundError(f"Parâmetros solar_{tipo} sem fator diário. Rode: python run.py treinar solar")

    def perfil(self, mes: int) -> np.ndarray:
        prop = np.array(self.p[mes]["perfil_proporcional"])
        prop = np.where(prop < 0.005 * prop.max(), 0.0, prop)     # resíduo noturno da referência COFF (poucos MW) -> 0
        if self.shape != 1.0:
            prop = prop ** self.shape
        return prop / prop.sum()

    def gerar_dia(self, mes: int, mw_medios: float) -> np.ndarray:
        """24 valores (MW) com média = mw_medios (determinístico)."""
        return self.perfil(mes) * mw_medios * 24

    def gerar_mes(self, mes: int, mw_medios: float, n_dias: int, rng: np.random.Generator | None = None) -> np.ndarray:
        """Matriz (n_dias, 24) em MW com média do mês = mw_medios; fator diário só se `solar_fator_diario`."""
        if not self.fator_diario:
            return np.tile(self.gerar_dia(mes, mw_medios), (n_dias, 1))
        return _diario.gerar_mes(self.perfil(mes), self.p[mes], mw_medios, n_dias, rng or np.random.default_rng(), ruido=False, aditivo=False)
