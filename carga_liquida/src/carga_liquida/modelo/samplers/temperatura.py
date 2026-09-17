"""Sampler de temperatura para meses sem dado real (projeção): anomalia diária + perfil horário típico.

    T_{d,h} = T_mês + A_d + desvio_h(mês)

    A_d = Q_mês(Φ(u_d)),  u_d = ρ·u_{d−1} + ε_d     (cópula gaussiana AR(1) sobre a distribuição EMPÍRICA da anomalia
                                                   diária média do dia − média do mês; constante no dia com transição
                                                   de ±3 h na meia-noite, como o fator diário eólico)

Sem isto, um mês projetado tem todos os dias na temperatura média e o sampler de carga não produz variabilidade
de nível dia a dia (observado: std 0,033 da média do dia / média do mês nos dias úteis, +1,35 % por °C).
A média do mês continua sendo a premissa (climatologia ou observada); só se distribui a anomalia entre os dias.

Treino: `python run.py treinar temperatura` -> params_dir/temperatura.json  (série Meteostat processada)
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

from ...config import get_logger, load_config
from ...dados import temperatura
from ._base import carregar_json, janela_treino, salvar_json
from ._diario import GRADE, TRANSICAO, _ar1

logger = get_logger("sampler.temperatura")
NOME = "temperatura"


def treinar() -> dict:
    df = temperatura.carregar_temperatura().rename(columns={"timestamp": "din_instante"})
    df = janela_treino(df).dropna(subset=["temp_brasil_c"]).sort_values("din_instante")
    df["ym"], df["dia"] = df["din_instante"].dt.to_period("M"), df["din_instante"].dt.normalize()
    df["mes"], df["hora"] = df["din_instante"].dt.month, df["din_instante"].dt.hour
    diario = df.groupby(["ym", "dia"])["temp_brasil_c"].mean().reset_index()
    diario["A"] = diario["temp_brasil_c"] - diario.groupby("ym")["temp_brasil_c"].transform("mean")
    diario["mes"] = diario["dia"].dt.month
    tmes = df.groupby("mes")["temp_brasil_c"].mean()
    desvio_h = df.groupby(["mes", "hora"])["temp_brasil_c"].mean().unstack().sub(tmes, axis=0)
    out = {}
    for mes, g in diario.groupby("mes"):
        g = g.sort_values("dia")
        rho, _ = _ar1(norm.ppf((g["A"].rank().values - 0.5) / len(g)))
        out[int(mes)] = {"rho_a": rho, "quantis_a": np.quantile(g["A"], GRADE).tolist(), "std_a": float(g["A"].std()),
                         "desvio_h": desvio_h.loc[mes].reindex(range(24)).fillna(0.0).tolist(), "n_dias": int(len(g))}
        logger.info(f"  mês {mes:2d}: {len(g)} dias, anomalia diária std {out[mes]['std_a']:.2f} °C  P10/P90 "
                    f"{np.quantile(g['A'], .1):+.2f}/{np.quantile(g['A'], .9):+.2f}  ρ {rho:.2f}")
    meta = {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}", "fonte": "Meteostat (temp_brasil_c)"}
    salvar_json(NOME, {"meta": meta, "meses": {str(k): v for k, v in out.items()}})
    return out


class TemperaturaSampler:
    def __init__(self, params: dict | None = None):
        p = params or carregar_json(NOME)["meses"]
        self.p = {int(k): v for k, v in p.items()}
        self.ativo = load_config()["modelo"].get("temperatura_fator_diario", True)

    def gerar_mes(self, mes: int, temp_media_mensal: float, n_dias: int, rng: np.random.Generator | None = None) -> dict[int, dict[int, float]]:
        """{dia: {hora: temp}} para um mês projetado; média do mês = temp_media_mensal."""
        p = self.p[mes]
        rng = rng or np.random.default_rng()
        desvio = np.array(p["desvio_h"])
        anom = np.zeros((n_dias, 24))
        if self.ativo:
            rho = p["rho_a"]
            u = np.empty(n_dias + 2)
            u[0] = rng.normal()
            for t in range(1, n_dias + 2):
                u[t] = rho * u[t - 1] + rng.normal(0, np.sqrt(1 - rho ** 2))
            A = np.interp(norm.cdf(u), GRADE, p["quantis_a"])
            nos = np.concatenate([[(i * 24 - TRANSICAO, i * 24 + TRANSICAO) for i in range(n_dias + 1)]]).ravel()
            anom = np.interp(np.arange(n_dias * 24), nos, np.repeat(A, 2)[1:-1]).reshape(n_dias, 24)
            anom -= anom.mean()                                   # a média do mês é a premissa
        T = temp_media_mensal + anom + desvio[None, :]
        return {d + 1: {h: float(T[d, h]) for h in range(24)} for d in range(n_dias)}
