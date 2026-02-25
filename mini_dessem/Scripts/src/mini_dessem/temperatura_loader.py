"""
CARREGADOR DE TEMPERATURA PARA SIMULAÇÕES
==========================================

Fornece temperatura média mensal:
- Valores REAIS quando disponíveis (dados históricos 2023-2025)
- Climatologia como fallback (projeções futuras ou dados faltantes)
"""

import pandas as pd
from pathlib import Path

# Cache global
_TEMP_DATA = None
_TEMP_MENSAL_REAL = None

def carregar_temperatura():
    """Carrega dados de temperatura uma única vez (cache)"""
    global _TEMP_DATA
    
    if _TEMP_DATA is not None:
        return _TEMP_DATA
    
    try:
        # Buscar arquivo de temperatura
        base_dir = Path(__file__).parent.parent.parent.parent
        temp_file = base_dir / "Data" / "temperatura" / "temperatura_processada.parquet"
        
        if temp_file.exists():
            df = pd.read_parquet(temp_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            _TEMP_DATA = df
            print(f"[TEMP] Dados de temperatura carregados: {len(df):,} registros")
            return df
        else:
            print(f"[TEMP] Arquivo não encontrado: {temp_file}")
            return None
            
    except Exception as e:
        print(f"[TEMP] Erro ao carregar temperatura: {e}")
        return None


def obter_temperaturas_dia(ano: int, mes: int, dia: int) -> dict:
    """
    Obtém temperaturas horárias para um dia específico.
    
    Retorna:
    - Se dados disponíveis: dicionário {hora: temperatura_real}
    - Se não disponível: None (usa inferência do modelo)
    
    Args:
        ano: Ano
        mes: Mês (1-12)
        dia: Dia do mês
    
    Returns:
        Dict {hora: temp_C} ou None
    """
    df_temp = carregar_temperatura()
    
    if df_temp is None or df_temp.empty:
        return None
    
    try:
        from datetime import datetime
        
        # Filtrar temperaturas do dia específico
        data_inicio = datetime(ano, mes, dia, 0, 0, 0)
        data_fim = datetime(ano, mes, dia, 23, 59, 59)
        
        df_dia = df_temp[
            (df_temp['timestamp'] >= data_inicio) & 
            (df_temp['timestamp'] <= data_fim)
        ].copy()
        
        if len(df_dia) < 12:  # Menos de metade do dia
            return None
        
        # Extrair hora e temperatura
        df_dia['hora'] = df_dia['timestamp'].dt.hour
        
        # Agrupar por hora (média se houver múltiplos registros)
        temp_por_hora = df_dia.groupby('hora')['temp_brasil_c'].mean().to_dict()
        
        # Interpolar horas faltantes se necessário
        if len(temp_por_hora) < 24:
            import numpy as np
            horas_disponiveis = sorted(temp_por_hora.keys())
            temps_disponiveis = [temp_por_hora[h] for h in horas_disponiveis]
            
            # Interpolar linearmente
            temp_completa = {}
            for h in range(24):
                if h in temp_por_hora:
                    temp_completa[h] = temp_por_hora[h]
                else:
                    # Interpolar
                    temp_completa[h] = np.interp(h, horas_disponiveis, temps_disponiveis)
            
            return temp_completa
        
        return temp_por_hora
        
    except Exception as e:
        return None


def obter_temperatura_mensal(ano: int, mes: int) -> float:
    """
    Obtém temperatura média mensal.
    
    Estratégia:
    1. Tenta usar temperatura REAL do ano/mês específico (se disponível)
    2. Se não disponível, usa CLIMATOLOGIA (média histórica do mês)
    
    Args:
        ano: Ano da simulação
        mes: Mês (1-12)
    
    Returns:
        Temperatura média mensal (°C)
    """
    # Climatologia (fallback)
    temp_climatologia = {
        1: 23.4, 2: 23.8, 3: 23.2, 4: 22.0, 5: 20.5, 6: 19.2,
        7: 19.0, 8: 20.5, 9: 22.0, 10: 23.0, 11: 23.5, 12: 23.6
    }
    
    # Carregar dados de temperatura
    df_temp = carregar_temperatura()
    
    if df_temp is None or df_temp.empty:
        # Sem dados - usar climatologia
        return temp_climatologia.get(mes, 22.0)
    
    # Tentar obter temperatura real do ano/mês específico
    try:
        df_mes = df_temp[
            (df_temp['timestamp'].dt.year == ano) & 
            (df_temp['timestamp'].dt.month == mes)
        ]
        
        if len(df_mes) >= 24 * 7:  # Pelo menos 1 semana de dados
            temp_real = df_mes['temp_brasil_c'].mean()
            return temp_real
        else:
            # Poucos dados para este mês específico - usar climatologia
            # Mas calcular climatologia dos dados reais se possível
            df_mes_todos_anos = df_temp[df_temp['timestamp'].dt.month == mes]
            
            if len(df_mes_todos_anos) >= 24 * 30:  # Pelo menos 1 mês de dados
                temp_climatologica_real = df_mes_todos_anos['temp_brasil_c'].mean()
                return temp_climatologica_real
            else:
                # Usar climatologia hardcoded
                return temp_climatologia.get(mes, 22.0)
    
    except Exception as e:
        # Erro - usar climatologia
        return temp_climatologia.get(mes, 22.0)


def obter_todas_temperaturas_mensais():
    """
    Pré-calcula temperaturas mensais para todos os anos/meses disponíveis.
    
    Retorna um dicionário: {(ano, mes): temperatura}
    """
    global _TEMP_MENSAL_REAL
    
    if _TEMP_MENSAL_REAL is not None:
        return _TEMP_MENSAL_REAL
    
    df_temp = carregar_temperatura()
    
    if df_temp is None or df_temp.empty:
        return {}
    
    # Calcular temperatura média por ano/mês
    df_temp['ano'] = df_temp['timestamp'].dt.year
    df_temp['mes'] = df_temp['timestamp'].dt.month
    
    temp_mensal = df_temp.groupby(['ano', 'mes'])['temp_brasil_c'].mean().to_dict()
    
    _TEMP_MENSAL_REAL = temp_mensal
    
    print(f"[TEMP] Pré-calculadas {len(temp_mensal)} temperaturas mensais")
    print(f"[TEMP] Anos disponíveis: {sorted(set(k[0] for k in temp_mensal.keys()))}")
    
    return temp_mensal


# Climatologia para referência rápida
CLIMATOLOGIA = {
    1: 23.4, 2: 23.8, 3: 23.2, 4: 22.0, 5: 20.5, 6: 19.2,
    7: 19.0, 8: 20.5, 9: 22.0, 10: 23.0, 11: 23.5, 12: 23.6
}

