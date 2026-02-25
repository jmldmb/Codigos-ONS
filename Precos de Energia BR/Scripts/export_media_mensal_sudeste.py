#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
import sys
import pandas as pd
import datetime as dt


def _resolve_base_dir() -> Path:
    """Resolve o diretório base deste projeto (pasta `Scripts`)."""
    try:
        if hasattr(sys, "_getframe"):
            base = Path(__file__).resolve().parent
        else:
            base = Path.cwd()

        if base.name != "Scripts":
            for parent in base.parents:
                candidate = parent / "Scripts"
                if candidate.exists():
                    base = candidate
                    break

        return base
    except Exception as exc:
        raise RuntimeError(f"Falha ao resolver diretório base: {exc}")


def _check_parquet_dependency() -> None:
    """Garante que há backend de parquet disponível."""
    try:
        import pyarrow  # noqa: F401
        return
    except Exception:
        try:
            import fastparquet  # noqa: F401
            return
        except Exception as exc:
            raise ImportError(
                "Nenhuma dependência de parquet encontrada. Instale `pyarrow` ou `fastparquet`."
            ) from exc


def carregar_base_pld(parquet_path: Path) -> pd.DataFrame:
    """Carrega a base processada de PLD (parquet) com colunas Hora, Submercado, Data, Preço."""
    if not parquet_path.exists():
        raise FileNotFoundError(f"Parquet não encontrado: {parquet_path}")

    _check_parquet_dependency()
    df = pd.read_parquet(parquet_path)
    # Normaliza tipos
    if not pd.api.types.is_datetime64_any_dtype(df.get("Data")):
        df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    return df


def calcular_media_mensal_sudeste(df_pld: pd.DataFrame) -> pd.DataFrame:
    """Calcula preço médio mensal do submercado SUDESTE.

    Retorna DataFrame com colunas: AnoMes, PrecoMedioMensal.
    """
    if "Submercado" not in df_pld.columns or "Preço" not in df_pld.columns or "Data" not in df_pld.columns:
        raise ValueError("Colunas esperadas não encontradas na base: requer 'Submercado', 'Preço', 'Data'")

    # Filtra Sudeste (garantindo case-insensitive)
    df_se = df_pld[df_pld["Submercado"].astype(str).str.upper() == "SUDESTE"].copy()
    if df_se.empty:
        raise ValueError("Não há registros para o submercado 'SUDESTE' na base informada.")

    df_se["Data"] = pd.to_datetime(df_se["Data"], errors="coerce")
    df_se = df_se.dropna(subset=["Data", "Preço"])  # garante datas e preços válidos

    # Agrega por mês calendário
    by_month = (
        df_se.groupby(df_se["Data"].dt.to_period("M"))
             ["Preço"].mean()
             .to_frame("PrecoMedioMensal")
             .sort_index()
             .reset_index()
    )
    # Converte período para string YYYY-MM
    by_month["AnoMes"] = by_month["Data"].astype(str)
    by_month = by_month[["AnoMes", "PrecoMedioMensal"]]
    return by_month


def salvar_excel(df: pd.DataFrame, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(output_path, index=False)
    return output_path


def main() -> int:
    base_dir = _resolve_base_dir()
    root = base_dir.parent

    parquet_path = root / "Data" / "processed" / "pld" / "base_master.parquet"
    df_pld = carregar_base_pld(parquet_path)

    mensal = calcular_media_mensal_sudeste(df_pld)

    today = dt.date.today().strftime("%Y%m%d")
    output_path = root / "report_out" / f"media_mensal_sudeste_{today}.xlsx"
    final_path = salvar_excel(mensal, output_path)

    print(f"Arquivo gerado: {final_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


