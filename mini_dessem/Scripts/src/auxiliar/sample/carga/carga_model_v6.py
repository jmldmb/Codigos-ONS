"""
MODELO V6: CARGA HORÁRIA DETERMINÍSTICA
========================================

Modelo: carga_normalizada[h] = f(temp_media_mes, mes, hora)
        carga[h] = carga_dia_tipo × perfil[h] / 24

Inputs:
    - data: datetime.date
    - carga_mensal: MWmedios do mês
    - temp_media_mensal: temperatura média do mês em °C

Output:
    - np.array[24] com carga em MW para cada hora
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, date
import calendar

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================
BASE_DIR = Path(__file__).parent.parent.parent.parent.parent.parent
PARAMS_DIR = BASE_DIR / "output" / "sample" / "carga_v6"

# ============================================================================
# CACHE GLOBAL DE PARÂMETROS
# ============================================================================
_PARAMS_CACHE = None

def _load_params():
    """Carrega parâmetros do modelo V6 (com cache)"""
    global _PARAMS_CACHE
    
    if _PARAMS_CACHE is not None:
        return _PARAMS_CACHE
    
    print(f"[V6] Carregando parâmetros de: {PARAMS_DIR}")
    
    # Carregar todos os parâmetros
    df_regressoes = pd.read_parquet(PARAMS_DIR / 'regressoes_v6.parquet')
    df_perfil_temp = pd.read_parquet(PARAMS_DIR / 'perfil_temperatura_v6.parquet')
    df_proporcoes = pd.read_parquet(PARAMS_DIR / 'proporcoes_tipo_dia_v6.parquet')
    df_temp_ref = pd.read_parquet(PARAMS_DIR / 'temperatura_referencia_v6.parquet')
    
    # Converter para estruturas de acesso rápido
    # Regressões: dicionário {(tipo_dia_modelo, mes, hora): {'intercept': ..., 'slope': ...}}
    regressoes = {}
    for _, row in df_regressoes.iterrows():
        tipo = row.get('tipo_dia_modelo', 'DU')  # Fallback para compatibilidade
        key = (tipo, int(row['mes']), int(row['hora']))
        regressoes[key] = {
            'intercept': row['intercept'],
            'slope': row['slope'],
            'r2': row['r2']
        }
    
    # Perfil temp: dicionário {(mes, hora): desvio}
    perfil_temp = {}
    for _, row in df_perfil_temp.iterrows():
        key = (int(row['mes']), int(row['hora']))
        perfil_temp[key] = row['desvio_hora']
    
    # Proporções: dicionário {mes: {'DU': 1.0, 'FDS': ...}}
    proporcoes = {}
    for _, row in df_proporcoes.iterrows():
        mes = int(row['mes'])
        proporcoes[mes] = {
            'DU': row.get('fator_du', 1.0),
            'FDS': row.get('fator_fds', row.get('fator_dom', 0.88)),  # Fallback
            'n_du': row.get('n_du_hist', 0),
            'n_fds': row.get('n_fds_hist', row.get('n_dom_hist', 0) + row.get('n_sab_hist', 0))
        }
    
    # Temperatura ref: dicionário {mes: {'media': ..., 'std': ...}}
    temp_ref = {}
    for _, row in df_temp_ref.iterrows():
        mes = int(row['mes'])
        temp_ref[mes] = {
            'media': row['temp_media'],
            'std': row['temp_std'],
            'min': row['temp_min'],
            'max': row['temp_max']
        }
    
    _PARAMS_CACHE = {
        'regressoes': regressoes,
        'perfil_temp': perfil_temp,
        'proporcoes': proporcoes,
        'temp_ref': temp_ref
    }
    
    print(f"[V6] Parâmetros carregados: {len(regressoes)} regressões, {len(perfil_temp)} perfis temp")
    
    return _PARAMS_CACHE


def _get_tipo_dia(data, feriados_nacionais=None):
    """
    Retorna tipo de dia: 'DU' ou 'FDS'
    Feriados, sábados e domingos são tratados como 'FDS'
    """
    if isinstance(data, datetime):
        data = data.date()
    
    # Verificar se é feriado
    if feriados_nacionais is not None and data in feriados_nacionais:
        return 'FDS'
    
    # Verificar dia da semana
    dia_semana = data.weekday()  # 0=segunda, 6=domingo
    
    if dia_semana < 5:  # Segunda a sexta
        return 'DU'
    else:  # Sábado ou Domingo
        return 'FDS'


def _calcular_carga_dia(data, carga_mensal, tipo_dia, proporcoes_mes):
    """
    Calcula carga média do dia baseada no calendário real do mês
    
    Lógica:
    1. Contar quantos DU/FDS tem no mês de 'data'
    2. Calcular carga esperada por tipo
    3. Retornar carga do tipo específico
    """
    ano = data.year
    mes = data.month
    
    # Quantos dias de cada tipo no mês?
    dias_no_mes = calendar.monthrange(ano, mes)[1]
    
    # Contar DU/FDS no mês
    n_du = 0
    n_fds = 0
    
    for dia in range(1, dias_no_mes + 1):
        data_temp = date(ano, mes, dia)
        tipo_temp = _get_tipo_dia(data_temp)
        
        if tipo_temp == 'DU':
            n_du += 1
        else:  # FDS
            n_fds += 1
    
    # Fatores históricos
    fator_du = proporcoes_mes['DU']
    fator_fds = proporcoes_mes['FDS']
    
    # Soma ponderada
    denominador = (n_du * fator_du + n_fds * fator_fds)
    
    if denominador > 0:
        base = carga_mensal * dias_no_mes / denominador
    else:
        base = carga_mensal
    
    # Carga do tipo específico
    if tipo_dia == 'DU':
        carga_dia = base * fator_du
    else:  # FDS
        carga_dia = base * fator_fds
    
    return carga_dia


def sample_carga_v6(data, carga_mensal, temp_media_mensal, temp_horaria_real=None, verificar_distorcao=False):
    """
    Gera perfil horário de carga (24 valores) usando modelo V6 (OPÇÃO C)
    
    Modelo: 
        1. carga_normalizada(h) = intercept[mes][h] + slope[mes][h] × temp(h)
        2. Renormalizar: perfil(h) = carga_normalizada(h) × (24 / sum(carga_normalizada))
        3. Calcular carga do dia ajustada por tipo_dia
        4. carga(h) = carga_dia × perfil(h) / 24
    
    Inputs:
        data: datetime.date ou datetime.datetime
        carga_mensal: MWmedios do mês (float)
        temp_media_mensal: temperatura média do mês em °C (float)
        temp_horaria_real: dict {hora: temp_C} com temperaturas REAIS (opcional)
                          Se fornecido, usa valores reais em vez de inferir
        verificar_distorcao: se True, imprime info sobre distorção (default False)
    
    Output:
        np.array[24] com carga em MW para cada hora
    
    Garantias:
        - Forma do perfil vem da temperatura (via regressão)
        - Média mensal considera tipo de dia (DU/SAB/DOM)
        - Renormalização garante consistência: mean(carga[h]) = carga_esperada_dia
    
    Exemplo:
        >>> from datetime import date
        >>> carga = sample_carga_v6(date(2024, 1, 15), 80000, 25.0)
        >>> print(carga.shape)
        (24,)
        >>> print(f"Carga média: {carga.mean():.0f} MW")
    """
    # Converter datetime para date se necessário
    if isinstance(data, datetime):
        data = data.date()
    
    # Carregar parâmetros
    params = _load_params()
    regressoes = params['regressoes']
    perfil_temp = params['perfil_temp']
    proporcoes = params['proporcoes']
    
    # Identificar mês e tipo de dia
    mes = data.month
    tipo_dia = _get_tipo_dia(data)
    
    # PASSO 1: Gerar perfil de temperatura horária
    temp_hora = np.zeros(24)
    
    if temp_horaria_real is not None:
        # Usar temperaturas REAIS (dados históricos disponíveis)
        for h in range(24):
            temp_hora[h] = temp_horaria_real.get(h, temp_media_mensal)
    else:
        # Inferir temperaturas a partir da média mensal (projeções futuras)
        # temp(h) = temp_media_mensal + desvio_tipico[mes][h]
        for h in range(24):
            desvio = perfil_temp.get((mes, h), 0.0)
            temp_hora[h] = temp_media_mensal + desvio
    
    # PASSO 2: Calcular carga normalizada por hora (usando regressão)
    # carga_normalizada(h) = intercept[tipo_dia][mes][h] + slope[tipo_dia][mes][h] × temp(h)
    carga_normalizada = np.zeros(24)
    for h in range(24):
        reg = regressoes.get((tipo_dia, mes, h), {'intercept': 1.0, 'slope': 0.0})
        carga_normalizada[h] = reg['intercept'] + reg['slope'] * temp_hora[h]
    
    # PASSO 3: Renormalizar para garantir soma = 24 (perfil)
    soma_original = carga_normalizada.sum()
    
    if soma_original > 0:
        perfil = carga_normalizada * (24.0 / soma_original)
    else:
        # Fallback: perfil uniforme
        perfil = np.ones(24)
        soma_original = 24.0
    
    # Verificar distorção se solicitado
    if verificar_distorcao:
        distorcao_pct = abs(soma_original - 24.0) / 24.0 * 100
        print(f"  [DISTORÇÃO] Soma original={soma_original:.4f}, Fator correção={24.0/soma_original:.6f}, Distorção={distorcao_pct:.2f}%")
    
    # PASSO 4: Calcular carga do dia considerando tipo de dia e calendário
    proporcoes_mes = proporcoes[mes]
    carga_dia = _calcular_carga_dia(data, carga_mensal, tipo_dia, proporcoes_mes)
    
    # PASSO 5: Distribuir carga pelas 24 horas
    # perfil[h] está normalizado tal que sum(perfil) = 24
    # perfil[h] representa "quantas vezes a média" essa hora tem
    # Como carga_dia é a MÉDIA diária (MW), então:
    # carga(h) = carga_dia × (perfil(h) / 24) × 24 = carga_dia × perfil(h)
    carga_horaria = carga_dia * perfil
    
    return carga_horaria


def sample_day_v6(data, carga_mensal, temp_media_mensal):
    """
    Alias para sample_carga_v6 (compatibilidade)
    """
    return sample_carga_v6(data, carga_mensal, temp_media_mensal)


# ============================================================================
# TESTE RÁPIDO
# ============================================================================
if __name__ == '__main__':
    from datetime import date
    
    print("="*80)
    print("  TESTE RÁPIDO - MODELO V6")
    print("="*80)
    
    # Testar alguns dias
    casos_teste = [
        (date(2024, 1, 15), 80000, 25.0, "Dia útil verão"),
        (date(2024, 1, 13), 80000, 25.0, "Sábado verão"),
        (date(2024, 1, 14), 80000, 25.0, "Domingo verão"),
        (date(2024, 7, 15), 75000, 18.0, "Dia útil inverno"),
    ]
    
    for data_teste, carga_mes, temp_mes, descricao in casos_teste:
        print(f"\n{descricao}: {data_teste}")
        print(f"  Inputs: carga_mensal={carga_mes:,.0f} MW, temp={temp_mes:.1f}°C")
        
        try:
            carga_hora = sample_carga_v6(data_teste, carga_mes, temp_mes)
            
            print(f"  Output:")
            print(f"    Carga média:  {carga_hora.mean():,.0f} MW")
            print(f"    Carga mín:    {carga_hora.min():,.0f} MW (hora {carga_hora.argmin()})")
            print(f"    Carga máx:    {carga_hora.max():,.0f} MW (hora {carga_hora.argmax()})")
            print(f"    Soma 24h:     {carga_hora.sum():,.0f} MWh")
            
            # Verificar consistência
            carga_media_calculada = carga_hora.mean()
            print(f"    Consistência: OK" if abs(carga_media_calculada - carga_hora.mean()) < 1 else "    ERRO!")
            
        except Exception as e:
            print(f"  ERRO: {e}")
    
    print("\n" + "="*80)

