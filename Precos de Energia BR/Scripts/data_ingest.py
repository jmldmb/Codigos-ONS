#!/usr/bin/env python
# coding: utf-8

# In[3]:


import pandas as pd
import requests
from datetime import datetime, timedelta
from urllib.parse import urlencode
from pathlib import Path
import urllib3
import sys
import csv 
import io     

# ---------------- CONFIGURAÇÕES ----------------

# Caminhos relativos à pasta do script atual

# Detecta ambiente interativo (ex: Jupyter Notebook) ou execução via script
if hasattr(sys, 'ps1') or 'ipykernel' in sys.modules:
    BASE_DIR = Path.cwd()
else:
    BASE_DIR = Path(__file__).resolve().parent

PASTA_DOWNLOAD = BASE_DIR.parent / "Data" / "raw" / "pld horario"
PASTA_OUTPUT = BASE_DIR.parent / "Data" / "processed" / "pld"
ARQUIVO_MASTER = PASTA_OUTPUT / "base_master.parquet"
TIPO_PRECO = "HORARIO"

# Ignorar avisos SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ---------------- FUNÇÕES AUXILIARES ----------------

def baixar_ultimos_30_dias(tipo_preco=TIPO_PRECO):
    PASTA_DOWNLOAD.mkdir(parents=True, exist_ok=True)

    data_fim = datetime.today() - timedelta(days=0)
    data_inicio = data_fim - timedelta(days=30)

    data_inicio_str = data_inicio.strftime("%d/%m/%Y")
    data_fim_str = data_fim.strftime("%d/%m/%Y")

    params = {
        "p_p_id": "br_org_ccee_pld_historico_PLDHistoricoPortlet_INSTANCE_lzsn",
        "p_p_lifecycle": "2",
        "p_p_state": "normal",
        "p_p_mode": "view",
        "p_p_cacheability": "cacheLevelPage",
        "_br_org_ccee_pld_historico_PLDHistoricoPortlet_INSTANCE_lzsn_inputInitialDate": data_inicio_str,
        "_br_org_ccee_pld_historico_PLDHistoricoPortlet_INSTANCE_lzsn_inputFinalDate": data_fim_str,
        "_br_org_ccee_pld_historico_PLDHistoricoPortlet_INSTANCE_lzsn_tipoPreco": tipo_preco
    }

    url = f"https://www.ccee.org.br/web/guest/precos/painel-precos?{urlencode(params)}"
    nome_arquivo = f"PLD_{tipo_preco}_{data_inicio.strftime('%Y%m%d')}_{data_fim.strftime('%Y%m%d')}.csv"
    caminho_arquivo = PASTA_DOWNLOAD / nome_arquivo

    print(f" Baixando arquivo: {nome_arquivo}")
    response = requests.get(url, verify=False)
    response.raise_for_status()

    with open(caminho_arquivo, "wb") as f:
        f.write(response.content)

    print(f" Salvo: {caminho_arquivo}")
    return caminho_arquivo
    

def transformar_csv_em_long(caminho_arquivo):
    encodings = ['utf-8-sig', 'latin1']
    for encoding in encodings:
        try:
            # Lê o arquivo inteiro, remove aspas iniciais/finais e monta um buffer em memória
            with open(caminho_arquivo, 'r', encoding=encoding) as f:
                cleaned_text = '\n'.join(
                    line.strip().strip('"')          # tira \n, \r e aspas das bordas
                    for line in f
                )
            buffer = io.StringIO(cleaned_text)       # arquivo virtual

            # Lê o CSV a partir do buffer (nenhum arquivo temporário é criado)
            df_raw = pd.read_csv(
                buffer,
                sep=';',
                engine='python',
                quoting=csv.QUOTE_NONE
            )

            if len(df_raw.columns) > 1:
                break                                # leitura OK; sai do loop
        except Exception as e:
            print(f" Falha com {encoding}: {e}")
            continue
    else:
        print(f" Não foi possível ler {caminho_arquivo.name} com nenhum encoding.")
        return pd.DataFrame()                        # retorna DF vazio, nunca None

    # --- validação e transformação em formato longo ---
    df_raw = df_raw.dropna(how="all")
    id_vars = ['Hora', 'Submercado']
    if not all(col in df_raw.columns for col in id_vars):
        print(f" Ignorando {caminho_arquivo.name}: colunas esperadas não encontradas.")
        print(f"    Colunas encontradas: {df_raw.columns.tolist()}")
        return pd.DataFrame()

    value_vars = [col for col in df_raw.columns if col not in id_vars]
    df_long = df_raw.melt(
        id_vars=id_vars,
        value_vars=value_vars,
        var_name='Data',
        value_name='Preço'
    )
    df_long['Data'] = pd.to_datetime(df_long['Data'], dayfirst=True, errors='coerce')
    df_long = df_long.dropna(subset=['Data'])

    # substitui vírgula decimal por ponto e força numérico
    df_long["Preço"] = (
        df_long["Preço"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    return df_long


def carregar_base_master():
    if ARQUIVO_MASTER.exists():
        return pd.read_parquet(ARQUIVO_MASTER)
    else:
        return pd.DataFrame(columns=["Hora", "Submercado", "Data", "Preço"])

def salvar_base_master(df):
    PASTA_OUTPUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ARQUIVO_MASTER, index=False)
    print(f" Base master atualizada: {ARQUIVO_MASTER}")

# ---------------- PIPELINE PRINCIPAL ----------------

def atualizar_base_master():
    print(" Atualizando base master...")

    # 1. Carregar base master existente
    df_master = carregar_base_master()

    # 2. Consolidar todos os arquivos CSV da pasta em formato long
    todos_arquivos = list(PASTA_DOWNLOAD.glob("*.csv"))
    dfs = [transformar_csv_em_long(arquivo) for arquivo in todos_arquivos]
    dfs = [df for df in dfs if not df.empty]

    if dfs:
        df_historico = pd.concat(dfs, ignore_index=True)
    else:
        print(" Nenhum arquivo histórico válido encontrado.")
        df_historico = pd.DataFrame(columns=["Hora", "Submercado", "Data", "Preço"])

        # --------------    ADICIONE AQUI    --------------
    # Opção A – substitui master vazio ou concatena se já existir algo
    if df_master.empty:
        df_master = df_historico.copy()
    else:
        df_master = pd.concat([df_master, df_historico], ignore_index=True)
    # --------------    ADICIONE AQUI    --------------
    
    # 3. Baixar último mês e transformar
    arquivo_novo = baixar_ultimos_30_dias()
    df_novo = transformar_csv_em_long(arquivo_novo)

    # 4. Remover da master as datas presentes no novo
    datas_novas = df_novo['Data'].unique()
    df_master = df_master[~df_master['Data'].isin(datas_novas)]

    # 5. Juntar e salvar
    df_atualizado = pd.concat([df_master, df_novo], ignore_index=True)

    # eliminar linhas repetidas (mantém a mais recente, se houver diferença de preço)
    df_atualizado = df_atualizado.drop_duplicates(
        subset=["Hora", "Submercado", "Data"],
        keep="last"
    )

    salvar_base_master(df_atualizado)


# (adicione no FINAL do seu data_ingest.py)

# --------------------------------------------------------------
# função-fachada chamada pelo orquestrador
# --------------------------------------------------------------
def update_all():
    """
    Atualiza o parquet de PLD.
    (Se mais tarde você adicionar o CMO aqui, basta chamar
     as funções correspondentes antes de salvar.)
    """
    atualizar_base_master()   # ← a rotina que você já tem
    print("Ingestão PLD concluída.")



# In[ ]:




