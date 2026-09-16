"""Validação: carga líquida observada vs simulada, componente a componente.

Substitui os 13 scripts de comparação/backtest do carga_liquida antigo. Alinha por hora a média dos
cenários simulados com o observado e mede erro por componente:

    carga (balanço)  eólica pós-corte  solar pós-corte  hidro FD  hidro R  térmica flexível  carga líquida

Saídas em Output/validacao/: comparacao_horaria.csv, metricas.csv, metricas_por_ano_mes.csv e gráficos.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from ..config import MESES_PT, get_logger, load_config, output_dir  # noqa: E402
from ..dados import ons  # noqa: E402
from ..modelo import simulacao  # noqa: E402
from ..observado import carga_liquida as cl  # noqa: E402

logger = get_logger("validacao")

# (rótulo, coluna observada, coluna simulada)
COMPONENTES = [
    ("carga", "carga_obs", "val_carga"),
    ("eolica", "eolica_obs", "val_gereolica_depois_corte"),
    ("solar", "solar_obs", "val_gersolar_depois_corte"),
    ("hidro_fd", "FD", "val_gerhidro_fd"),
    ("hidro_r", "R", "val_gerhidro_reservatorio"),
    ("termica_flex", "termica_flexivel", "val_term_despacho"),
    ("carga_liquida", "carga_liquida_historica", "carga_liquida"),
]


def montar_comparacao() -> pd.DataFrame:
    """Uma linha por hora com observado e simulado (média, P10, P90 dos cenários)."""
    obs = cl.carregar_historico()
    ger = cl.carregar_geracao_por_tipo()
    tipo_solar = load_config()["carga_liquida"]["tipo_usina_solar"]
    solar_cols = [c for c in ger.columns if c.startswith(tipo_solar)]
    ger = ger.assign(eolica_obs=ger["EOLIELÉTRICA"], solar_obs=ger[solar_cols].fillna(0).sum(axis=1))[["din_instante", "eolica_obs", "solar_obs"]]
    bal = ons.carregar_balanco()
    if load_config()["modelo"].get("carga_inclui_intercambio", True):
        bal = bal.assign(val_carga=bal["val_carga"] + bal["val_intercambio"].fillna(0.0))
    bal = bal[["din_instante", "val_carga"]].rename(columns={"val_carga": "carga_obs"})
    obs = obs.merge(ger, on="din_instante", how="left").merge(bal, on="din_instante", how="left")

    sim = simulacao.carregar_resultados()
    cols_sim = [c for _, _, c in COMPONENTES] + ["curtailment", "pld"]
    agg = sim.groupby("din_instante")[cols_sim].mean()
    q = sim.groupby("din_instante")["carga_liquida"].quantile([0.1, 0.9]).unstack()
    agg["carga_liquida_p10"], agg["carga_liquida_p90"] = q[0.1], q[0.9]
    agg["n_cenarios"] = sim.groupby("din_instante")["simulacao"].nunique()
    df = obs.merge(agg.reset_index(), on="din_instante", how="inner")
    for rot, o, s in COMPONENTES:
        df[f"erro_{rot}"] = df[s] - df[o]
    df["dia_semana"] = df["din_instante"].dt.dayofweek
    return df


def _metricas(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for rot, o, s in COMPONENTES:
        d = df.dropna(subset=[o, s])
        if d.empty:
            continue
        e = d[s] - d[o]
        rows.append({"componente": rot, "obs_medio": d[o].mean(), "sim_medio": d[s].mean(), "bias_mw": e.mean(),
                     "mae_mw": e.abs().mean(), "rmse_mw": np.sqrt((e ** 2).mean()),
                     "mae_pct_media": e.abs().mean() / abs(d[o].mean()) * 100,  # MAE relativo à média observada
                     "r2": 1 - (e ** 2).sum() / ((d[o] - d[o].mean()) ** 2).sum() if d[o].std() > 0 else np.nan,
                     "n": len(d)})
    return pd.DataFrame(rows)


def validar():
    g = load_config()["graficos"]
    df = montar_comparacao()
    out = output_dir("validacao")
    logger.info(f"{len(df):,} horas comparáveis ({df['din_instante'].min():%Y-%m} a {df['din_instante'].max():%Y-%m}), "
                f"{int(df['n_cenarios'].iloc[0])} cenários")
    df.to_csv(out / "comparacao_horaria.csv", index=False)

    met = _metricas(df)
    met.to_csv(out / "metricas.csv", index=False)
    for r in met.itertuples():
        logger.info(f"  {r.componente:<14} obs {r.obs_medio:8,.0f}  sim {r.sim_medio:8,.0f}  viés {r.bias_mw:+7,.0f}  "
                    f"MAE {r.mae_mw:6,.0f} ({r.mae_pct_media:4.1f}% da média)  R² {r.r2:5.3f}")
    por_mes = pd.concat([_metricas(d).assign(ano=a, mes=m) for (a, m), d in df.groupby(["ano", "mes"])], ignore_index=True)
    por_mes.to_csv(out / "metricas_por_ano_mes.csv", index=False)

    # 1. médias mensais observado vs simulado, por componente
    mens = df.groupby(["ano", "mes"]).mean(numeric_only=True).reset_index()
    mens["t"] = pd.to_datetime(mens[["ano", "mes"]].assign(day=1).rename(columns={"ano": "year", "mes": "month"}))
    fig, axes = plt.subplots(4, 2, figsize=(18, 18))
    fig.suptitle("Médias mensais: observado vs simulado", fontsize=16, fontweight="bold")
    for ax, (rot, o, s) in zip(axes.flatten(), COMPONENTES):
        ax.plot(mens["t"], mens[o], "o-", color="black", label="observado")
        ax.plot(mens["t"], mens[s], "s--", color="tab:red", label="simulado")
        ax.set(title=rot, ylabel="MW")
        ax.legend()
    ax = axes.flatten()[-1]
    ax.plot(mens["t"], mens["curtailment"], "s--", color="tab:red", label="curtailment simulado")
    ax.set(title="curtailment (simulado)", ylabel="MW")
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "medias_mensais.png", dpi=g["dpi"], bbox_inches="tight")
    plt.close(fig)

    # 2. perfil horário da carga líquida por mês
    fig, axes = plt.subplots(3, 4, figsize=(20, 12))
    fig.suptitle("Carga líquida: perfil horário médio por mês (observado vs simulado, faixa P10–P90)", fontsize=15, fontweight="bold")
    for ax, mes in zip(axes.flatten(), range(1, 13)):
        d = df[df["mes"] == mes].groupby("hora")[["carga_liquida_historica", "carga_liquida", "carga_liquida_p10", "carga_liquida_p90"]].mean()
        if d.empty:
            ax.set_title(f"{MESES_PT[mes]} (sem dados)")
            continue
        ax.fill_between(d.index, d["carga_liquida_p10"], d["carga_liquida_p90"], color="tab:red", alpha=0.15, label="sim P10–P90")
        ax.plot(d.index, d["carga_liquida_historica"], color="black", lw=2, label="observado")
        ax.plot(d.index, d["carga_liquida"], color="tab:red", lw=2, ls="--", label="simulado")
        ax.set(title=MESES_PT[mes], xlabel="hora", ylabel="MW", xticks=range(0, 24, 4))
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out / "perfil_horario_carga_liquida.png", dpi=g["dpi"], bbox_inches="tight")
    plt.close(fig)

    # 3. dispersão observado vs simulado (carga líquida e R)
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    for ax, (rot, o, s) in zip(axes, [COMPONENTES[6], COMPONENTES[4]]):
        d = df.dropna(subset=[o, s])
        ax.scatter(d[o], d[s], s=6, alpha=0.25, c=d["ano"], cmap="viridis")
        lim = [min(d[o].min(), d[s].min()), max(d[o].max(), d[s].max())]
        ax.plot(lim, lim, "k--", lw=1)
        m = met.set_index("componente").loc[rot]
        ax.set(title=f"{rot}: R² {m.r2:.3f}, viés {m.bias_mw:+,.0f} MW, MAE {m.mae_mw:,.0f} MW",
               xlabel="observado (MW)", ylabel="simulado (MW)")
    fig.tight_layout()
    fig.savefig(out / "dispersao_obs_sim.png", dpi=g["dpi"], bbox_inches="tight")
    plt.close(fig)

    # 4. decomposição do erro da carga líquida por componente (média mensal do erro)
    # CL = carga − eólica − solar − inflex − FD  =>  erro_CL ≈ erro_carga − erro_eólica − erro_solar − erro_FD (inflex fixo)
    dec = df.groupby(["ano", "mes"])[["erro_carga", "erro_eolica", "erro_solar", "erro_hidro_fd", "erro_carga_liquida"]].mean().reset_index()
    dec["t"] = pd.to_datetime(dec[["ano", "mes"]].assign(day=1).rename(columns={"ano": "year", "mes": "month"}))
    contrib = pd.DataFrame({"carga": dec["erro_carga"], "eólica (−)": -dec["erro_eolica"], "solar (−)": -dec["erro_solar"],
                            "hidro FD (−)": -dec["erro_hidro_fd"]}, index=dec["t"])
    fig, ax = plt.subplots(figsize=(18, 7))
    contrib.plot(kind="bar", stacked=True, ax=ax, width=0.8, colormap="tab10")
    ax.plot(range(len(dec)), dec["erro_carga_liquida"], "ko-", label="erro carga líquida (sim − obs)")
    ax.set(title="Decomposição do erro médio mensal da carga líquida por componente", ylabel="MW",
           xticks=range(len(dec)), xticklabels=[t.strftime("%Y-%m") for t in dec["t"]])
    ax.tick_params(axis="x", rotation=90, labelsize=7)
    ax.axhline(0, color="black", lw=0.8)
    ax.legend()
    fig.tight_layout()
    fig.savefig(out / "decomposicao_erro.png", dpi=g["dpi"], bbox_inches="tight")
    plt.close(fig)

    # 5. erro por hora e por tipo de dia
    df["fds"] = np.where(df["dia_semana"] >= 5, "FDS", "DU")
    eh = df.groupby(["fds", "hora"])["erro_carga_liquida"].agg(["mean", lambda s: s.abs().mean()]).unstack(0)
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    eh["mean"].plot(ax=axes[0], marker="o")
    axes[0].axhline(0, color="black", lw=0.8)
    axes[0].set(title="Viés da carga líquida por hora (sim − obs)", ylabel="MW", xlabel="hora")
    eh["<lambda_0>"].plot(ax=axes[1], marker="o")
    axes[1].set(title="Erro absoluto médio por hora", ylabel="MW", xlabel="hora")
    fig.tight_layout()
    fig.savefig(out / "erro_por_hora.png", dpi=g["dpi"], bbox_inches="tight")
    plt.close(fig)
    logger.info(f"saídas em {out}")
    return met
