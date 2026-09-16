"""
Processamento auxiliar de curtailment (isolado do modelo principal)

Leitura de CSVs do ONS (eólica e fotovoltaica), cálculo de curtailment em MWh
e agregação mensal a nível Brasil.

Saídas (Parquet):
  - output/curtailment/curtailment_raw.parquet
  - output/curtailment/brasil_mensal.parquet

Padrões de arquivo esperados no diretório de entrada:
  - RESTRICAO_COFF_EOLICA_YYYY_MM.csv
  - RESTRICAO_COFF_FOTOVOLTAICA_YYYY_MM.csv

Uso programático:
  from auxiliar.curtailment.processor import process_and_save
  process_and_save()
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd


# Diretórios padrão (pode ser sobrescrito via parâmetros da função)
DEFAULT_INPUT_DIR = Path(
    r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\Curtailment\Dados\raw_data"
)

# __file__ está em: mini_dessem/Scripts/src/auxiliar/curtailment/processor.py
# Raiz do projeto mini_dessem = parents[4]
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[4]
DEFAULT_OUTPUT_DIR = _PROJECT_ROOT / "output" / "curtailment"


def _parse_year_month_from_filename(path: Path) -> Optional[Tuple[int, int]]:
    """Extrai (ano, mes) do nome do arquivo esperado *_YYYY_MM.csv.

    Retorna None se o padrão não for encontrado.
    """
    try:
        parts = path.stem.split("_")
        year = int(parts[-2])
        month = int(parts[-1])
        return year, month
    except Exception:
        return None


def _discover_files(input_dir: Path) -> List[Path]:
    """Lista todos os arquivos de curtailment válidos no diretório."""
    files = sorted(input_dir.glob("RESTRICAO_COFF_*.csv"))
    valid = []
    for f in files:
        ym = _parse_year_month_from_filename(f)
        if ym is not None:
            valid.append(f)
    return valid


def _compute_auto_end(input_dir: Path) -> pd.Timestamp:
    """Determina a data fim (auto): min(hoje, fim do mês mais recente disponível)."""
    files = _discover_files(input_dir)
    if not files:
        # Se não houver arquivos, usa hoje
        return pd.Timestamp(datetime.now().date())

    dates = []
    for f in files:
        ym = _parse_year_month_from_filename(f)
        if ym is None:
            continue
        y, m = ym
        dates.append(pd.Timestamp(f"{y}-{m:02d}-01"))

    if not dates:
        return pd.Timestamp(datetime.now().date())

    latest_month = max(dates)
    month_end = latest_month + pd.offsets.MonthEnd(0)
    today = pd.Timestamp(datetime.now().date())
    return min(today, month_end)


def _read_single_csv(path: Path) -> pd.DataFrame:
    """Lê um CSV do ONS com separador ';' e tipagem adequada."""
    df = pd.read_csv(
        path,
        sep=";",
        low_memory=False,
        dtype={"cod_razaorestricao": "string"},
    )

    # Anotar tipo de usina com base no nome
    stem = path.stem.upper()
    if "EOLICA" in stem:
        df["tipo_usina"] = "eolica"
    elif "FOTOVOLTAICA" in stem:
        df["tipo_usina"] = "solar"
    else:
        df["tipo_usina"] = "desconhecida"

    return df


def _load_raw(inicio: pd.Timestamp, fim: pd.Timestamp, input_dir: Path) -> pd.DataFrame:
    """Carrega os CSVs dentro do período desejado (por mês do arquivo)."""
    dfs: List[pd.DataFrame] = []
    files = _discover_files(input_dir)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo RESTRICAO_COFF_* encontrado em {input_dir}")

    for f in files:
        ym = _parse_year_month_from_filename(f)
        if ym is None:
            continue
        y, m = ym
        file_month = pd.Timestamp(f"{y}-{m:02d}-01")
        # Carregar somente meses dentro do intervalo solicitado
        if file_month < (inicio.replace(day=1)) or file_month > (fim.replace(day=1)):
            continue
        try:
            df = _read_single_csv(f)
            dfs.append(df)
        except Exception:
            # Ignora arquivos com problemas (ex.: meses faltantes de FV)
            continue

    if not dfs:
        raise ValueError("Nenhum dado carregado no período solicitado.")

    return pd.concat(dfs, ignore_index=True)


def _transform(df: pd.DataFrame) -> pd.DataFrame:
    """Aplica conversões para MWh, datas e calcula curtailment."""
    df = df.copy()

    # Conversões 30-min -> MWh
    for col in ("val_geracao", "val_disponibilidade", "val_geracaoreferencia"):
        if col in df.columns:
            df[f"{col}_mwh"] = df[col] * 0.5

    # Datas
    df["din_instante"] = pd.to_datetime(df["din_instante"], errors="coerce")
    df = df[df["din_instante"].notna()].copy()
    df["data"] = df["din_instante"].dt.floor("D")

    # Razão de restrição
    if "cod_razaorestricao" not in df.columns:
        df["cod_razaorestricao"] = "SR"
    else:
        df["cod_razaorestricao"] = df["cod_razaorestricao"].fillna("SR")

    # Curtailment
    for needed in ("val_disponibilidade_mwh", "val_geracaoreferencia_mwh", "val_geracao_mwh"):
        if needed not in df.columns:
            df[needed] = np.nan

    df["val_curtail_mwh"] = np.maximum(
        np.minimum(df["val_disponibilidade_mwh"], df["val_geracaoreferencia_mwh"]) - df["val_geracao_mwh"],
        0,
    )

    return df


def _filter_period(df: pd.DataFrame, inicio: pd.Timestamp, fim: pd.Timestamp) -> pd.DataFrame:
    """Filtra linhas por intervalo de data (coluna 'data')."""
    mask = (df["data"] >= inicio) & (df["data"] <= fim)
    return df.loc[mask].copy()


def _aggregate_brazil_monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados a nível Brasil por mês, separando tipos de restrição."""
    # Agregação diária com corte por tipo de restrição
    agr_dia = (
        df.groupby(["data", "cod_razaorestricao"], dropna=False)
        .agg(
            geracao_est_mwh=("val_geracaoreferencia_mwh", "sum"),
            curt_mwh=("val_curtail_mwh", "sum"),
        )
        .reset_index()
    )

    agr_dia["mes"] = agr_dia["data"].dt.to_period("M")

    mensal = (
        agr_dia.groupby(["mes"], as_index=False)
        .agg(
            geracao_est_mwh=("geracao_est_mwh", "sum"),
            curt_ENE_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "ENE"].sum()),
            curt_CNF_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "CNF"].sum()),
            curt_REL_mwh=("curt_mwh", lambda x: x[agr_dia.loc[x.index, "cod_razaorestricao"] == "REL"].sum()),
        )
    )

    den = mensal["geracao_est_mwh"].replace({0: np.nan})
    mensal["pct_ENE"] = mensal["curt_ENE_mwh"] / den
    mensal["pct_CNF"] = mensal["curt_CNF_mwh"] / den
    mensal["pct_REL"] = mensal["curt_REL_mwh"] / den

    # Converter período para timestamp (início do mês) para compatibilidade Parquet
    mensal["mes"] = mensal["mes"].dt.to_timestamp()

    cols_order = [
        "mes",
        "geracao_est_mwh",
        "curt_ENE_mwh",
        "curt_CNF_mwh",
        "curt_REL_mwh",
        "pct_ENE",
        "pct_CNF",
        "pct_REL",
    ]
    return mensal[cols_order]


def process_and_save(
    inicio: str = "2021-01-01",
    fim: str = "auto",
    input_dir: Optional[Path | str] = None,
    output_dir: Optional[Path | str] = None,
) -> Tuple[Path, Path]:
    """Processa dados e salva Parquet do bruto e do agregado Brasil mensal.

    Retorna (path_curta_raw, path_brasil_mensal).
    """
    in_dir = Path(input_dir) if input_dir is not None else DEFAULT_INPUT_DIR
    out_dir = Path(output_dir) if output_dir is not None else DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    inicio_ts = pd.Timestamp(inicio)
    fim_ts = _compute_auto_end(in_dir) if str(fim).lower() == "auto" else pd.Timestamp(fim)

    # Carregar
    df_raw = _load_raw(inicio_ts, fim_ts, in_dir)

    # Transformar e filtrar
    df_tr = _transform(df_raw)
    df_tr = _filter_period(df_tr, inicio_ts, fim_ts)

    # Agregar Brasil
    df_brasil = _aggregate_brazil_monthly(df_tr)

    # Salvar
    path_raw = out_dir / "curtailment_raw.parquet"
    total_dir = out_dir / "total"
    total_dir.mkdir(parents=True, exist_ok=True)
    path_brasil = total_dir / "brasil_mensal_total.parquet"

    df_tr.to_parquet(path_raw, index=False, compression="snappy")
    df_brasil.to_parquet(path_brasil, index=False, compression="snappy")

    return path_raw, path_brasil


__all__ = ["process_and_save"]


