"""
Funções para cálculo de preços (PLD)
"""

import pandas as pd
from pathlib import Path
from .config import PLD_MINIMO


def carregar_pilha_termica(filepath=None):
    """
    Carrega a pilha térmica de um arquivo Excel.
    
    Parâmetros:
    - filepath (str/Path): Caminho para o arquivo Excel com a pilha térmica.
                          Se None, tenta carregar do caminho padrão.
    
    Retorna:
    - pd.DataFrame: DataFrame com colunas 'potencia' e 'cvu'
    """
    if filepath is None:
        # Caminho padrão
        # __file__ está em: Scripts/src/mini_dessem/pricing.py
        # Precisamos subir 4 níveis para chegar na raiz do projeto (mini_dessem/)
        filepath = Path(__file__).parent.parent.parent.parent / "Data" / "auxiliar" / "CVU_USINA_TERMICA_2025.xlsx"
    
    try:
        pilha_term = pd.read_excel(filepath, sheet_name="pilha_term")
        
        # Verificar se tem as colunas necessárias
        if 'potencia' not in pilha_term.columns or 'cvu' not in pilha_term.columns:
            raise ValueError("DataFrame deve conter colunas 'potencia' e 'cvu'")
        
        # Ordenar por potência
        pilha_term = pilha_term.sort_values('potencia').reset_index(drop=True)
        
        return pilha_term
    
    except FileNotFoundError:
        print(f"[AVISO] Arquivo nao encontrado: {filepath}")
        print("   Criando pilha termica de exemplo...")
        return criar_pilha_termica_exemplo()
    except Exception as e:
        print(f"[AVISO] Erro ao carregar pilha termica: {e}")
        print("   Criando pilha termica de exemplo...")
        return criar_pilha_termica_exemplo()


def criar_pilha_termica_exemplo():
    """
    Cria uma pilha térmica de exemplo (merit order).
    
    Esta é uma função placeholder para quando não há dados reais disponíveis.
    
    Retorna:
    - pd.DataFrame: DataFrame com colunas 'potencia' e 'cvu'
    """
    # Exemplo simplificado de pilha térmica
    data = {
        'potencia': [0, 500, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000, 15000, 20000, 30000],
        'cvu': [61, 150, 250, 350, 450, 550, 650, 750, 900, 1200, 1500, 2000, 3000]
    }
    return pd.DataFrame(data)


def encontrar_cvu_proximo(potencia_input, df):
    """
    Encontra o CVU (Custo Variável Unitário) correspondente ao nível de despacho térmico.
    
    Esta função implementa a curva de merit order das térmicas, retornando
    o preço marginal (PLD) baseado no nível de despacho.
    
    Parâmetros:
    - potencia_input (float): Despacho térmico em MW
    - df (pd.DataFrame): DataFrame com colunas 'potencia' e 'cvu'
    
    Retorna:
    - float: CVU correspondente (R$/MWh), ou PLD_MINIMO se não encontrado
    """
    if potencia_input <= 0:
        return PLD_MINIMO
    
    # Filtrar apenas as potências maiores ou iguais à potência de input
    potencia_maior = df[df['potencia'] >= potencia_input]
    
    # Se houver potências maiores ou iguais, pegar a menor delas
    if not potencia_maior.empty:
        potencia_proxima = potencia_maior['potencia'].min()
    else:
        # Se todas as potências no dataframe forem menores que o input
        # Retornar o CVU máximo (último valor)
        return df['cvu'].max()
    
    # Encontrar o cvu correspondente à potência mais próxima
    cvu_proximo = df.loc[df['potencia'] == potencia_proxima, 'cvu'].values[0]
    
    return cvu_proximo


def calcular_pld(val_term_despacho, valor_fixo, pilha_term):
    """
    Calcula o PLD baseado no despacho térmico.
    
    Parâmetros:
    - val_term_despacho (float): Despacho térmico (MW)
    - valor_fixo (float): Valor fixo de inflexibilidade térmica adicional (MW)
    - pilha_term (pd.DataFrame): DataFrame da pilha térmica com colunas 'potencia' e 'cvu'
    
    Retorna:
    - float: PLD calculado (R$/MWh)
    """
    if val_term_despacho > 200:
        pld = encontrar_cvu_proximo(val_term_despacho + valor_fixo, pilha_term)
    else:
        pld = max(encontrar_cvu_proximo(valor_fixo, pilha_term), PLD_MINIMO)
    
    return pld

