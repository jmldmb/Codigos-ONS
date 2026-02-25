"""
Análise auxiliar do curtailment Brasil mensal e geração de gráfico.

Saída:
  - PNG: output/curtailment/brasil_curtailment_pct.png
  - Impressão de head() e estatísticas resumidas no stdout
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import matplotlib.pyplot as plt


# __file__ está em: mini_dessem/Scripts/src/auxiliar/curtailment/analysis.py
# Raiz do projeto mini_dessem = parents[4]
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[4]
DEFAULT_CURT_DIR = _PROJECT_ROOT / "output" / "curtailment"


def summarize_and_plot(
    brasil_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[pd.DataFrame, Path]:
    """Lê brasil_mensal.parquet, imprime resumo e gera gráfico percentual empilhado.

    Retorna (df, path_pct_png).
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    parquet_path = (
        Path(brasil_parquet_path)
        if brasil_parquet_path is not None
        else (curtail_dir / "total" / "brasil_mensal_total.parquet")
    )

    if not parquet_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {parquet_path}")

    df = pd.read_parquet(parquet_path)

    # Ordenar por mês
    if "mes" in df.columns:
        df = df.sort_values("mes").reset_index(drop=True)

    # Estatísticas resumidas
    print("\n=== brasil_mensal.parquet :: head(5) ===")
    print(df.head(5))

    if not df.empty:
        print("\n=== Estatísticas ===")
        print(f"Período: {df['mes'].min().date()} a {df['mes'].max().date()}")
        print(
            "Curtailment total (MWh):",
            (df["curt_ENE_mwh"].sum() + df["curt_CNF_mwh"].sum() + df["curt_REL_mwh"].sum()),
        )
        print(
            "Média percentual (ENE/CNF/REL) (%):",
            round((df["pct_ENE"].mean() or 0) * 100, 3),
            round((df["pct_CNF"].mean() or 0) * 100, 3),
            round((df["pct_REL"].mean() or 0) * 100, 3),
        )

    # Gráfico percentual empilhado por tipo (ENE, CNF, REL)
    x = df["mes"].dt.to_period("M").astype(str)
    ene = (df["pct_ENE"] * 100).fillna(0)
    cnf = (df["pct_CNF"] * 100).fillna(0)
    rel = (df["pct_REL"] * 100).fillna(0)

    plt.figure(figsize=(12, 6))
    plt.bar(x, ene, label="ENE")
    plt.bar(x, cnf, bottom=ene, label="CNF")
    plt.bar(x, rel, bottom=ene + cnf, label="REL")
    plt.ylabel("Curtailment / Geração (%)")
    plt.title("Brasil – Curtailment por mês e por tipo (%)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()

    out_png = curtail_dir / "brasil_curtailment_pct.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()

    return df, out_png


def plot_curtailment_mwh(
    brasil_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Path:
    """Gera gráfico de curtailment mensal empilhado em MWh (ENE, CNF, REL)."""
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    parquet_path = (
        Path(brasil_parquet_path)
        if brasil_parquet_path is not None
        else (curtail_dir / "total" / "brasil_mensal_total.parquet")
    )

    df = pd.read_parquet(parquet_path)
    df = df.sort_values("mes").reset_index(drop=True)

    x = df["mes"].dt.to_period("M").astype(str)
    ene = df["curt_ENE_mwh"].fillna(0)
    cnf = df["curt_CNF_mwh"].fillna(0)
    rel = df["curt_REL_mwh"].fillna(0)

    plt.figure(figsize=(12, 6))
    plt.bar(x, ene, label="ENE")
    plt.bar(x, cnf, bottom=ene, label="CNF")
    plt.bar(x, rel, bottom=ene + cnf, label="REL")
    plt.ylabel("Curtailment (MWh)")
    plt.title("Brasil – Curtailment por mês e por tipo (MWh)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()

    out_png = curtail_dir / "brasil_curtailment_mwh.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()

    return out_png


def plot_potential_vs_generation(
    brasil_parquet_path: Optional[Path | str] = None,
    raw_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Path:
    """Gera gráfico mensal de geração (MWh) vs geração potencial (geração + curtailment).

    Usa o parquet bruto para obter a geração realizada e soma curtailment mensal.
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    brasil_path = (
        Path(brasil_parquet_path)
        if brasil_parquet_path is not None
        else curtail_dir / "brasil_mensal.parquet"
    )
    raw_path = (
        Path(raw_parquet_path)
        if raw_parquet_path is not None
        else curtail_dir / "curtailment_raw.parquet"
    )

    df_brasil = pd.read_parquet(brasil_path).copy()
    df_brasil = df_brasil.sort_values("mes")
    df_brasil["curt_total_mwh"] = (
        df_brasil["curt_ENE_mwh"].fillna(0)
        + df_brasil["curt_CNF_mwh"].fillna(0)
        + df_brasil["curt_REL_mwh"].fillna(0)
    )

    # Carregar geração realizada do bruto
    df_raw = pd.read_parquet(raw_path)[["data", "val_geracao_mwh"]].copy()
    df_raw["mes"] = pd.to_datetime(df_raw["data"]).dt.to_period("M").dt.to_timestamp()
    gen_mensal = df_raw.groupby("mes", as_index=False)["val_geracao_mwh"].sum()
    gen_mensal = gen_mensal.sort_values("mes")

    # Juntar com curtailment mensal
    df_plot = pd.merge(df_brasil[["mes", "curt_total_mwh"]], gen_mensal, on="mes", how="outer").fillna(0)
    df_plot = df_plot.sort_values("mes")
    df_plot["potencial_mwh"] = df_plot["val_geracao_mwh"] + df_plot["curt_total_mwh"]

    x = df_plot["mes"].dt.to_period("M").astype(str)

    plt.figure(figsize=(12, 6))
    # Barras empilhadas: geração (base) + curtailment (topo) para mostrar potencial
    plt.bar(x, df_plot["val_geracao_mwh"], label="Geração (MWh)", color="#4e79a7")
    plt.bar(
        x,
        df_plot["curt_total_mwh"],
        bottom=df_plot["val_geracao_mwh"],
        label="Curtailment (MWh)",
        color="#f28e2b",
    )
    plt.ylabel("Energia (MWh)")
    plt.title("Brasil – Geração vs Geração Potencial (MWh)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()

    out_png = curtail_dir / "brasil_potencial_vs_geracao.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()

    return out_png


__all__ = [
    "summarize_and_plot",
    "plot_curtailment_mwh",
    "plot_potential_vs_generation",
    "generate_source_graphs",
    "save_source_monthly_parquets",
    "generate_daily_high_frequency_graphs",
    "generate_hourly_graphs",
]


# ==========================
# Gráficos por fonte (total/eólica/solar)
# ==========================

def _aggregate_monthly_from_raw(
    raw_parquet_path: Optional[Path | str] = None,
    tipo_usina: Optional[str] = None,
) -> pd.DataFrame:
    """Agrupa mensalmente a partir do parquet bruto, opcionalmente filtrando por fonte.

    Retorna colunas: mes, geracao_est_mwh, curt_ENE_mwh, curt_CNF_mwh, curt_REL_mwh,
    pct_ENE, pct_CNF, pct_REL, val_geracao_mwh, curt_total_mwh, potencial_mwh.
    """
    curtail_dir = DEFAULT_CURT_DIR
    raw_path = (
        Path(raw_parquet_path)
        if raw_parquet_path is not None
        else curtail_dir / "curtailment_raw.parquet"
    )

    df = pd.read_parquet(raw_path)
    if tipo_usina is not None:
        df = df[df["tipo_usina"].str.lower() == tipo_usina.lower()].copy()

    # Datas e mês
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df[df["data"].notna()].copy()
    df["mes"] = df["data"].dt.to_period("M")

    # Agregação diária com tipo de restrição
    # Primeiro por dia e razão para somar MWh corretamente
    agr_dia = (
        df.groupby(["data", "cod_razaorestricao"], dropna=False)
        .agg(
            geracao_est_mwh=("val_geracaoreferencia_mwh", "sum"),
            curt_mwh=("val_curtail_mwh", "sum"),
        )
        .reset_index()
    )
    agr_dia["mes"] = agr_dia["data"].dt.to_period("M")

    # Mensal por tipo de restrição
    mensal = (
        agr_dia.groupby(["mes"], as_index=False)
        .agg(
            geracao_est_mwh=("geracao_est_mwh", "sum"),
            curt_ENE_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "ENE"].sum()),
            curt_CNF_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "CNF"].sum()),
            curt_REL_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "REL"].sum()),
        )
    )

    den = mensal["geracao_est_mwh"].replace({0: pd.NA})
    mensal["pct_ENE"] = mensal["curt_ENE_mwh"] / den
    mensal["pct_CNF"] = mensal["curt_CNF_mwh"] / den
    mensal["pct_REL"] = mensal["curt_REL_mwh"] / den

    # Geração realizada mensal a partir do bruto
    gen_mensal = df.groupby("mes", as_index=False)["val_geracao_mwh"].sum()

    # Juntar e calcular total/potencial
    res = pd.merge(mensal, gen_mensal, on="mes", how="outer").fillna(0)
    res = res.sort_values("mes").reset_index(drop=True)
    res["curt_total_mwh"] = (
        res["curt_ENE_mwh"].fillna(0) + res["curt_CNF_mwh"].fillna(0) + res["curt_REL_mwh"].fillna(0)
    )
    res["potencial_mwh"] = res["val_geracao_mwh"] + res["curt_total_mwh"]

    # Converter mes para timestamp
    res["mes"] = res["mes"].dt.to_timestamp()
    return res


def _plot_pct(df: pd.DataFrame, out_png: Path) -> None:
    x = df["mes"].dt.to_period("M").astype(str)
    ene = (df["pct_ENE"] * 100).fillna(0)
    cnf = (df["pct_CNF"] * 100).fillna(0)
    rel = (df["pct_REL"] * 100).fillna(0)
    plt.figure(figsize=(12, 6))
    plt.bar(x, ene, label="ENE")
    plt.bar(x, cnf, bottom=ene, label="CNF")
    plt.bar(x, rel, bottom=ene + cnf, label="REL")
    plt.ylabel("Curtailment / Geração (%)")
    plt.title("Curtailment por mês e por tipo (%)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def _plot_mwh(df: pd.DataFrame, out_png: Path) -> None:
    x = df["mes"].dt.to_period("M").astype(str)
    ene = df["curt_ENE_mwh"].fillna(0)
    cnf = df["curt_CNF_mwh"].fillna(0)
    rel = df["curt_REL_mwh"].fillna(0)
    plt.figure(figsize=(12, 6))
    plt.bar(x, ene, label="ENE")
    plt.bar(x, cnf, bottom=ene, label="CNF")
    plt.bar(x, rel, bottom=ene + cnf, label="REL")
    plt.ylabel("Curtailment (MWh)")
    plt.title("Curtailment por mês e por tipo (MWh)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def _plot_potential(df: pd.DataFrame, out_png: Path) -> None:
    x = df["mes"].dt.to_period("M").astype(str)
    plt.figure(figsize=(12, 6))
    plt.bar(x, df["val_geracao_mwh"], label="Geração (MWh)", color="#4e79a7")
    plt.bar(
        x,
        df["curt_total_mwh"],
        bottom=df["val_geracao_mwh"],
        label="Curtailment (MWh)",
        color="#f28e2b",
    )
    plt.ylabel("Energia (MWh)")
    plt.title("Geração vs Geração Potencial (MWh)")
    plt.xticks(rotation=45, ha="right")
    plt.legend()
    plt.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def generate_source_graphs(
    raw_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path, Path, Path, Path, Path, Path, Path, Path]:
    """Gera os 3 gráficos (pct, MWh, potencial) em três escopos: total, eólica e solar.

    Retorna tupla com 9 caminhos (total_pct, total_mwh, total_pot, eolica_pct, ... solar_pot).
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    dir_total = curtail_dir / "total"
    dir_eolica = curtail_dir / "eolica"
    dir_solar = curtail_dir / "solar"

    # Total
    df_total = _aggregate_monthly_from_raw(raw_parquet_path, tipo_usina=None)
    total_pct = dir_total / "curtailment_pct.png"
    total_mwh = dir_total / "curtailment_mwh.png"
    total_pot = dir_total / "potencial_vs_geracao.png"
    _plot_pct(df_total, total_pct)
    _plot_mwh(df_total, total_mwh)
    _plot_potential(df_total, total_pot)

    # Eólica
    df_eolica = _aggregate_monthly_from_raw(raw_parquet_path, tipo_usina="eolica")
    eolica_pct = dir_eolica / "curtailment_pct.png"
    eolica_mwh = dir_eolica / "curtailment_mwh.png"
    eolica_pot = dir_eolica / "potencial_vs_geracao.png"
    _plot_pct(df_eolica, eolica_pct)
    _plot_mwh(df_eolica, eolica_mwh)
    _plot_potential(df_eolica, eolica_pot)

    # Solar
    df_solar = _aggregate_monthly_from_raw(raw_parquet_path, tipo_usina="solar")
    solar_pct = dir_solar / "curtailment_pct.png"
    solar_mwh = dir_solar / "curtailment_mwh.png"
    solar_pot = dir_solar / "potencial_vs_geracao.png"
    _plot_pct(df_solar, solar_pct)
    _plot_mwh(df_solar, solar_mwh)
    _plot_potential(df_solar, solar_pot)

    return (
        total_pct,
        total_mwh,
        total_pot,
        eolica_pct,
        eolica_mwh,
        eolica_pot,
        solar_pct,
        solar_mwh,
        solar_pot,
    )


def save_source_monthly_parquets(
    raw_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """Salva agregados mensais por fonte (eólica e solar) em Parquet.

    Retorna (path_eolica, path_solar).
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    df_eolica = _aggregate_monthly_from_raw(raw_parquet_path, tipo_usina="eolica")
    df_solar = _aggregate_monthly_from_raw(raw_parquet_path, tipo_usina="solar")

    dir_eolica = curtail_dir / "eolica"
    dir_solar = curtail_dir / "solar"
    dir_eolica.mkdir(parents=True, exist_ok=True)
    dir_solar.mkdir(parents=True, exist_ok=True)

    path_eolica = dir_eolica / "brasil_mensal_eolica.parquet"
    path_solar = dir_solar / "brasil_mensal_solar.parquet"

    df_eolica.to_parquet(path_eolica, index=False, compression="snappy")
    df_solar.to_parquet(path_solar, index=False, compression="snappy")

    return path_eolica, path_solar


# ==========================
# Gráficos de Alta Frequência (Últimos 15 dias)
# ==========================

def _aggregate_daily_last_n_days(
    raw_parquet_path: Optional[Path | str] = None,
    tipo_usina: Optional[str] = None,
    n_days: int = 15,
) -> pd.DataFrame:
    """Agrupa diariamente os últimos N dias a partir do parquet bruto.
    
    Retorna colunas: data, val_geracao_mwh, curt_ENE_mwh, curt_CNF_mwh, curt_REL_mwh,
    curt_total_mwh, potencial_mwh, pct_ENE, pct_CNF, pct_REL, pct_total.
    """
    curtail_dir = DEFAULT_CURT_DIR
    raw_path = (
        Path(raw_parquet_path)
        if raw_parquet_path is not None
        else curtail_dir / "curtailment_raw.parquet"
    )

    df = pd.read_parquet(raw_path)
    if tipo_usina is not None:
        df = df[df["tipo_usina"].str.lower() == tipo_usina.lower()].copy()

    # Processar datas
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df = df[df["data"].notna()].copy()
    
    # Filtrar últimos N dias
    max_date = df["data"].max()
    cutoff_date = max_date - pd.Timedelta(days=n_days - 1)
    df = df[df["data"] >= cutoff_date].copy()

    # Agregação diária por tipo de restrição
    daily_agg = (
        df.groupby(["data", "cod_razaorestricao"], dropna=False)
        .agg(
            val_geracao_mwh=("val_geracao_mwh", "sum"),
            val_geracaoreferencia_mwh=("val_geracaoreferencia_mwh", "sum"),
            val_curtail_mwh=("val_curtail_mwh", "sum"),
        )
        .reset_index()
    )

    # Pivotar por tipo de restrição
    res = (
        daily_agg.groupby("data", as_index=False)
        .agg(
            val_geracao_mwh=("val_geracao_mwh", "sum"),
            geracao_est_mwh=("val_geracaoreferencia_mwh", "sum"),
            curt_ENE_mwh=("val_curtail_mwh", lambda x: x[daily_agg.loc[x.index, "cod_razaorestricao"] == "ENE"].sum()),
            curt_CNF_mwh=("val_curtail_mwh", lambda x: x[daily_agg.loc[x.index, "cod_razaorestricao"] == "CNF"].sum()),
            curt_REL_mwh=("val_curtail_mwh", lambda x: x[daily_agg.loc[x.index, "cod_razaorestricao"] == "REL"].sum()),
        )
    )

    # Calcular curtailment total e potencial
    res["curt_total_mwh"] = res["curt_ENE_mwh"] + res["curt_CNF_mwh"] + res["curt_REL_mwh"]
    res["potencial_mwh"] = res["val_geracao_mwh"] + res["curt_total_mwh"]

    # Calcular percentuais
    den = res["geracao_est_mwh"].replace({0: pd.NA})
    res["pct_ENE"] = res["curt_ENE_mwh"] / den
    res["pct_CNF"] = res["curt_CNF_mwh"] / den
    res["pct_REL"] = res["curt_REL_mwh"] / den
    res["pct_total"] = res["curt_total_mwh"] / den

    return res.sort_values("data").reset_index(drop=True)


def _plot_daily_mwh(df: pd.DataFrame, out_png: Path, title_suffix: str = "", n_days: int = None) -> None:
    """Gera gráfico de curtailment diário empilhado em MWh."""
    x = df["data"].dt.strftime("%d/%m")
    ene = df["curt_ENE_mwh"].fillna(0)
    cnf = df["curt_CNF_mwh"].fillna(0)
    rel = df["curt_REL_mwh"].fillna(0)
    
    # Determinar n_days se não fornecido
    if n_days is None:
        n_days = len(df)
    
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x, ene, label="ENE", color="#e74c3c")
    ax.bar(x, cnf, bottom=ene, label="CNF", color="#f39c12")
    ax.bar(x, rel, bottom=ene + cnf, label="REL", color="#95a5a6")
    
    ax.set_ylabel("Curtailment (MWh)", fontsize=11)
    ax.set_xlabel("Data", fontsize=11)
    ax.set_title(f"Curtailment Diário - Últimos {n_days} Dias{title_suffix}", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def _plot_daily_pct(df: pd.DataFrame, out_png: Path, title_suffix: str = "", n_days: int = None) -> None:
    """Gera gráfico de curtailment diário empilhado em percentual."""
    x = df["data"].dt.strftime("%d/%m")
    ene = (df["pct_ENE"] * 100).fillna(0)
    cnf = (df["pct_CNF"] * 100).fillna(0)
    rel = (df["pct_REL"] * 100).fillna(0)
    
    # Determinar n_days se não fornecido
    if n_days is None:
        n_days = len(df)
    
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(x, ene, label="ENE", color="#e74c3c")
    ax.bar(x, cnf, bottom=ene, label="CNF", color="#f39c12")
    ax.bar(x, rel, bottom=ene + cnf, label="REL", color="#95a5a6")
    
    ax.set_ylabel("Curtailment / Geração (%)", fontsize=11)
    ax.set_xlabel("Data", fontsize=11)
    ax.set_title(f"Curtailment Diário (%) - Últimos {n_days} Dias{title_suffix}", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def generate_daily_high_frequency_graphs(
    raw_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    n_days: int = 15,
) -> Tuple[Path, Path, Path, Path, Path, Path]:
    """Gera gráficos diários de curtailment dos últimos N dias para total, eólica e solar.
    
    Retorna tupla com 6 caminhos (total_mwh, total_pct, eolica_mwh, eolica_pct, solar_mwh, solar_pct).
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    dir_total = curtail_dir / "total"
    dir_eolica = curtail_dir / "eolica"
    dir_solar = curtail_dir / "solar"

    # Total
    df_total = _aggregate_daily_last_n_days(raw_parquet_path, tipo_usina=None, n_days=n_days)
    total_mwh = dir_total / f"curtailment_diario_{n_days}d_mwh.png"
    total_pct = dir_total / f"curtailment_diario_{n_days}d_pct.png"
    _plot_daily_mwh(df_total, total_mwh, title_suffix=" - Total", n_days=n_days)
    _plot_daily_pct(df_total, total_pct, title_suffix=" - Total", n_days=n_days)

    # Eólica
    df_eolica = _aggregate_daily_last_n_days(raw_parquet_path, tipo_usina="eolica", n_days=n_days)
    eolica_mwh = dir_eolica / f"curtailment_diario_{n_days}d_mwh.png"
    eolica_pct = dir_eolica / f"curtailment_diario_{n_days}d_pct.png"
    _plot_daily_mwh(df_eolica, eolica_mwh, title_suffix=" - Eólica", n_days=n_days)
    _plot_daily_pct(df_eolica, eolica_pct, title_suffix=" - Eólica", n_days=n_days)

    # Solar
    df_solar = _aggregate_daily_last_n_days(raw_parquet_path, tipo_usina="solar", n_days=n_days)
    solar_mwh = dir_solar / f"curtailment_diario_{n_days}d_mwh.png"
    solar_pct = dir_solar / f"curtailment_diario_{n_days}d_pct.png"
    _plot_daily_mwh(df_solar, solar_mwh, title_suffix=" - Solar", n_days=n_days)
    _plot_daily_pct(df_solar, solar_pct, title_suffix=" - Solar", n_days=n_days)

    return (
        total_mwh,
        total_pct,
        eolica_mwh,
        eolica_pct,
        solar_mwh,
        solar_pct,
    )


# ==========================
# Gráficos Horários (Últimos 10 dias)
# ==========================

def _aggregate_hourly_last_n_days(
    raw_parquet_path: Optional[Path | str] = None,
    tipo_usina: Optional[str] = None,
    n_days: int = 10,
) -> pd.DataFrame:
    """Agrupa por hora os últimos N dias a partir do parquet bruto.
    
    Retorna colunas: din_instante (hora), val_geracao_mwh, curt_ENE_mwh, curt_CNF_mwh, 
    curt_REL_mwh, curt_total_mwh, potencial_mwh, pct_total.
    """
    curtail_dir = DEFAULT_CURT_DIR
    raw_path = (
        Path(raw_parquet_path)
        if raw_parquet_path is not None
        else curtail_dir / "curtailment_raw.parquet"
    )

    df = pd.read_parquet(raw_path)
    if tipo_usina is not None:
        df = df[df["tipo_usina"].str.lower() == tipo_usina.lower()].copy()

    # Processar datas e horários
    df["din_instante"] = pd.to_datetime(df["din_instante"], errors="coerce")
    df = df[df["din_instante"].notna()].copy()
    
    # Filtrar últimos N dias
    max_date = df["din_instante"].max()
    cutoff_datetime = max_date - pd.Timedelta(days=n_days - 1)
    df = df[df["din_instante"] >= cutoff_datetime].copy()

    # Arredondar para hora cheia (agregar semi-horários)
    df["hora_cheia"] = df["din_instante"].dt.floor("h")

    # Agregação horária por tipo de restrição
    hourly_agg = (
        df.groupby(["hora_cheia", "cod_razaorestricao"], dropna=False)
        .agg(
            val_geracao_mwh=("val_geracao_mwh", "sum"),
            val_geracaoreferencia_mwh=("val_geracaoreferencia_mwh", "sum"),
            val_curtail_mwh=("val_curtail_mwh", "sum"),
        )
        .reset_index()
    )

    # Pivotar por tipo de restrição
    res = (
        hourly_agg.groupby("hora_cheia", as_index=False)
        .agg(
            val_geracao_mwh=("val_geracao_mwh", "sum"),
            geracao_est_mwh=("val_geracaoreferencia_mwh", "sum"),
            curt_ENE_mwh=("val_curtail_mwh", lambda x: x[hourly_agg.loc[x.index, "cod_razaorestricao"] == "ENE"].sum()),
            curt_CNF_mwh=("val_curtail_mwh", lambda x: x[hourly_agg.loc[x.index, "cod_razaorestricao"] == "CNF"].sum()),
            curt_REL_mwh=("val_curtail_mwh", lambda x: x[hourly_agg.loc[x.index, "cod_razaorestricao"] == "REL"].sum()),
        )
    )

    # Renomear coluna
    res = res.rename(columns={"hora_cheia": "din_instante"})

    # Calcular curtailment total e potencial
    res["curt_total_mwh"] = res["curt_ENE_mwh"] + res["curt_CNF_mwh"] + res["curt_REL_mwh"]
    res["potencial_mwh"] = res["val_geracao_mwh"] + res["curt_total_mwh"]

    # Calcular percentual total
    den = res["geracao_est_mwh"].replace({0: pd.NA})
    res["pct_total"] = (res["curt_total_mwh"] / den) * 100

    return res.sort_values("din_instante").reset_index(drop=True)


def _plot_hourly_curtailment(df: pd.DataFrame, out_png: Path, title_suffix: str = "", n_days: int = None) -> None:
    """Gera gráfico de curtailment horário em MWh (linha + área)."""
    if len(df) == 0:
        print(f"  [AVISO] Sem dados para {title_suffix}")
        return
    
    # Determinar n_days se não fornecido
    if n_days is None:
        n_days = int((df["din_instante"].max() - df["din_instante"].min()).total_seconds() / 86400) + 1
    
    fig, ax = plt.subplots(figsize=(16, 6))
    
    x = df["din_instante"]
    
    # Gráfico de área empilhada para os tipos de curtailment
    ene = df["curt_ENE_mwh"].fillna(0)
    cnf = df["curt_CNF_mwh"].fillna(0)
    rel = df["curt_REL_mwh"].fillna(0)
    
    ax.fill_between(x, 0, ene, label="ENE", color="#e74c3c", alpha=0.7)
    ax.fill_between(x, ene, ene + cnf, label="CNF", color="#f39c12", alpha=0.7)
    ax.fill_between(x, ene + cnf, ene + cnf + rel, label="REL", color="#95a5a6", alpha=0.7)
    
    # Linha para curtailment total
    total = df["curt_total_mwh"]
    ax.plot(x, total, color="#2c3e50", linewidth=1.5, alpha=0.8, label="Total")
    
    ax.set_ylabel("Curtailment (MWh)", fontsize=11)
    ax.set_xlabel("Data e Hora", fontsize=11)
    ax.set_title(f"Curtailment Horário - Últimos {n_days} Dias{title_suffix}", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    # Formatar eixo X
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))  # Marca a cada 12 horas
    
    plt.xticks(rotation=0, ha="center")
    plt.tight_layout()
    
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def _plot_hourly_potential(df: pd.DataFrame, out_png: Path, title_suffix: str = "", n_days: int = None) -> None:
    """Gera gráfico horário de geração vs potencial (geração + curtailment)."""
    if len(df) == 0:
        print(f"  [AVISO] Sem dados para {title_suffix}")
        return
    
    # Determinar n_days se não fornecido
    if n_days is None:
        n_days = int((df["din_instante"].max() - df["din_instante"].min()).total_seconds() / 86400) + 1
    
    fig, ax = plt.subplots(figsize=(16, 6))
    
    x = df["din_instante"]
    
    # Barras empilhadas: geração (base) + curtailment (topo) para mostrar potencial
    ax.bar(x, df["val_geracao_mwh"], label="Geração (MWh)", color="#4e79a7", width=0.03)
    ax.bar(
        x,
        df["curt_total_mwh"],
        bottom=df["val_geracao_mwh"],
        label="Curtailment (MWh)",
        color="#f28e2b",
        width=0.03,
    )
    
    ax.set_ylabel("Energia (MWh)", fontsize=11)
    ax.set_xlabel("Data e Hora", fontsize=11)
    ax.set_title(f"Geração vs Potencial Horário - Últimos {n_days} Dias{title_suffix}", fontsize=13, fontweight="bold")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    
    # Formatar eixo X
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m\n%H:%M"))
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=12))  # Marca a cada 12 horas
    
    plt.xticks(rotation=0, ha="center")
    plt.tight_layout()
    
    out_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()


def generate_hourly_graphs(
    raw_parquet_path: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
    n_days: int = 10,
) -> Tuple[Path, Path, Path, Path, Path, Path]:
    """Gera gráficos horários de curtailment dos últimos N dias para total, eólica e solar.
    
    Gera 2 gráficos por fonte:
    - curtailment_horario_Nd.png: Curtailment horário por tipo (área empilhada)
    - potencial_horario_Nd.png: Geração vs Potencial horário (barras empilhadas)
    
    Retorna tupla com 6 caminhos (total_curt, total_pot, eolica_curt, eolica_pot, solar_curt, solar_pot).
    """
    curtail_dir = Path(output_dir) if output_dir is not None else DEFAULT_CURT_DIR
    dir_total = curtail_dir / "total"
    dir_eolica = curtail_dir / "eolica"
    dir_solar = curtail_dir / "solar"

    # Total - Curtailment e Potencial
    df_total = _aggregate_hourly_last_n_days(raw_parquet_path, tipo_usina=None, n_days=n_days)
    total_curt = dir_total / f"curtailment_horario_{n_days}d.png"
    total_pot = dir_total / f"potencial_horario_{n_days}d.png"
    _plot_hourly_curtailment(df_total, total_curt, title_suffix=" - Total", n_days=n_days)
    _plot_hourly_potential(df_total, total_pot, title_suffix=" - Total", n_days=n_days)

    # Eólica - Curtailment e Potencial
    df_eolica = _aggregate_hourly_last_n_days(raw_parquet_path, tipo_usina="eolica", n_days=n_days)
    eolica_curt = dir_eolica / f"curtailment_horario_{n_days}d.png"
    eolica_pot = dir_eolica / f"potencial_horario_{n_days}d.png"
    _plot_hourly_curtailment(df_eolica, eolica_curt, title_suffix=" - Eólica", n_days=n_days)
    _plot_hourly_potential(df_eolica, eolica_pot, title_suffix=" - Eólica", n_days=n_days)

    # Solar - Curtailment e Potencial
    df_solar = _aggregate_hourly_last_n_days(raw_parquet_path, tipo_usina="solar", n_days=n_days)
    solar_curt = dir_solar / f"curtailment_horario_{n_days}d.png"
    solar_pot = dir_solar / f"potencial_horario_{n_days}d.png"
    _plot_hourly_curtailment(df_solar, solar_curt, title_suffix=" - Solar", n_days=n_days)
    _plot_hourly_potential(df_solar, solar_pot, title_suffix=" - Solar", n_days=n_days)

    return (
        total_curt,
        total_pot,
        eolica_curt,
        eolica_pot,
        solar_curt,
        solar_pot,
    )


