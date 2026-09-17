"""Fator diário D e ruído intradiário Z, comuns à eólica e à solar.

    Y_{d,h} = μ_h(mês) · D_d · (1 + Z_{d,h})

    D_d = Q_mês(Φ(u_d)),  u_d = ρ·u_{d−1} + ε_d       (cópula gaussiana: AR(1) normal padrão mapeado na distribuição
                                                       EMPÍRICA de D do mês; regime de vento dura dias, ρ ≈ 0,4–0,8)
    Z_t = φ·Z_{t−1} + η_t,   η ~ N(0, σ_Z²)             (AR(1) horário, contínuo entre os dias do mês)

D = média do dia / média do mês, estimado da série diária observada por mês; a marginal é a empírica (quantis) porque
D é limitado pela capacidade instalada — uma lognormal com o mesmo desvio dava P99 de 2,6 em fevereiro contra máximo
observado de 1,9. Z = resíduo hora a hora contra μ_h·D_d. A média dos dias do MÊS é renormalizada à premissa (antes
cada dia era renormalizado: todo dia simulado tinha exatamente a média do mês — a eólica observada tem P10/P90 de D
em 0,5/1,5 no verão).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

GRADE = np.linspace(0, 1, 41)  # quantis guardados por mês


def _ar1(x: np.ndarray) -> tuple[float, float]:
    x = x - x.mean()
    if len(x) < 3:
        return 0.0, float(np.std(x)) if len(x) else 0.0
    phi = float(np.clip(np.corrcoef(x[:-1], x[1:])[0, 1], -0.99, 0.99))
    return phi, float(np.std(x[1:] - phi * x[:-1]))


def estimar(df: pd.DataFrame, col: str, perfis: dict) -> dict:
    """Por mês: {'rho_d', 'quantis_d', 'std_d', 'phi_z', 'sigma_z', 'n_dias'} a partir da série horária observada
    (`din_instante`, col) e dos perfis absolutos μ_h por mês (perfil_proporcional_por_mes)."""
    d = df.dropna(subset=[col]).sort_values("din_instante").copy()
    d["ym"], d["dia"] = d["din_instante"].dt.to_period("M"), d["din_instante"].dt.normalize()
    d["mes"], d["hora"] = d["din_instante"].dt.month, d["din_instante"].dt.hour
    diario = d.groupby(["ym", "dia"])[col].mean().reset_index()
    diario["D"] = diario[col] / diario.groupby("ym")[col].transform("mean")
    diario["mes"] = diario["dia"].dt.month
    d = d.merge(diario[["dia", "D"]], on="dia")
    d["mu"] = [perfis[m]["perfil_absoluto"][h] if m in perfis and perfis[m].get("perfil_absoluto") else np.nan
               for m, h in zip(d["mes"], d["hora"])]
    d["z"] = d[col] / (d["mu"] * d["D"]).replace(0, np.nan) - 1
    out = {}
    for mes, g in diario.groupby("mes"):
        g = g.sort_values("dia")
        scores = norm.ppf((g["D"].rank().values - 0.5) / len(g))        # escores normais (cópula gaussiana)
        rho, _ = _ar1(scores)
        z = d.loc[(d["mes"] == mes), "z"].dropna().clip(-1, 5).values
        phi, sz = _ar1(z)
        out[int(mes)] = {"rho_d": rho, "quantis_d": np.quantile(g["D"], GRADE).tolist(), "std_d": float(g["D"].std()),
                         "phi_z": phi, "sigma_z": sz, "n_dias": int(len(g))}
    return out


def gerar_mes(perfil_prop: np.ndarray, p: dict, mw_medios: float, n_dias: int, rng: np.random.Generator,
              fator_diario: bool = True, ruido: bool = True) -> np.ndarray:
    """Matriz (n_dias, 24) em MW com média do mês = mw_medios."""
    mu = np.asarray(perfil_prop) * mw_medios * 24
    D = np.ones(n_dias)
    if fator_diario and p.get("quantis_d"):
        rho = p["rho_d"]
        u = np.empty(n_dias)
        u[0] = rng.normal()
        for t in range(1, n_dias):
            u[t] = rho * u[t - 1] + rng.normal(0, np.sqrt(1 - rho ** 2))
        D = np.interp(norm.cdf(u), GRADE, p["quantis_d"])
    Z = np.zeros(n_dias * 24)
    if ruido and p.get("sigma_z", 0) > 0:
        phi, sz = p["phi_z"], p["sigma_z"]
        Z[0] = rng.normal(0, sz / np.sqrt(1 - phi ** 2))
        for t in range(1, len(Z)):
            Z[t] = phi * Z[t - 1] + rng.normal(0, sz)
    Z = Z.reshape(n_dias, 24)
    Z -= Z.mean(axis=1, keepdims=True)                  # o nível do dia é do D; Z só redistribui dentro do dia (como na estimação)
    y = np.maximum(mu[None, :] * D[:, None] * (1 + Z), 0.0)
    return y * (mw_medios / y.mean()) if y.mean() > 0 else np.tile(mu, (n_dias, 1))
