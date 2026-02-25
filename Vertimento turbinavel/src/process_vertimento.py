import argparse
from pathlib import Path
from typing import Iterable, List

import numpy as np
import pandas as pd


def list_parquet_files(root: Path) -> List[Path]:
    return sorted(root.rglob("*.parquet"))


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_month_year(df: pd.DataFrame) -> pd.DataFrame:
    if "din_instante" not in df.columns:
        raise KeyError("Coluna 'din_instante' não encontrada no dataset.")
    if not np.issubdtype(df["din_instante"].dtype, np.datetime64):
        df["din_instante"] = pd.to_datetime(df["din_instante"], errors="coerce", utc=False)
    df["ano"] = df["din_instante"].dt.year
    df["mes"] = df["din_instante"].dt.month
    return df


def resolve_numeric_range_columns(df: pd.DataFrame) -> List[str]:
    columns = list(df.columns)
    try:
        start_idx = columns.index("val_geracao")
        end_idx = columns.index("val_energiavertidaturbinavel")
    except ValueError as exc:
        raise KeyError(
            "As colunas de faixa 'val_geracao' e/ou 'val_energiavertidaturbinavel' não foram encontradas."
        ) from exc

    if start_idx > end_idx:
        start_idx, end_idx = end_idx, start_idx
    candidate_cols = columns[start_idx : end_idx + 1]
    # Keep only numeric columns among the candidates
    numeric_cols = [c for c in candidate_cols if pd.api.types.is_numeric_dtype(df[c])]
    return numeric_cols


def aggregate_monthly_by_usina(df: pd.DataFrame) -> pd.DataFrame:
    df = parse_month_year(df)
    numeric_cols = resolve_numeric_range_columns(df)

    group_keys = ["ano", "mes", "cod_usina"]
    # Categorical columns: keep first non-null per group
    exclude_cols = set(numeric_cols + ["din_instante"]) | set(group_keys)
    cat_cols = [c for c in df.columns if c not in exclude_cols]

    numeric_agg = (
        df.groupby(group_keys, dropna=False)[numeric_cols]
        .mean(numeric_only=True)
        .reset_index()
    )

    if cat_cols:
        cat_agg = (
            df.groupby(group_keys, dropna=False)[cat_cols]
            .agg(lambda s: s.dropna().iloc[0] if len(s.dropna()) else np.nan)
            .reset_index()
        )
        merged = pd.merge(numeric_agg, cat_agg, on=group_keys, how="left")
    else:
        merged = numeric_agg

    return merged


def aggregate_monthly_by_subsistema(monthly_usina: pd.DataFrame) -> pd.DataFrame:
    # We expect 'nom_subsistema' to be present in the categorical columns kept above
    required_cols = {"ano", "mes", "nom_subsistema"}
    if not required_cols.issubset(monthly_usina.columns):
        missing = required_cols - set(monthly_usina.columns)
        raise KeyError(f"Colunas necessárias ausentes para agregação por subsistema: {missing}")

    numeric_cols = [
        c
        for c in monthly_usina.columns
        if pd.api.types.is_numeric_dtype(monthly_usina[c]) and c not in ("ano", "mes", "cod_usina")
    ]

    group_keys = ["ano", "mes", "nom_subsistema"]
    monthly_subsistema = (
        monthly_usina.groupby(group_keys, dropna=False)[numeric_cols]
        .sum(numeric_only=True)
        .reset_index()
    )
    return monthly_subsistema


def run_processing(
    input_root: Path,
    output_root: Path,
) -> None:
    input_root = input_root.resolve()
    output_root = output_root.resolve()
    ensure_directory(output_root)

    files = list_parquet_files(input_root)
    if not files:
        print(f"Nenhum arquivo Parquet encontrado em: {input_root}")
        return

    print(f"Processando {len(files)} arquivos de entrada...")
    monthly_parts: List[pd.DataFrame] = []
    for file_path in files:
        try:
            df = pd.read_parquet(file_path)
            monthly_part = aggregate_monthly_by_usina(df)
            monthly_parts.append(monthly_part)
        except Exception as exc:  # noqa: BLE001
            print(f"Falha ao processar {file_path.name}: {exc}")

    if not monthly_parts:
        print("Nenhum dado processado.")
        return

    monthly_by_usina = pd.concat(monthly_parts, ignore_index=True)
    # Reagrupar para garantir unicidade por [ano, mes, cod_usina]
    numeric_cols = [
        c
        for c in monthly_by_usina.columns
        if pd.api.types.is_numeric_dtype(monthly_by_usina[c]) and c not in ("ano", "mes", "cod_usina")
    ]
    group_keys = ["ano", "mes", "cod_usina"]
    monthly_by_usina = (
        monthly_by_usina.groupby(group_keys, dropna=False)
        .agg({**{c: "mean" for c in numeric_cols}, **{c: "first" for c in monthly_by_usina.columns if c not in numeric_cols + group_keys}})
        .reset_index()
    )

    # Agregação por subsistema
    monthly_by_subsistema = aggregate_monthly_by_subsistema(monthly_by_usina)

    # Saídas
    out_usina = output_root / "monthly_by_usina.parquet"
    out_subsis = output_root / "monthly_by_subsistema.parquet"
    out_subsis_xlsx = output_root / "monthly_by_subsistema.xlsx"
    monthly_by_usina.to_parquet(out_usina, index=False)
    monthly_by_subsistema.to_parquet(out_subsis, index=False)

    print(f"Salvo: {out_usina}")
    print(f"Salvo: {out_subsis}")
    # Excel export (optional dependency: openpyxl or xlsxwriter)
    try:
        monthly_by_subsistema.to_excel(out_subsis_xlsx, index=False)
        print(f"Salvo: {out_subsis_xlsx}")
    except Exception as exc:  # noqa: BLE001
        print(
            "Falha ao exportar Excel (instale 'openpyxl' ou 'xlsxwriter'): " f"{exc}"
        )


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Processa os Parquets de vertimento (hora x usina) e agrega por mês: "
            "(1) média por usina (colunas numéricas entre val_geracao e val_energiavertidaturbinavel), "
            "(2) média por nom_subsistema."
        )
    )
    default_input = Path(__file__).resolve().parents[1] / "data" / "raw" / "vertimento"
    default_output = (
        Path(__file__).resolve().parents[1] / "data" / "processed" / "vertimento"
    )
    parser.add_argument("--input", type=Path, default=default_input, help=f"Diretório raiz de entrada (default: {default_input})")
    parser.add_argument("--output", type=Path, default=default_output, help=f"Diretório de saída (default: {default_output})")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> None:
    args = parse_args(argv)
    ensure_directory(args.output)
    run_processing(args.input, args.output)


if __name__ == "__main__":
    main()


