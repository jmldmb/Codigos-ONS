"""Análises e gráficos da carga líquida observada.

Cada função pública é uma análise independente, lê o processado (Output/observado/) e
escreve em Output/<analise>/. São chamadas pelo CLI: `python run.py analisar [nome ...]`.

    hidro        FD vs R: mensal, dia da semana, horário, distribuições, séries, relatório
    cmo          carga líquida x CMO (subsistema config.carga_liquida.cmo_subsistema)
    diarios      últimos N dias: despacho térmico por componente e geração por tipo + carga líquida
    curtailment  carga líquida x curtailment eólico+solar (constrained-off)
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from scipy import stats  # noqa: E402

from ..config import DIAS_SEMANA_PT, MESES_PT, get_logger, load_config, output_dir  # noqa: E402
from ..dados import ons  # noqa: E402
from . import carga_liquida as cl  # noqa: E402

logger = get_logger("analises")
sns.set_style("whitegrid")
COR_FD, COR_R = "steelblue", "coral"


def _salvar(fig, out, nome):
    fig.tight_layout()
    fig.savefig(out / nome, dpi=load_config()["graficos"]["dpi"], bbox_inches="tight")
    plt.close(fig)
    logger.info(f"  {out.name}/{nome}")


def _com_tempo(df):
    df = df.copy()
    df["dia_semana"] = df["din_instante"].dt.dayofweek
    df["data"] = df["din_instante"].dt.date
    return df


# ----------------------------------------------------------------------------- hidro
def hidro():
    """Hidrelétricas fio d'água (FD) vs reservatório (R)."""
    df = _com_tempo(cl.carregar_historico())
    out = output_dir("hidro_reservatorio")

    # 1. mensal: série por ano, média por mês, razão FD/R
    mensal = df.groupby(["ano", "mes"], as_index=False)[["FD", "R"]].mean()
    por_mes = df.groupby("mes", as_index=False)[["FD", "R"]].mean()
    por_mes["razao_FD_R"] = por_mes["FD"] / por_mes["R"]
    fig, axes = plt.subplots(3, 1, figsize=(16, 14))
    fig.suptitle("Análise mensal: hidrelétricas FD vs R", fontsize=16, fontweight="bold")
    ax = axes[0]
    for ano, g in mensal.groupby("ano"):
        ax.plot(g["mes"], g["FD"], "o-", label=f"FD {ano}")
        ax.plot(g["mes"], g["R"], "s--", label=f"R {ano}")
    ax.set(title="Geração média mensal", ylabel="MW", xticks=range(1, 13), xticklabels=list(MESES_PT.values()))
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)
    ax = axes[1]
    x, w = np.arange(12), 0.35
    ax.bar(x - w / 2, por_mes["FD"], w, label="FD (fio d'água)", color=COR_FD, edgecolor="black", alpha=0.8)
    ax.bar(x + w / 2, por_mes["R"], w, label="R (reservatório)", color=COR_R, edgecolor="black", alpha=0.8)
    ax.set(title="Média histórica por mês", ylabel="MW", xticks=x, xticklabels=list(MESES_PT.values()))
    ax.legend()
    ax = axes[2]
    ax.bar(x, por_mes["razao_FD_R"], color=["green" if r > 1 else "red" for r in por_mes["razao_FD_R"]],
           alpha=0.7, edgecolor="black")
    ax.axhline(1, color="black", ls="--", label="FD = R")
    ax.set(title="Razão FD / R por mês", ylabel="FD/R", xticks=x, xticklabels=list(MESES_PT.values()))
    ax.legend()
    _salvar(fig, out, "analise_mensal.png")
    mensal.to_csv(out / "valores_mensais.csv", index=False)
    por_mes.to_csv(out / "media_por_mes.csv", index=False)

    # 2. dia da semana
    sem = df.groupby("dia_semana")[["FD", "R"]].agg(["mean", "std"])
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle("Perfil por dia da semana: FD vs R", fontsize=16, fontweight="bold")
    ax = axes[0]
    for col, cor, mk in (("FD", COR_FD, "o-"), ("R", COR_R, "s-")):
        m, s = sem[(col, "mean")], sem[(col, "std")]
        ax.plot(sem.index, m, mk, color=cor, lw=3, label=col)
        ax.fill_between(sem.index, m - s, m + s, color=cor, alpha=0.3)
    ax.set(title="Média ± desvio", ylabel="MW", xticks=range(7), xticklabels=list(DIAS_SEMANA_PT.values()))
    ax.legend()
    ax = axes[1]
    for col, cor, off in (("FD", COR_FD, -0.2), ("R", COR_R, 0.2)):
        bp = ax.boxplot([df.loc[df["dia_semana"] == d, col].dropna() for d in range(7)],
                        positions=np.arange(7) + off, widths=0.35, patch_artist=True, showfliers=False)
        for b in bp["boxes"]:
            b.set(facecolor=cor, alpha=0.7)
    ax.set(title="Distribuição por dia da semana", ylabel="MW", xticks=range(7), xticklabels=list(DIAS_SEMANA_PT.values()))
    ax.legend(handles=[Patch(facecolor=COR_FD, alpha=0.7, label="FD"), Patch(facecolor=COR_R, alpha=0.7, label="R")])
    _salvar(fig, out, "perfil_dia_semana.png")

    # 3. horário + heatmaps hora x mês
    hor = df.groupby("hora")[["FD", "R"]].agg(["mean", "std"])
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))
    fig.suptitle("Perfil horário: FD vs R", fontsize=16, fontweight="bold")
    ax = axes[0, 0]
    for col, cor, mk in (("FD", COR_FD, "o-"), ("R", COR_R, "s-")):
        m, s = hor[(col, "mean")], hor[(col, "std")]
        ax.plot(hor.index, m, mk, color=cor, lw=2.5, label=col)
        ax.fill_between(hor.index, m - s, m + s, color=cor, alpha=0.3)
    ax.set(title="Média ± desvio por hora", ylabel="MW", xlabel="Hora", xticks=range(0, 24, 2))
    ax.legend()
    ax = axes[0, 1]
    for col, cor, mk in (("FD", COR_FD, "o-"), ("R", COR_R, "s-")):
        ax.plot(hor.index, 100 * hor[(col, "std")] / hor[(col, "mean")], mk, color=cor, lw=2.5, label=col)
    ax.set(title="Coeficiente de variação por hora", ylabel="%", xlabel="Hora", xticks=range(0, 24, 2))
    ax.legend()
    for ax, col, cmap in ((axes[1, 0], "FD", "YlOrRd"), (axes[1, 1], "R", "YlGnBu")):
        piv = df.pivot_table(values=col, index="hora", columns="mes", aggfunc="mean")
        im = ax.imshow(piv.values, aspect="auto", cmap=cmap, interpolation="nearest")
        ax.set(title=f"{col}: hora x mês", xlabel="Mês", ylabel="Hora",
               xticks=range(len(piv.columns)), xticklabels=[MESES_PT[m] for m in piv.columns],
               yticks=range(0, 24, 2), yticklabels=range(0, 24, 2))
        fig.colorbar(im, ax=ax, label="MW")
    _salvar(fig, out, "perfil_horario.png")
    hor_flat = hor.copy()
    hor_flat.columns = ["_".join(c) for c in hor_flat.columns]
    hor_flat.reset_index().to_csv(out / "perfil_horario.csv", index=False)

    # 4. distribuições
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle("Distribuições: FD vs R", fontsize=16, fontweight="bold")
    ax = axes[0, 0]
    ax.hist(df["FD"].dropna(), bins=50, alpha=0.7, color=COR_FD, edgecolor="black", label="FD")
    ax.hist(df["R"].dropna(), bins=50, alpha=0.7, color=COR_R, edgecolor="black", label="R")
    ax.set(title="Histograma", xlabel="MW")
    ax.legend()
    ax = axes[0, 1]
    df["FD"].plot.kde(ax=ax, color=COR_FD, lw=2.5, label="FD")
    df["R"].plot.kde(ax=ax, color=COR_R, lw=2.5, label="R")
    ax.set(title="Densidade", xlabel="MW")
    ax.legend()
    ax = axes[0, 2]
    bp = ax.boxplot([df["FD"].dropna(), df["R"].dropna()], tick_labels=["FD", "R"], patch_artist=True, showfliers=False)
    for b, cor in zip(bp["boxes"], (COR_FD, COR_R)):
        b.set(facecolor=cor, alpha=0.7)
    ax.set(title="Boxplot", ylabel="MW")
    for ax, col in ((axes[1, 0], "FD"), (axes[1, 1], "R")):
        stats.probplot(df[col].dropna(), dist="norm", plot=ax)
        ax.set_title(f"Q-Q {col}")
    ax = axes[1, 2]
    amostra = df.dropna(subset=["FD", "R"]).sample(min(10000, len(df)), random_state=0)
    ax.scatter(amostra["FD"], amostra["R"], alpha=0.3, s=10, color="purple")
    z = np.polyfit(df["FD"].fillna(0), df["R"].fillna(0), 1)
    xs = np.linspace(df["FD"].min(), df["FD"].max(), 50)
    ax.plot(xs, np.poly1d(z)(xs), "r--", lw=2, label=f"y={z[0]:.2f}x+{z[1]:.0f}")
    ax.text(0.05, 0.95, f"corr = {df['FD'].corr(df['R']):.3f}", transform=ax.transAxes, va="top",
            bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))
    ax.set(title="FD vs R", xlabel="FD (MW)", ylabel="R (MW)")
    ax.legend()
    _salvar(fig, out, "distribuicoes.png")
    df[["FD", "R"]].describe().T.to_csv(out / "estatisticas_descritivas.csv")

    # 5. séries temporais diárias
    diario = df.groupby("data", as_index=False)[["FD", "R"]].mean()
    diario["data"] = pd.to_datetime(diario["data"])
    diario["razao_FD_R"] = diario["FD"] / diario["R"]
    for c in ("FD", "R", "razao_FD_R"):
        diario[f"{c}_MA30"] = diario[c].rolling(30, center=True).mean()
    fig, axes = plt.subplots(3, 1, figsize=(18, 14))
    fig.suptitle("Séries temporais (médias diárias): FD vs R", fontsize=16, fontweight="bold")
    axes[0].plot(diario["data"], diario["FD"], color=COR_FD, lw=1.5, alpha=0.8, label="FD")
    axes[0].plot(diario["data"], diario["R"], color=COR_R, lw=1.5, alpha=0.8, label="R")
    axes[0].set(title="Média diária", ylabel="MW")
    axes[1].plot(diario["data"], diario["FD_MA30"], color=COR_FD, lw=2.5, label="FD (MM 30d)")
    axes[1].plot(diario["data"], diario["R_MA30"], color=COR_R, lw=2.5, label="R (MM 30d)")
    axes[1].set(title="Média móvel de 30 dias", ylabel="MW")
    axes[2].plot(diario["data"], diario["razao_FD_R"], color="gray", lw=1, alpha=0.3, label="razão diária")
    axes[2].plot(diario["data"], diario["razao_FD_R_MA30"], color="purple", lw=2.5, label="razão (MM 30d)")
    axes[2].axhline(1, color="red", ls="--", label="FD = R")
    axes[2].set(title="Razão FD / R", ylabel="FD/R")
    for ax in axes:
        ax.legend()
    _salvar(fig, out, "series_temporais.png")
    diario.to_csv(out / "dados_diarios.csv", index=False)

    # 6. relatório
    tot = df["FD"].mean() + df["R"].mean()
    top_fd = mensal.nlargest(5, "FD")
    top_r = mensal.nlargest(5, "R")
    linhas = [
        "RELATÓRIO: HIDRELÉTRICAS FD vs R", "=" * 60,
        f"Período: {df['din_instante'].min()} a {df['din_instante'].max()}  ({len(df):,} horas)", "",
        *[f"{col}: média {df[col].mean():>10,.0f} MW | desvio {df[col].std():>8,.0f} | "
          f"min {df[col].min():>8,.0f} | max {df[col].max():>8,.0f} | mediana {df[col].median():>8,.0f}"
          for col in ("FD", "R")], "",
        f"Razão média FD/R: {df['FD'].mean() / df['R'].mean():.3f}",
        f"Correlação FD x R: {df['FD'].corr(df['R']):.3f}",
        f"Participação FD/R na hidro classificada: {100 * df['FD'].mean() / tot:.1f}% / {100 * df['R'].mean() / tot:.1f}%", "",
        "Top 5 meses FD: " + ", ".join(f"{int(r.ano)}-{int(r.mes):02d} ({r.FD:,.0f} MW)" for r in top_fd.itertuples()),
        "Top 5 meses R:  " + ", ".join(f"{int(r.ano)}-{int(r.mes):02d} ({r.R:,.0f} MW)" for r in top_r.itertuples()),
    ]
    (out / "RELATORIO_RESUMO.txt").write_text("\n".join(linhas), encoding="utf-8")
    logger.info(f"  {out.name}/RELATORIO_RESUMO.txt")


# ----------------------------------------------------------------------------- cmo
def carga_liquida_com_cmo() -> pd.DataFrame:
    """Histórico horário + CMO (média dos dois patamares semi-horários da hora)."""
    df = cl.carregar_historico()
    cmo = ons.carregar_cmo()
    cmo["din_instante"] = cmo["din_instante"].dt.floor("h")
    cmo = cmo.groupby("din_instante", as_index=False)["val_cmo"].mean()
    df = df.merge(cmo, on="din_instante", how="inner").dropna(subset=["carga_liquida_historica", "val_cmo"])
    return df


def _grade_mensal(df, x, y, hue, titulo, xlim, ylim, xlabel, ylabel):
    fig, axes = plt.subplots(6, 2, figsize=(16, 30))
    fig.suptitle(titulo, fontsize=18, fontweight="bold", y=1.0)
    for ax, mes in zip(axes.flatten(), range(1, 13)):
        g = df[df["mes"] == mes]
        ax.set(title=MESES_PT[mes], xlabel=xlabel, ylabel=ylabel, xlim=xlim, ylim=ylim)
        if g.empty:
            ax.text(0.5, 0.5, "sem dados", ha="center", va="center", transform=ax.transAxes)
            continue
        sns.scatterplot(data=g, x=x, y=y, hue=hue, palette="tab10", alpha=0.6, edgecolor="k", s=40, ax=ax)
        ax.legend(title=hue, fontsize=8)
    return fig


def cmo():
    """Carga líquida x CMO."""
    cfg = load_config()
    sub = cfg["carga_liquida"]["cmo_subsistema"]
    g = cfg["graficos"]
    df = carga_liquida_com_cmo()
    out = output_dir("cmo")
    logger.info(f"  {len(df):,} horas com CMO {sub}")

    fig = _grade_mensal(df, "carga_liquida_historica", "val_cmo", "ano",
                        f"Carga líquida (MW) x CMO {sub} (R$/MWh) por mês", g["cl_xlim"], g["cmo_ylim"],
                        "Carga líquida (MW)", "CMO (R$/MWh)")
    _salvar(fig, out, "scatter_cl_cmo_por_mes.png")

    fig, axes = plt.subplots(1, 2, figsize=(20, 8))
    sns.scatterplot(data=df, x="carga_liquida_historica", y="val_cmo", hue="ano", palette="viridis",
                    alpha=0.4, edgecolor="k", s=25, ax=axes[0])
    axes[0].set(title=f"Carga líquida x CMO {sub}", xlabel="Carga líquida (MW)", ylabel="CMO (R$/MWh)",
                xlim=g["cl_xlim"], ylim=g["cmo_ylim"])
    pos = df[(df["R"] > 0) & (df["val_cmo"] > 0)]
    sns.scatterplot(data=pos, x="R", y="val_cmo", hue="ano", palette="viridis", alpha=0.4, edgecolor="k", s=25, ax=axes[1])
    axes[1].set(title=f"Hidro reservatório (R) x CMO {sub}", xlabel="R (MW)", ylabel="CMO (R$/MWh)", ylim=g["cmo_ylim"])
    _salvar(fig, out, "scatter_cl_cmo.png")

    cols = ["din_instante", "ano", "mes", "dia", "hora", "FD", "R", "termica_flexivel", "carga_liquida_historica", "val_cmo"]
    df[cols].to_csv(out / "carga_liquida_cmo.csv", index=False)
    resumo = df.groupby(["ano", "mes"]).agg(carga_liquida=("carga_liquida_historica", "mean"), cmo=("val_cmo", "mean"))
    # corr fica NaN nos meses de CMO constante (piso o mês inteiro)
    resumo["corr"] = df.groupby(["ano", "mes"]).apply(
        lambda g: g["carga_liquida_historica"].corr(g["val_cmo"]) if g["val_cmo"].std() > 0 else np.nan,
        include_groups=False)
    resumo.reset_index().to_csv(out / "resumo_mensal.csv", index=False)
    logger.info(f"  {out.name}/carga_liquida_cmo.csv, resumo_mensal.csv")


# ----------------------------------------------------------------------------- diarios
def diarios(n_dias: int | None = None):
    """Gráficos dos últimos N dias: despacho térmico por componente e geração por tipo + carga líquida."""
    cfg = load_config()
    n_dias = n_dias or cfg["graficos"]["dias_recentes"]
    comp = cfg["carga_liquida"]["componentes_termica_todas"]
    flex = cfg["carga_liquida"]["componentes_termica_flexivel"]
    hist = cl.carregar_historico()
    ger = cl.carregar_geracao_por_tipo()
    term = cl.carregar_termica_componentes()
    out = output_dir("diarios")
    dias = sorted(hist["din_instante"].dt.date.unique())[-n_dias:]
    tipos = [c for c in ger.columns if c != "din_instante"]

    for dia in dias:
        t = term[term["din_instante"].dt.date == dia].set_index("din_instante")
        if not t.empty:
            ax = t[[c for c in comp if c in t.columns]].plot(kind="bar", stacked=True, figsize=(16, 8), colormap="tab20")
            ax.set(title=f"Despacho térmico verificado por componente - {dia}", xlabel="Hora", ylabel="MW")
            ax.set_xticklabels([ts.strftime("%H:%M") for ts in t.index], rotation=45)
            ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
            _salvar(ax.figure, out, f"termica_componentes_{dia}.png")

        g = ger[ger["din_instante"].dt.date == dia].sort_values("din_instante")
        h = hist[hist["din_instante"].dt.date == dia].sort_values("din_instante")
        if g.empty:
            continue
        fig, ax = plt.subplots(figsize=(16, 8))
        ax.stackplot(g["din_instante"], [g[c].fillna(0).values for c in tipos], labels=tipos, alpha=0.7)
        ax.plot(h["din_instante"], h["carga_liquida_historica"], color="black", lw=2, label="Carga líquida (R + térmica flex)")
        ax.plot(h["din_instante"], h["termica_flexivel"], color="red", lw=2, ls="--", label=f"Térmica flexível ({' + '.join(flex)})")
        ax.set(title=f"Geração por tipo de usina e carga líquida - {dia}", xlabel="Hora", ylabel="MW")
        ax.legend(loc="upper left", fontsize=8)
        _salvar(fig, out, f"geracao_por_tipo_{dia}.png")


# ----------------------------------------------------------------------------- curtailment
def carga_liquida_com_curtailment() -> pd.DataFrame:
    df = cl.carregar_historico()
    curt = ons.carregar_curtailment()
    return df.merge(curt, on="din_instante", how="inner")


def curtailment():
    """Carga líquida x curtailment eólico + solar (constrained-off), horário."""
    g = load_config()["graficos"]
    df = carga_liquida_com_curtailment()
    out = output_dir("curtailment")
    logger.info(f"  {len(df):,} horas com curtailment ({df['din_instante'].min():%Y-%m} a {df['din_instante'].max():%Y-%m})")

    df["dia_semana"] = df["din_instante"].dt.dayofweek
    df["fds"] = np.where(df["dia_semana"] >= 5, "FDS", "DU")
    ymax = float(np.ceil(df["curtailment_mw"].quantile(0.999) / 5000) * 5000)
    for ano, d in df.groupby("ano"):
        fig = _grade_mensal(d, "carga_liquida_historica", "curtailment_mw", "fds",
                            f"Carga líquida (MW) x curtailment (MW) por mês - {ano}", g["cl_xlim"], [0, ymax],
                            "Carga líquida (MW)", "Curtailment (MW)")
        _salvar(fig, out, f"scatter_cl_curtailment_{ano}.png")

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.scatterplot(data=df, x="carga_liquida_historica", y="curtailment_mw", hue="ano", palette="tab10",
                    alpha=0.4, edgecolor="k", s=25, ax=ax)
    ax.set(title="Carga líquida x curtailment (eólico + solar)", xlabel="Carga líquida (MW)",
           ylabel="Curtailment (MW)", xlim=g["cl_xlim"], ylim=[0, ymax])
    _salvar(fig, out, "scatter_cl_curtailment.png")

    cols = ["din_instante", "ano", "mes", "dia", "hora", "FD", "R", "termica_flexivel", "carga_liquida_historica",
            "curtailment_eolica_mw", "curtailment_solar_mw", "curtailment_mw", "curtailment_ene_mw", "curtailment_rede_mw"]
    df[cols].to_csv(out / "carga_liquida_curtailment.csv", index=False)
    resumo = df.groupby(["ano", "mes"]).agg(carga_liquida=("carga_liquida_historica", "mean"),
                                            curtailment_mw=("curtailment_mw", "mean"),
                                            curtailment_ene_mw=("curtailment_ene_mw", "mean"),
                                            curtailment_rede_mw=("curtailment_rede_mw", "mean"),
                                            curtailment_gwh=("curtailment_mw", lambda s: s.sum() / 1000),
                                            horas_com_corte=("curtailment_mw", lambda s: int((s > 0).sum())))
    resumo.reset_index().to_csv(out / "resumo_mensal.csv", index=False)
    logger.info(f"  {out.name}/carga_liquida_curtailment.csv, resumo_mensal.csv")
