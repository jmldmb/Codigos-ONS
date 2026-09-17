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

_RE_ANO_MES = re.compile(r"_(\d{4})_(\d{2})\.(parquet|csv)$")
_RE_ANO = re.compile(r"_(\d{4})\.(parquet|csv)$")


def _ler(p: Path, columns: list[str] | None = None) -> pd.DataFrame:
    """Lê parquet ou csv (ONS: separador ';') com as colunas pedidas."""
    if p.suffix == ".parquet":
        return pd.read_parquet(p, columns=columns)
    return pd.read_csv(p, sep=";", usecols=columns, encoding="utf-8", low_memory=False)


def _arquivos(name: str, inicio: str, fim: str) -> list[Path]:
    """Arquivos parquet do dataset cujo ano/mês intersecta [inicio, fim]."""
    ini, end = pd.Timestamp(inicio), pd.Timestamp(fim)
    out = []
    for p in sorted(list(dataset_dir(name).glob("*.parquet")) + list(dataset_dir(name).glob("*.csv"))):
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


def iterar_termica_despacho(colunas: list[str], inicio: str | None = None, fim: str | None = None,
                            colunas_extra: list[str] | None = None) -> Iterator[pd.DataFrame]:
    """Itera os arquivos mensais de despacho térmico (colunas `val_*` convertidas para float; `colunas_extra` como estão)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    for p in _arquivos("termica_despacho", inicio, fim):
        df = pd.read_parquet(p, columns=["din_instante", *colunas, *(colunas_extra or [])])
        for c in colunas:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        yield _filtrar_periodo(df, inicio, fim)


def carregar_cmo(subsistema: str | None = "config",
                 inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """CMO semi-horário (din_instante, val_cmo) de um subsistema ("config" = config.carga_liquida.cmo_subsistema;
    None = todos, com coluna id_subsistema)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    dfs = [pd.read_parquet(p) for p in _arquivos("cmo", inicio, fim)]
    df = pd.concat(dfs, ignore_index=True)
    df["val_cmo"] = pd.to_numeric(df["val_cmo"], errors="coerce")
    df = _filtrar_periodo(df, inicio, fim)
    if subsistema is None:
        df["id_subsistema"] = df["id_subsistema"].astype(str).str.upper().str.strip()
        return df[["din_instante", "id_subsistema", "val_cmo"]].sort_values("din_instante").reset_index(drop=True)
    if subsistema == "config":
        subsistema = load_config()["carga_liquida"]["cmo_subsistema"]
    df = df[df["nom_subsistema"].str.upper() == subsistema.upper()]
    return df[["din_instante", "val_cmo"]].sort_values("din_instante").reset_index(drop=True)


def carregar_cvu(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """CVU semanal por usina térmica (dat_iniciosemana, num_revisao, cod_usinaplanejamento, nom_usina, val_cvu)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    df = pd.concat([pd.read_parquet(p) for p in _arquivos("cvu", inicio, fim)], ignore_index=True)
    df["dat_iniciosemana"] = pd.to_datetime(df["dat_iniciosemana"])
    df["val_cvu"] = pd.to_numeric(df["val_cvu"], errors="coerce")
    df = df.dropna(subset=["cod_usinaplanejamento", "val_cvu"])
    df["cod_usinaplanejamento"] = df["cod_usinaplanejamento"].astype(int)
    df = df[(df["dat_iniciosemana"] >= inicio) & (df["dat_iniciosemana"] <= fim)]
    return df[["dat_iniciosemana", "num_revisao", "cod_usinaplanejamento", "nom_usina", "val_cvu"]].reset_index(drop=True)


def carregar_disponibilidade_termica(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Disponibilidade operacional declarada das térmicas (UTE/UTN), média por semana operativa e CEG:
    (semana, ceg, nom_usina, disp_operacional_mw, potencia_instalada_mw, nuclear)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    partes = []
    for p in _arquivos("disponibilidade", inicio, fim):
        df = _ler(p, ["id_tipousina", "nom_usina", "ceg", "din_instante", "val_potenciainstalada", "val_dispoperacional"])
        df = df[df["id_tipousina"].isin(["UTE", "UTN"])].copy()
        for c in ("val_potenciainstalada", "val_dispoperacional"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["din_instante"] = pd.to_datetime(df["din_instante"])
        df["semana"] = (df["din_instante"] - pd.to_timedelta((df["din_instante"].dt.weekday + 2) % 7, unit="D")).dt.normalize()
        partes.append(df.groupby(["semana", "ceg"]).agg(nom_usina=("nom_usina", "first"), disp_operacional_mw=("val_dispoperacional", "mean"),
                                                         potencia_instalada_mw=("val_potenciainstalada", "mean"),
                                                         nuclear=("id_tipousina", lambda s: bool((s == "UTN").any()))))
    if not partes:
        raise FileNotFoundError("Sem arquivos de disponibilidade. Rode: python run.py baixar disponibilidade")
    df = pd.concat(partes).groupby(level=[0, 1]).agg(nom_usina=("nom_usina", "first"), disp_operacional_mw=("disp_operacional_mw", "mean"),
                                                      potencia_instalada_mw=("potencia_instalada_mw", "mean"), nuclear=("nuclear", "max"))
    return df.reset_index()


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


def carregar_balanco(subsistema: str = "SIN", inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Balanço de energia horário (val_carga, val_gerhidraulica, val_gertermica, val_gereolica, val_gersolar, ...).

    `val_gertermica` inclui nuclear. Linha 'SIN' = total do sistema.
    """
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    dfs = [pd.read_parquet(p) for p in _arquivos("balanco", inicio, fim)]
    df = pd.concat(dfs, ignore_index=True)
    df = df[df["id_subsistema"].astype(str).str.upper().str.strip() == subsistema.upper()].copy()
    for c in df.columns:
        if c.startswith("val_"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    df = _filtrar_periodo(df, inicio, fim)
    return df.drop(columns=["id_subsistema", "nom_subsistema"]).sort_values("din_instante")              .drop_duplicates("din_instante").reset_index(drop=True)


def carregar_ena(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """ENA diária do SIN (soma dos 4 subsistemas): ena_data, ena_bruta_mwmed, ena_armazenavel_mwmed.

    A ENA usada pelo modelo (regressão hidro FD) é a armazenável do SIN, em MWmed.
    Parquets de 2021-22 trazem as colunas numéricas como string.
    """
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    dfs = [pd.read_parquet(p) for p in _arquivos("ena", inicio, fim)]
    df = pd.concat(dfs, ignore_index=True)
    df["ena_data"] = pd.to_datetime(df["ena_data"])
    for c in ("ena_bruta_regiao_mwmed", "ena_armazenavel_regiao_mwmed"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df[(df["ena_data"] >= inicio) & (df["ena_data"] <= fim)]
    sin = df.groupby("ena_data", as_index=False)[["ena_bruta_regiao_mwmed", "ena_armazenavel_regiao_mwmed"]].sum()
    return sin.rename(columns={"ena_bruta_regiao_mwmed": "ena_bruta_mwmed",
                               "ena_armazenavel_regiao_mwmed": "ena_armazenavel_mwmed"})


def _coff_por_patamar(fonte: str, inicio: str, fim: str) -> pd.DataFrame:
    """Constrained-off (eólica|solar) agregado ao SIN por patamar semi-horário: geração, corte e potencial.

    Geração não realizada (GNRa) = val_geracaonaorealizadaapurada quando existe (arquivos >= 2025-01),
    senão max(0, referência - geração) nos patamares com razão de restrição. Valores em MWmed do patamar.
    """
    name = {"eolica": "coff_eolica", "solar": "coff_fotovoltaica"}[fonte]
    partes = []
    for p in _arquivos(name, inicio, fim):
        base = ["din_instante", "val_geracao", "val_geracaoreferencia", "cod_razaorestricao"]
        tem_apurada = "val_geracaonaorealizadaapurada" in pq.read_schema(p).names
        df = pd.read_parquet(p, columns=base + (["val_geracaonaorealizadaapurada"] if tem_apurada else []))
        gnr = df["val_geracaonaorealizadaapurada"].astype(float) if tem_apurada else pd.Series(float("nan"), index=df.index)
        proxy = (df["val_geracaoreferencia"] - df["val_geracao"]).clip(lower=0)
        proxy = proxy.where(df["cod_razaorestricao"].notna(), 0.0)
        df["corte_mw"] = gnr.where(gnr.notna(), proxy).fillna(0.0)
        df["geracao_mw"] = df["val_geracao"].fillna(0.0)
        partes.append(df.groupby("din_instante", as_index=False)[["geracao_mw", "corte_mw"]].sum())
    df = pd.concat(partes, ignore_index=True).groupby("din_instante", as_index=False)[["geracao_mw", "corte_mw"]].sum()
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    df = df[(df["din_instante"] >= inicio) & (df["din_instante"] <= fim)]
    df["potencial_mw"] = df["geracao_mw"] + df["corte_mw"]
    return df.sort_values("din_instante").reset_index(drop=True)


def carregar_coff_horario(fonte: str, inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Geração, corte e potencial (geração + corte) horários do SIN para 'eolica' ou 'solar' (centralizada),
    em MW médios da hora (média dos patamares semi-horários)."""
    ini, end = periodo()
    inicio, fim = inicio or ini, fim or end
    df = _coff_por_patamar(fonte, inicio, fim)
    df["din_instante"] = df["din_instante"].dt.floor("h")
    return df.groupby("din_instante", as_index=False)[["geracao_mw", "corte_mw", "potencial_mw"]].mean()


def carregar_curtailment(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Curtailment eólico + solar horário do SIN (MW médios): curtailment_eolica_mw, curtailment_solar_mw, curtailment_mw."""
    partes = []
    for fonte in ("eolica", "solar"):
        try:
            d = carregar_coff_horario(fonte, inicio, fim)[["din_instante", "corte_mw"]]
        except FileNotFoundError as e:
            logger.warning(str(e))
            continue
        partes.append(d.rename(columns={"corte_mw": f"curtailment_{fonte}_mw"}).set_index("din_instante"))
    if not partes:
        raise FileNotFoundError("Nenhum arquivo RESTRICAO_COFF_* encontrado (datasets coff_eolica / coff_fotovoltaica)")
    wide = pd.concat(partes, axis=1).fillna(0.0)
    wide["curtailment_mw"] = wide.sum(axis=1)
    return wide.reset_index()
