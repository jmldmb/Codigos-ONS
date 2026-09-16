"""
AJUSTE FINO PARA CORREÇÃO DE VIÉS NOS PICOS - MODELO V6
=========================================================

Estratégia ELEGANTE:
- Ajustar intercepts das regressões nos horários de pico
- Manter slopes (sensibilidade à temperatura) inalterados
- Aplicar correção separada para DU vs FDS
- Reaplicar constraint para garantir soma = 24
"""

import pandas as pd
import numpy as np
from pathlib import Path
import pickle

print("="*100)
print("  AJUSTE FINO V6: CORRECAO DE VIES NOS PICOS")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
PARAMS_DIR = BASE_DIR / "output" / "sample" / "carga_v6"
ANALISE_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR PARÂMETROS ATUAIS
# ============================================================================
print("\n[1/5] CARREGANDO PARAMETROS ATUAIS...")

df_regressoes = pd.read_parquet(PARAMS_DIR / 'regressoes_v6.parquet')
df_perfil_temp = pd.read_parquet(PARAMS_DIR / 'perfil_temperatura_v6.parquet')
df_proporcoes = pd.read_parquet(PARAMS_DIR / 'proporcoes_tipo_dia_v6.parquet')
df_temp_ref = pd.read_parquet(PARAMS_DIR / 'temperatura_referencia_v6.parquet')

print(f"  [OK] {len(df_regressoes)} regressoes carregadas")

# ============================================================================
# 2. CARREGAR ANÁLISE DE VIÉS
# ============================================================================
print("\n[2/5] CARREGANDO ANALISE DE VIES...")

df_vies = pd.read_csv(ANALISE_DIR / 'vies_por_hora_e_tipo_dia.csv')

print(f"  [OK] {len(df_vies)} vieses calculados")

# Exibir viés por hora e tipo de dia
print(f"\n  Vies Medio por (Hora, Tipo):")
print(f"  {'Tipo':>4} | {'Hora':>4} | {'Vies %':>8}")
print("-"*30)

for _, row in df_vies.iterrows():
    print(f"  {row['tipo_dia']:>4} | {int(row['hora']):>4} | {row['erro_pct']:>7.2f}%")

# ============================================================================
# 3. CALCULAR FATORES DE CORREÇÃO
# ============================================================================
print("\n[3/5] CALCULANDO FATORES DE CORRECAO...")

# Criar dicionário de fatores de correção
fatores_correcao = {}

for _, row in df_vies.iterrows():
    tipo_dia = row['tipo_dia']
    hora = int(row['hora'])
    erro_pct = row['erro_pct']
    
    # Fator de correção: se erro_pct = -2%, fator = 1.02 (aumenta 2%)
    #                     se erro_pct = +1%, fator = 0.99 (diminui 1%)
    fator = 1.0 - (erro_pct / 100.0)
    
    fatores_correcao[(tipo_dia, hora)] = fator

print(f"  [OK] {len(fatores_correcao)} fatores calculados")

# Mostrar fatores para horários de pico
horarios_pico = [16, 17, 18, 19, 20, 21]
print(f"\n  Fatores de Correcao para Horarios de PICO:")
print(f"  {'Tipo':>4} | {'Hora':>4} | {'Fator':>8}")
print("-"*30)

for tipo in ['DU', 'FDS']:
    for hora in horarios_pico:
        fator = fatores_correcao.get((tipo, hora), 1.0)
        print(f"  {tipo:>4} | {hora:>4} | {fator:>8.4f}")

# ============================================================================
# 4. APLICAR CORREÇÃO NOS INTERCEPTS
# ============================================================================
print("\n[4/5] APLICANDO CORRECAO NOS INTERCEPTS...")

df_regressoes_ajustado = df_regressoes.copy()

for idx, row in df_regressoes_ajustado.iterrows():
    tipo_dia = row['tipo_dia_modelo']
    hora = int(row['hora'])
    
    fator = fatores_correcao.get((tipo_dia, hora), 1.0)
    
    # Ajustar apenas o intercept, manter o slope
    df_regressoes_ajustado.at[idx, 'intercept'] = row['intercept'] * fator

print(f"  [OK] Intercepts ajustados")

# Comparar antes e depois (para horários de pico)
print(f"\n  Comparacao ANTES vs DEPOIS (Hora 18, DU):")
reg_antes = df_regressoes[(df_regressoes['tipo_dia_modelo']=='DU') & 
                          (df_regressoes['hora']==18) & 
                          (df_regressoes['mes']==7)].iloc[0]
reg_depois = df_regressoes_ajustado[(df_regressoes_ajustado['tipo_dia_modelo']=='DU') & 
                                    (df_regressoes_ajustado['hora']==18) & 
                                    (df_regressoes_ajustado['mes']==7)].iloc[0]

print(f"    Intercept ANTES:  {reg_antes['intercept']:.6f}")
print(f"    Intercept DEPOIS: {reg_depois['intercept']:.6f}")
print(f"    Slope (inalterado): {reg_depois['slope']:.6f}")

# ============================================================================
# 5. REAPLICAR CONSTRAINT
# ============================================================================
print("\n[5/5] REAPLICANDO CONSTRAINT (soma = 24)...")

regressoes_finais = []

for tipo in ['DU', 'FDS']:
    print(f"\n  Ajustando {tipo}:")
    
    for mes in range(1, 13):
        # Obter regressões deste mês e tipo
        df_mes_reg = df_regressoes_ajustado[
            (df_regressoes_ajustado['tipo_dia_modelo'] == tipo) & 
            (df_regressoes_ajustado['mes'] == mes)
        ].copy()
        
        # Temperatura média do mês
        temp_media = df_temp_ref[df_temp_ref['mes'] == mes]['temp_media'].iloc[0]
        
        # Para cada hora, calcular temperatura típica
        temp_hora = []
        for h in range(24):
            desvio = df_perfil_temp[(df_perfil_temp['mes'] == mes) & 
                                    (df_perfil_temp['hora'] == h)]['desvio_hora'].iloc[0]
            temp_hora.append(temp_media + desvio)
        
        # Calcular soma ANTES do constraint
        soma_antes = sum(
            row['intercept'] + row['slope'] * temp_hora[int(row['hora'])]
            for _, row in df_mes_reg.iterrows()
        )
        
        # Calcular ajuste necessário
        soma_slopes_temp = sum(
            row['slope'] * temp_hora[int(row['hora'])] 
            for _, row in df_mes_reg.iterrows()
        )
        
        soma_intercepts_necessaria = 24.0 - soma_slopes_temp
        soma_intercepts_atual = df_mes_reg['intercept'].sum()
        
        if soma_intercepts_atual > 0:
            fator_constraint = soma_intercepts_necessaria / soma_intercepts_atual
        else:
            fator_constraint = 1.0
        
        # Aplicar constraint
        for idx, row in df_mes_reg.iterrows():
            intercept_final = row['intercept'] * fator_constraint
            
            regressoes_finais.append({
                'tipo_dia_modelo': tipo,
                'mes': row['mes'],
                'hora': row['hora'],
                'intercept': intercept_final,
                'slope': row['slope'],
                'r2': row['r2'],
                'n_obs': row['n_obs']
            })
        
        # Verificar soma DEPOIS
        soma_depois = sum(
            reg['intercept'] + reg['slope'] * temp_hora[int(reg['hora'])]
            for reg in regressoes_finais 
            if reg['tipo_dia_modelo'] == tipo and reg['mes'] == mes
        )
        
        print(f"    Mes {mes:2d}: Soma ANTES={soma_antes:6.2f}, DEPOIS={soma_depois:6.2f}, Fator constraint={fator_constraint:.6f}")

df_regressoes_final = pd.DataFrame(regressoes_finais)

print(f"\n  [OK] Constraint reaplicado")

# ============================================================================
# 6. SALVAR PARÂMETROS AJUSTADOS
# ============================================================================
print("\n[6/6] SALVANDO PARAMETROS AJUSTADOS...")

# Backup dos parâmetros originais
df_regressoes.to_parquet(PARAMS_DIR / 'regressoes_v6_BACKUP_antes_ajuste.parquet', index=False)
print(f"  [BACKUP] Salvo: regressoes_v6_BACKUP_antes_ajuste.parquet")

# Salvar novos parâmetros
df_regressoes_final.to_parquet(PARAMS_DIR / 'regressoes_v6.parquet', index=False)
print(f"  [OK] Salvo: regressoes_v6.parquet (AJUSTADO)")

# Atualizar metadata
with open(PARAMS_DIR / 'metadata_v6.pkl', 'rb') as f:
    metadata = pickle.load(f)

metadata['ajuste_vies_picos'] = True
metadata['data_ajuste'] = pd.Timestamp.now().isoformat()
metadata['descricao_ajuste'] = 'Ajuste fino nos intercepts para corrigir vies nos picos (P90+)'

with open(PARAMS_DIR / 'metadata_v6.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print(f"  [OK] Metadata atualizado")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO DO AJUSTE")
print("="*100)

print(f"""
AJUSTE APLICADO:
  - Intercepts ajustados com base no vies medio por (hora, tipo_dia)
  - Slopes mantidos INALTERADOS (preserva sensibilidade a temperatura)
  - Constraint reaplicado (soma = 24 para cada mes/tipo)

BACKUP:
  - Parametros originais salvos em: regressoes_v6_BACKUP_antes_ajuste.parquet

PROXIMOS PASSOS:
  1. Rodar novo backtest: backtest_v6_detalhado_com_constraint.py
  2. Verificar se o vies P90 foi corrigido
  3. Comparar metricas antes vs depois do ajuste

ARQUIVO ATUALIZADO:
  {PARAMS_DIR / 'regressoes_v6.parquet'}
""")

print("="*100)





