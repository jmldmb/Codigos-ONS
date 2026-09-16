"""Carga líquida observada do SIN (dados horários verificados do ONS).

Definição:
    carga_liquida = Hidro_R + termica_flexivel
    Hidro_R           = geração das UHEs classificadas como 'R' (reservatório) no cadastro
    termica_flexivel  = val_verifordemdemeritoacimadainflex + val_verifunitcommitment

É a parcela da carga decidida pelo operador: exclui renováveis, fio d'água (FD) e a
térmica forçada (inflexibilidade, razão elétrica, garantia energética, GFOM, exportação,
reserva, GSUB).

Saídas (Output/observado/):
    carga_liquida_historica.parquet  din_instante, FD, R, termica_flexivel, carga_liquida_historica, ano, mes, dia, hora
    geracao_por_tipo.parquet         geração horária por tipo de usina (hidro aberta em FD/R)
    termica_componentes.parquet      geração térmica horária por componente de despacho
"""
import pandas as pd

from ..config import get_logger, load_config, output_dir
from ..dados import ons

logger = get_logger("observado")

SAIDA = "observado"
ARQ_HISTORICO = "carga_liquida_historica.parquet"
ARQ_GERACAO_TIPO = "geracao_por_tipo.parquet"
ARQ_TERMICA = "termica_componentes.parquet"


def geracao_por_tipo(cadastro: pd.DataFrame) -> pd.DataFrame:
    """Geração horária do SIN por tipo de usina, com a hidrelétrica aberta em 'HIDROELÉTRICA - FD' e '- R'.

    UHEs ausentes do cadastro ficam em 'HIDROELÉTRICA' (sem sufixo) e são listadas no log.
    """
    cfg = load_config()["carga_liquida"]
    tipo_hidro = cfg["tipo_usina_hidro"]
    partes, sem_cadastro = [], set()
    for df in ons.iterar_geracao_usina():
        eh_hidro = df["nom_tipousina"] == tipo_hidro
        df = df.merge(cadastro, on="nom_usina", how="left")
        sem = eh_hidro & df["classificacao"].isna()
        sem_cadastro.update(df.loc[sem, "nom_usina"].unique())
        df["tipo"] = df["nom_tipousina"]
        com_classe = eh_hidro & df["classificacao"].notna()
        df.loc[com_classe, "tipo"] = tipo_hidro + " - " + df.loc[com_classe, "classificacao"]
        partes.append(df.groupby(["din_instante", "tipo"], as_index=False)["val_geracao"].sum())
    if sem_cadastro:
        logger.warning(f"{len(sem_cadastro)} UHEs sem classificação no cadastro (ficam fora de FD/R): "
                       f"{sorted(sem_cadastro)}")
    df = pd.concat(partes, ignore_index=True)
    df = df.groupby(["din_instante", "tipo"], as_index=False)["val_geracao"].sum()
    wide = df.pivot(index="din_instante", columns="tipo", values="val_geracao").sort_index()
    wide.columns.name = None
    return wide.reset_index()


def termica_componentes() -> pd.DataFrame:
    """Geração térmica verificada horária do SIN, somada por componente de despacho."""
    cols = load_config()["carga_liquida"]["componentes_termica_todas"]
    partes = [df.groupby("din_instante", as_index=False)[cols].sum() for df in ons.iterar_termica_despacho(cols)]
    df = pd.concat(partes, ignore_index=True).groupby("din_instante", as_index=False)[cols].sum()
    return df.sort_values("din_instante").reset_index(drop=True)


def calcular_carga_liquida(ger_tipo: pd.DataFrame, termica: pd.DataFrame) -> pd.DataFrame:
    """Combina hidro FD/R e térmica flexível na série horária de carga líquida.

    Horas sem despacho térmico recebem termica_flexivel = 0 (left join a partir da geração).
    """
    cfg = load_config()["carga_liquida"]
    tipo_hidro = cfg["tipo_usina_hidro"]
    df = ger_tipo[["din_instante"]].copy()
    for cls in ("FD", "R"):
        col = f"{tipo_hidro} - {cls}"
        df[cls] = ger_tipo[col].values if col in ger_tipo.columns else 0.0
    flex = termica[["din_instante"]].copy()
    flex["termica_flexivel"] = termica[cfg["componentes_termica_flexivel"]].sum(axis=1)
    df = df.merge(flex, on="din_instante", how="left")
    df["termica_flexivel"] = df["termica_flexivel"].fillna(0.0)
    df["carga_liquida_historica"] = df["R"] + df["termica_flexivel"]
    df["ano"] = df["din_instante"].dt.year
    df["mes"] = df["din_instante"].dt.month
    df["dia"] = df["din_instante"].dt.day
    df["hora"] = df["din_instante"].dt.hour
    return df


def processar(salvar: bool = True) -> pd.DataFrame:
    """Pipeline completo: raw ONS -> carga líquida histórica (+ tabelas auxiliares)."""
    cadastro = ons.carregar_cadastro()
    logger.info(f"Cadastro: {len(cadastro)} UHEs ({(cadastro['classificacao'] == 'R').sum()} R, "
                f"{(cadastro['classificacao'] == 'FD').sum()} FD)")
    ger_tipo = geracao_por_tipo(cadastro)
    logger.info(f"Geração por tipo: {len(ger_tipo):,} horas, tipos={[c for c in ger_tipo.columns if c != 'din_instante']}")
    termica = termica_componentes()
    logger.info(f"Térmica: {len(termica):,} horas")
    df = calcular_carga_liquida(ger_tipo, termica)
    logger.info(f"Carga líquida: {df['din_instante'].min()} -> {df['din_instante'].max()}, {len(df):,} horas, "
                f"média {df['carga_liquida_historica'].mean():,.0f} MW "
                f"(R {df['R'].mean():,.0f} + térmica flex {df['termica_flexivel'].mean():,.0f})")
    if salvar:
        out = output_dir(SAIDA)
        df.to_parquet(out / ARQ_HISTORICO, index=False, compression="snappy")
        df.to_excel(out / ARQ_HISTORICO.replace(".parquet", ".xlsx"), index=False)
        ger_tipo.to_parquet(out / ARQ_GERACAO_TIPO, index=False, compression="snappy")
        termica.to_parquet(out / ARQ_TERMICA, index=False, compression="snappy")
        logger.info(f"Salvo em {out}")
    return df


def carregar_historico() -> pd.DataFrame:
    return _carregar(ARQ_HISTORICO)


def carregar_geracao_por_tipo() -> pd.DataFrame:
    return _carregar(ARQ_GERACAO_TIPO)


def carregar_termica_componentes() -> pd.DataFrame:
    return _carregar(ARQ_TERMICA)


def _carregar(nome: str) -> pd.DataFrame:
    path = output_dir(SAIDA) / nome
    if not path.exists():
        raise FileNotFoundError(f"{path} não existe. Rode: python run.py processar")
    df = pd.read_parquet(path)
    df["din_instante"] = pd.to_datetime(df["din_instante"])
    return df
