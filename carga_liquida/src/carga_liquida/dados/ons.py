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
    """Constrained-off (eólica|solar) agregado ao SIN por patamar semi-horário: geração, corte (total, energético
    e de rede) e potencial.

    Geração não realizada (GNRa) = val_geracaonaorealizadaapurada quando existe (arquivos >= 2025-01),
    senão max(0, referência - geração) nos patamares com razão de restrição. Valores em MWmed do patamar.
    Sem restrição: `cod_razaorestricao` é '' até 2024-12 e NaN a partir de 2025-01 — os dois são tratados como
    "sem corte" (contar o '' como restrição inflava o potencial em ~0,5 GW médios em 2024).
    corte_ene_mw = razão ENE (sobra de energia no SIN, o que o despacho reproduz); corte_rede_mw = demais razões
    (CNF confiabilidade, REL elétrica: restrições regionais de transmissão, quase todo NE).
    """
    name = {"eolica": "coff_eolica", "solar": "coff_fotovoltaica"}[fonte]
    cols = ["geracao_mw", "corte_mw", "corte_ene_mw", "corte_rede_mw"]
    partes = []
    for p in _arquivos(name, inicio, fim):
        base = ["din_instante", "val_geracao", "val_geracaoreferencia", "cod_razaorestricao"]
        tem_apurada = "val_geracaonaorealizadaapurada" in pq.read_schema(p).names
        df = pd.read_parquet(p, columns=base + (["val_geracaonaorealizadaapurada"] if tem_apurada else []))
        razao = df["cod_razaorestricao"].astype("string").str.strip().replace("", pd.NA)
        gnr = df["val_geracaonaorealizadaapurada"].astype(float) if tem_apurada else pd.Series(float("nan"), index=df.index)
        proxy = (df["val_geracaoreferencia"] - df["val_geracao"]).clip(lower=0).where(razao.notna(), 0.0)
        df["corte_mw"] = gnr.where(gnr.notna(), proxy).fillna(0.0).where(razao.notna(), 0.0)
        df["corte_ene_mw"] = df["corte_mw"].where((razao == "ENE").fillna(False), 0.0)
        df["corte_rede_mw"] = df["corte_mw"] - df["corte_ene_mw"]
        df["geracao_mw"] = df["val_geracao"].fillna(0.0)
        partes.append(df.groupby("din_instante", as_index=False)[cols].sum())
    df = pd.concat(partes, ignore_index=True).groupby("din_instante", as_index=False)[cols].sum()
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
    return df.groupby("din_instante", as_index=False)[["geracao_mw", "corte_mw", "corte_ene_mw", "corte_rede_mw", "potencial_mw"]].mean()


def carregar_capacidade_mensal(tipo: str = "EOLIELÉTRICA") -> pd.Series:
    """Capacidade instalada (MW, soma da potência efetiva das unidades em operação no fim do mês) por mês, para o tipo de
    usina cujo nome contém `tipo` (nom_tipousina: EOLIELÉTRICA, FOTOVOLTAICA, TÉRMICA...; dataset `capacidade`). Índice: Period mensal."""
    p = dataset_dir("capacidade") / "CAPACIDADE_GERACAO.parquet"
    if not p.exists():
        raise FileNotFoundError(f"{p} não existe. Rode: python run.py baixar capacidade")
    d = pd.read_parquet(p, columns=["nom_tipousina", "dat_entradaoperacao", "dat_entradateste", "dat_desativacao", "val_potenciaefetiva"])
    d = d[d["nom_tipousina"].astype(str).str.upper().str.contains(tipo.upper())].copy()
    d["ini"] = pd.to_datetime(d["dat_entradaoperacao"].fillna(d["dat_entradateste"]))
    d["fim"] = pd.to_datetime(d["dat_desativacao"])
    ini, end = periodo()
    meses = pd.period_range(pd.Timestamp(ini), pd.Timestamp(end), freq="M")
    return pd.Series({m: float(d[(d["ini"] <= m.end_time) & (d["fim"].isna() | (d["fim"] > m.end_time))]["val_potenciaefetiva"].sum())
                      for m in meses}, name="capacidade_mw")


def carregar_curtailment(inicio: str | None = None, fim: str | None = None) -> pd.DataFrame:
    """Curtailment eólico + solar horário do SIN (MW médios): curtailment_{eolica|solar}_mw (total) e as parcelas
    curtailment_{eolica|solar}_{ene|rede}_mw; totais curtailment_mw, curtailment_ene_mw, curtailment_rede_mw."""
    partes = []
    for fonte in ("eolica", "solar"):
        try:
            d = carregar_coff_horario(fonte, inicio, fim)[["din_instante", "corte_mw", "corte_ene_mw", "corte_rede_mw"]]
        except FileNotFoundError as e:
            logger.warning(str(e))
            continue
        partes.append(d.rename(columns={"corte_mw": f"curtailment_{fonte}_mw", "corte_ene_mw": f"curtailment_{fonte}_ene_mw",
                                        "corte_rede_mw": f"curtailment_{fonte}_rede_mw"}).set_index("din_instante"))
    if not partes:
        raise FileNotFoundError("Nenhum arquivo RESTRICAO_COFF_* encontrado (datasets coff_eolica / coff_fotovoltaica)")
    wide = pd.concat(partes, axis=1).fillna(0.0)
    fontes = [c.split("_")[1] for c in wide.columns if c.count("_") == 2]
    for suf in ("", "_ene", "_rede"):
        wide[f"curtailment{suf}_mw"] = wide[[f"curtailment_{f}{suf}_mw" for f in fontes]].sum(axis=1)
    return wide.reset_index()
