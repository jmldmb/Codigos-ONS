"""Leitura dos dados brutos do ONS já baixados (Data/raw/...).

Os arquivos mensais de geração por usina e de despacho térmico são grandes (centenas de
milhares de linhas, colunas numéricas como string); por isso os leitores são geradores
por arquivo, e a agregação acontece em observado/ antes de concatenar.
"""
import re
from collections.abc import Iterator
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

from ..config import data_dir, dataset_dir, get_logger, load_config, periodo

logger = get_logger("dados")

_RE_ANO_MES = re.compile(r"_(\d{4})_(\d{2})\.parquet$")
_RE_ANO = re.compile(r"_(\d{4})\.parquet$")


def _arquivos(name: str, inicio: str, fim: str) -> list[Path]:
    """Arquivos parquet do dataset cujo ano/mês intersecta [inicio, fim]."""
    ini, end = pd.Timestamp(inicio), pd.Timestamp(fim)
    out = []
    for p in sorted(dataset_dir(name).glob("*.parquet")):
        m = _RE_ANO_MES.search(p.name)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            if (y, mo) < (ini.year, ini.month) or (y, mo) > (end.year, end.month):
                continue
        else:
            m = _RE_ANO.search(p.name)
            if m and not (ini.year <= int(m.group(1)) <= end.year):
                continue
        out.append(p)
    if not out:
        raise FileNotFoundError(f"Nenhum arquivo de '{name}' em {dataset_dir(name)} para {inicio}..{fim}. "
                                f"Rode: python run.py baixar {name}")
    return out


def _filtrar_periodo(df: pd.DataFrame, inicio: str, fim: str) -> pd.DataFrame:
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    return df[(df["din_instante"] >= inicio) & (df["din_instante"] <= fim)]


def iterar_geracao_usina(colunas: list[str] | None = None,
                         inicio: str | None = None, fim: str | None = None) -> Iterator[pd.DataFrame]:
    """Itera os arquivos mensais de geração por usina, um DataFrame por arquivo.

    `val_geracao` vem como string decimal no parquet do ONS -> convertido para float.
    """
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    colunas = colunas or ["din_instante", "nom_tipousina", "nom_usina", "val_geracao"]
    for p in _arquivos("geracao_usina", inicio, fim):
        df = pd.read_parquet(p, columns=colunas)
        df["val_geracao"] = pd.to_numeric(df["val_geracao"], errors="coerce")
        logger.debug(f"geracao_usina {p.name}: {len(df):,} linhas")
        yield _filtrar_periodo(df, inicio, fim)


def iterar_termica_despacho(colunas: list[str],
                            inicio: str | None = None, fim: str | None = None) -> Iterator[pd.DataFrame]:
    """Itera os arquivos mensais de despacho térmico (colunas `val_*` convertidas para float)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    for p in _arquivos("termica_despacho", inicio, fim):
        df = pd.read_parquet(p, columns=["din_instante", *colunas])
        for c in colunas:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        yield _filtrar_periodo(df, inicio, fim)


def carregar_cmo(subsistema: str | None = None,
                 inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """CMO semi-horário (din_instante, val_cmo) de um subsistema (default config.carga_liquida.cmo_subsistema)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    subsistema = subsistema or load_config()["carga_liquida"]["cmo_subsistema"]
    dfs = [pd.read_parquet(p) for p in _arquivos("cmo", inicio, fim)]
    df = pd.concat(dfs, ignore_index=True)
    df = df[df["nom_subsistema"].str.upper() == subsistema.upper()].copy()
    df["val_cmo"] = pd.to_numeric(df["val_cmo"], errors="coerce")
    df = _filtrar_periodo(df, inicio, fim)
    return df[["din_instante", "val_cmo"]].sort_values("din_instante").reset_index(drop=True)


def carregar_cadastro() -> pd.DataFrame:
    """Cadastro manual de UHEs: colunas normalizadas para (nom_usina, classificacao) com valores 'R'|'FD'."""
    path = data_dir() / load_config()["cadastro"]["arquivo"]
    if not path.exists():
        raise FileNotFoundError(f"Cadastro de UHEs não encontrado: {path}")
    cad = pd.read_excel(path)
    col_cls = next((c for c in cad.columns if str(c).lower().startswith("classifica")), None)
    if col_cls is None or "nom_usina" not in cad.columns:
        raise ValueError(f"Cadastro deve ter colunas 'nom_usina' e 'Classificação'; encontrado {list(cad.columns)}")
    cad = cad.rename(columns={col_cls: "classificacao"})[["nom_usina", "classificacao"]]
    cad["classificacao"] = cad["classificacao"].astype(str).str.strip().str.upper()
    # nomes novos usados pelo ONS herdam a classificação do nome cadastrado
    aliases = load_config()["cadastro"].get("aliases") or {}
    extras = [{"nom_usina": novo, "classificacao": cls}
              for novo, antigo in aliases.items()
              for cls in cad.loc[cad["nom_usina"] == antigo, "classificacao"].head(1)]
    faltando = [a for a in aliases.values() if a not in set(cad["nom_usina"])]
    if faltando:
        logger.warning(f"Aliases apontam para usinas ausentes do cadastro: {faltando}")
    cad = pd.concat([cad, pd.DataFrame(extras)], ignore_index=True)
    invalidas = set(cad["classificacao"]) - {"R", "FD"}
    if invalidas:
        raise ValueError(f"Classificações inválidas no cadastro: {invalidas}")
    dup = cad[cad["nom_usina"].duplicated()]
    if not dup.empty:
        logger.warning(f"Cadastro com usinas duplicadas (mantida a primeira): {dup['nom_usina'].tolist()}")
        cad = cad.drop_duplicates("nom_usina")
    return cad.reset_index(drop=True)


def carregar_curtailment(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Curtailment eólico + solar (constrained-off) horário do SIN, em MW médios.

    Lê os parquets RESTRICAO_COFF_* já baixados pelo módulo baterias/ (config.paths.coff_*_dir).
    Geração não realizada por patamar semi-horário = val_geracaonaorealizadaapurada quando existe
    (arquivos >= 2025-01), senão max(0, referência - geração) nos patamares com razão de restrição.
    Hora = média dos dois patamares (MWmed).
    """
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    cfg = load_config()["paths"]
    ini_ts, end_ts = pd.Timestamp(inicio), pd.Timestamp(fim)
    partes = []
    for key, fonte in (("coff_eolica_dir", "eolica"), ("coff_fotovoltaica_dir", "solar")):
        d = Path(cfg[key])
        if not d.exists():
            logger.warning(f"Pasta de curtailment não encontrada: {d}")
            continue
        for p in sorted(d.glob("RESTRICAO_COFF_*.parquet")):
            m = _RE_ANO_MES.search(p.name)
            if m and ((int(m.group(1)), int(m.group(2))) < (ini_ts.year, ini_ts.month)
                      or (int(m.group(1)), int(m.group(2))) > (end_ts.year, end_ts.month)):
                continue
            base = ["din_instante", "val_geracao", "val_geracaoreferencia", "cod_razaorestricao"]
            tem_apurada = "val_geracaonaorealizadaapurada" in pq.read_schema(p).names  # só >= 2025-01
            df = pd.read_parquet(p, columns=base + (["val_geracaonaorealizadaapurada"] if tem_apurada else []))
            gnr = df["val_geracaonaorealizadaapurada"].astype(float) if tem_apurada else pd.Series(float("nan"), index=df.index)
            proxy = (df["val_geracaoreferencia"] - df["val_geracao"]).clip(lower=0)
            proxy = proxy.where(df["cod_razaorestricao"].notna(), 0.0)
            df["curtailment_mw"] = gnr.where(gnr.notna(), proxy).fillna(0.0)
            df["fonte"] = fonte
            partes.append(df.groupby(["din_instante", "fonte"], as_index=False)["curtailment_mw"].sum())
    if not partes:
        raise FileNotFoundError("Nenhum arquivo RESTRICAO_COFF_* encontrado (config.paths.coff_*_dir)")
    df = pd.concat(partes, ignore_index=True)  # total do SIN por patamar semi-horário e fonte
    df["din_instante"] = pd.to_datetime(df["din_instante"]).dt.floor("h")
    df = df[(df["din_instante"] >= inicio) & (df["din_instante"] <= fim)]
    # MWmed por patamar -> média dos patamares da hora
    wide = df.pivot_table(index="din_instante", columns="fonte", values="curtailment_mw", aggfunc="mean")
    wide = wide.rename(columns={"eolica": "curtailment_eolica_mw", "solar": "curtailment_solar_mw"}).fillna(0.0)
    wide["curtailment_mw"] = wide.sum(axis=1)
    return wide.reset_index()
