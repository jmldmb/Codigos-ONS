"""Fator diário D e ruído intradiário Z, comuns à eólica e à solar.

    Y_{d,h} = M · [ p_h(mês) + (D_d − 1) + Z_{d,h} ]        M = média do mês (premissa), p_h = perfil normalizado (média 1)

    D_d = Q_mês(Φ(u_d)),  u_d = ρ·u_{d−1} + ε_d       (cópula gaussiana: AR(1) normal padrão mapeado na distribuição
                                                       EMPÍRICA de D do mês; regime de vento dura dias, ρ ≈ 0,4–0,8)
    Z_t = φ·Z_{t−1} + η_t,   η ~ N(0, σ_Z²)             (AR(1) horário, contínuo entre os dias do mês, média zero no dia)

O nível do dia entra ADITIVAMENTE, não como fator: a amplitude diurna em MW (jato noturno / brisa no NE) não depende de
quanto ventou na média do dia — perfil y/M por tercil de D é o mesmo deslocado (~0,55) em todas as horas e o resíduo
aditivo tem std constante (0,12–0,16) enquanto o multiplicativo vai de 0,24 (dias fracos) a 0,13 (fortes). Multiplicar
μ_h·D·(1+Z) estourava a capacidade instalada (43,8 GW simulados vs 29,5 observados). D é constante no dia com transição
linear de ±3 h na meia-noite (o salto observado 0h vs 23h é igual ao de qualquer hora; interpolar entre meios-dias
encolhia a variância de D). D = média do dia / média do
mês, estimado da série diária por mês; a marginal é a empírica (quantis) porque D é limitado pela capacidade instalada.
A média dos dias do MÊS é renormalizada à premissa (antes cada dia era renormalizado: todo dia simulado tinha
exatamente a média do mês — a eólica observada tem P10/P90 de D em 0,5/1,5 no verão).
"""
import numpy as np
import pandas as pd
from scipy.stats import norm

GRADE = np.linspace(0, 1, 41)  # quantis guardados por mês
TRANSICAO = 3                  # horas de transição do nível diário de cada lado da meia-noite


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
    d["M"] = d.groupby("ym")[col].transform("mean")
    d["p"] = [perfis[m]["perfil_proporcional"][h] * 24 if m in perfis and perfis[m].get("perfil_proporcional") else np.nan
              for m, h in zip(d["mes"], d["hora"])]
    d["z"] = d[col] / d["M"].replace(0, np.nan) - d["p"] - (d["D"] - 1)          # resíduo aditivo, em fração da média do mês
    out = {}
    for mes, g in diario.groupby("mes"):
        g = g.sort_values("dia")
        scores = norm.ppf((g["D"].rank().values - 0.5) / len(g))        # escores normais (cópula gaussiana)
        rho, _ = _ar1(scores)
        z = d.loc[(d["mes"] == mes), "z"].dropna().clip(-2, 2).values
        phi, sz = _ar1(z)
        out[int(mes)] = {"rho_d": rho, "quantis_d": np.quantile(g["D"], GRADE).tolist(), "std_d": float(g["D"].std()),
                         "phi_z": phi, "sigma_z": sz, "n_dias": int(len(g))}
    return out


def gerar_mes(perfil_prop: np.ndarray, p: dict, mw_medios: float, n_dias: int, rng: np.random.Generator,
              fator_diario: bool = True, ruido: bool = True, aditivo: bool = True, teto: float | None = None) -> np.ndarray:
    """Matriz (n_dias, 24) em MW com média do mês = mw_medios. `aditivo=False` (solar): Y = M · p_h · D — nebulosidade
    escala o dia inteiro, e um deslocamento aditivo criaria geração à noite. `teto` (MW): limite físico horário
    (capacidade instalada); o corte é redistribuído pela renormalização do mês."""
    perfil = np.asarray(perfil_prop) * 24                                       # média 1
    nivel = np.zeros((n_dias, 24))
    if fator_diario and p.get("quantis_d"):
        rho = p["rho_d"]
        u = np.empty(n_dias + 2)                                                # um dia extra em cada ponta para interpolar
        u[0] = rng.normal()
        for t in range(1, n_dias + 2):
            u[t] = rho * u[t - 1] + rng.normal(0, np.sqrt(1 - rho ** 2))
        D = np.interp(norm.cdf(u), GRADE, p["quantis_d"])
        # nível constante no dia (preserva a distribuição de D), com transição linear de ±TRANSICAO h em torno da meia-noite
        horas = np.arange(n_dias * 24)
        nos = np.concatenate([[(i * 24 - TRANSICAO, i * 24 + TRANSICAO) for i in range(n_dias + 1)]]).ravel()
        vals = np.repeat(D - 1, 2)[1:-1]
        nivel = np.interp(horas, nos, vals).reshape(n_dias, 24)
    Z = np.zeros(n_dias * 24)
    if ruido and p.get("sigma_z", 0) > 0:
        phi, sz = p["phi_z"], p["sigma_z"]
        Z[0] = rng.normal(0, sz / np.sqrt(1 - phi ** 2))
        for t in range(1, len(Z)):
            Z[t] = phi * Z[t - 1] + rng.normal(0, sz)
    # o nível do dia é do D; Z só redistribui dentro do dia (como na estimação): tira a média móvel de 24 h (contínua,
    # sem degrau à meia-noite que a média por dia-calendário criaria)
    Z = (Z - np.convolve(np.pad(Z, 12, mode="reflect"), np.ones(24) / 24, mode="valid")[:len(Z)]).reshape(n_dias, 24)
    y = np.maximum(mw_medios * ((perfil[None, :] + nivel + Z) if aditivo else perfil[None, :] * (1 + nivel) * (1 + Z)), 0.0)
    if y.mean() <= 0:
        return np.tile(perfil * mw_medios, (n_dias, 1))
    y *= mw_medios / y.mean()
    if teto is not None and np.isfinite(teto) and teto > 0 and y.max() > teto:
        for _ in range(3):                                   # cortar no teto e recompor a média do mês (converge em 2-3 passos)
            y = np.minimum(y, teto)
            y *= min(mw_medios / y.mean(), teto / max(y.max(), 1e-9))
    return y
