"""
TREINAR MODELO V6 COM REGRESSÕES SEPARADAS: DU vs FDS
=======================================================

Duas categorias:
- DU: Dias úteis
- FDS: Fim de semana (sábado + domingo + feriados)

Com constraint: sum(carga_normalizada[24h]) = 24 para cada tipo
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import pickle
from datetime import datetime

print("="*100)
print("  TREINANDO MODELO V6: DU vs FDS COM CONSTRAINT")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"
PARAMS_DIR = BASE_DIR / "output" / "sample" / "carga_v6"
PARAMS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/5] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Criar categoria FDS
df['tipo_dia_modelo'] = df['tipo_dia_v2'].replace({'SAB': 'FDS', 'DOM': 'FDS', 'FERIADO': 'FDS'})

# Calcular carga normalizada
df['carga_media_mes'] = df.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df['carga_normalizada'] = df['carga_mw'] / df['carga_media_mes']

print(f"  [OK] {len(df):,} horas de dados")
print(f"  Dias Úteis (DU):     {(df['tipo_dia_modelo']=='DU').sum():,} horas")
print(f"  Fim de Semana (FDS): {(df['tipo_dia_modelo']=='FDS').sum():,} horas")

# ============================================================================
# 2. TREINAR REGRESSÕES SEPARADAS POR TIPO DE DIA
# ============================================================================
print("\n[2/5] TREINANDO REGRESSÕES INICIAIS (DU e FDS)...")

regressoes_iniciais = []

for tipo in ['DU', 'FDS']:
    df_tipo = df[df['tipo_dia_modelo'] == tipo].copy()
    
    for mes in range(1, 13):
        for hora in range(24):
            df_subset = df_tipo[(df_tipo['mes'] == mes) & (df_tipo['hora'] == hora)]
            
            if len(df_subset) >= 10:
                try:
                    slope, intercept, r_val, p_val, stderr = stats.linregress(
                        df_subset['temp_brasil_c'],
                        df_subset['carga_normalizada']
                    )
                    
                    regressoes_iniciais.append({
                        'tipo_dia_modelo': tipo,
                        'mes': mes,
                        'hora': hora,
                        'intercept_original': intercept,
                        'slope': slope,
                        'r2': r_val**2,
                        'p_value': p_val,
                        'n_obs': len(df_subset)
                    })
                except:
                    regressoes_iniciais.append({
                        'tipo_dia_modelo': tipo,
                        'mes': mes,
                        'hora': hora,
                        'intercept_original': 1.0,
                        'slope': 0.0,
                        'r2': 0.0,
                        'p_value': 1.0,
                        'n_obs': 0
                    })
            else:
                regressoes_iniciais.append({
                    'tipo_dia_modelo': tipo,
                    'mes': mes,
                    'hora': hora,
                    'intercept_original': 1.0,
                    'slope': 0.0,
                    'r2': 0.0,
                    'p_value': 1.0,
                    'n_obs': len(df_subset)
                })

df_reg_inicial = pd.DataFrame(regressoes_iniciais)

print(f"  [OK] {len(df_reg_inicial)} regressões treinadas (288 DU + 288 FDS)")
print(f"  R2 médio DU:  {df_reg_inicial[df_reg_inicial['tipo_dia_modelo']=='DU']['r2'].mean():.4f}")
print(f"  R2 médio FDS: {df_reg_inicial[df_reg_inicial['tipo_dia_modelo']=='FDS']['r2'].mean():.4f}")

# ============================================================================
# 3. CALCULAR PERFIL DE TEMPERATURA
# ============================================================================
print("\n[3/5] CALCULANDO PERFIL DE TEMPERATURA...")

perfil_temp = []
temp_ref = []

# Usar dados de DU para perfil de temperatura (mais estável)
df_du = df[df['tipo_dia_modelo'] == 'DU'].copy()

for mes in range(1, 13):
    df_mes = df_du[df_du['mes'] == mes]
    
    if len(df_mes) > 0:
        temp_media_mes = df_mes['temp_brasil_c'].mean()
        temp_std_mes = df_mes['temp_brasil_c'].std()
        
        for hora in range(24):
            df_hora = df_mes[df_mes['hora'] == hora]
            
            if len(df_hora) > 0:
                temp_media_hora = df_hora['temp_brasil_c'].mean()
                desvio = temp_media_hora - temp_media_mes
            else:
                desvio = 0.0
            
            perfil_temp.append({
                'mes': mes,
                'hora': hora,
                'temp_media_mes': temp_media_mes,
                'temp_media_hora': temp_media_hora if len(df_hora) > 0 else temp_media_mes,
                'desvio_hora': desvio
            })
        
        temp_ref.append({
            'mes': mes,
            'temp_media': temp_media_mes,
            'temp_std': temp_std_mes,
            'temp_min': df_mes['temp_brasil_c'].min(),
            'temp_max': df_mes['temp_brasil_c'].max()
        })

df_perfil_temp = pd.DataFrame(perfil_temp)
df_temp_ref = pd.DataFrame(temp_ref)

print(f"  [OK] Perfil de temperatura calculado")

# ============================================================================
# 4. APLICAR CONSTRAINT: AJUSTAR INTERCEPTS POR TIPO DE DIA
# ============================================================================
print("\n[4/5] APLICANDO CONSTRAINT (ajustando intercepts)...")

regressoes_ajustadas = []

for tipo in ['DU', 'FDS']:
    print(f"\n  Ajustando {tipo}:")
    
    for mes in range(1, 13):
        # Obter regressões deste mês e tipo
        df_mes_reg = df_reg_inicial[
            (df_reg_inicial['tipo_dia_modelo'] == tipo) & 
            (df_reg_inicial['mes'] == mes)
        ].copy()
        
        # Temperatura média do mês
        temp_media = df_temp_ref[df_temp_ref['mes'] == mes]['temp_media'].iloc[0]
        
        # Para cada hora, calcular temperatura típica
        temp_hora = []
        for h in range(24):
            desvio = df_perfil_temp[(df_perfil_temp['mes'] == mes) & 
                                    (df_perfil_temp['hora'] == h)]['desvio_hora'].iloc[0]
            temp_hora.append(temp_media + desvio)
        
        # Calcular soma ANTES do ajuste
        soma_antes = sum(
            row['intercept_original'] + row['slope'] * temp_hora[int(row['hora'])]
            for _, row in df_mes_reg.iterrows()
        )
        
        # Calcular ajuste necessário
        soma_slopes_temp = sum(
            row['slope'] * temp_hora[int(row['hora'])] 
            for _, row in df_mes_reg.iterrows()
        )
        
        soma_intercepts_necessaria = 24.0 - soma_slopes_temp
        soma_intercepts_original = df_mes_reg['intercept_original'].sum()
        
        if soma_intercepts_original > 0:
            fator_ajuste = soma_intercepts_necessaria / soma_intercepts_original
        else:
            fator_ajuste = 1.0
        
        # Aplicar ajuste
        for idx, row in df_mes_reg.iterrows():
            intercept_ajustado = row['intercept_original'] * fator_ajuste
            
            regressoes_ajustadas.append({
                'tipo_dia_modelo': tipo,
                'mes': row['mes'],
                'hora': row['hora'],
                'intercept': intercept_ajustado,
                'slope': row['slope'],
                'r2': row['r2'],
                'n_obs': row['n_obs']
            })
        
        # Verificar soma DEPOIS
        soma_depois = sum(
            reg['intercept'] + reg['slope'] * temp_hora[int(reg['hora'])]
            for reg in regressoes_ajustadas 
            if reg['tipo_dia_modelo'] == tipo and reg['mes'] == mes
        )
        
        print(f"    Mês {mes:2d}: Soma ANTES={soma_antes:6.2f}, DEPOIS={soma_depois:6.2f}, Fator={fator_ajuste:.4f}")

df_regressoes = pd.DataFrame(regressoes_ajustadas)

print(f"\n  [OK] Intercepts ajustados para garantir soma = 24")

# ============================================================================
# 5. CALCULAR PROPORÇÕES
# ============================================================================
print("\n[5/5] CALCULANDO PROPORÇÕES DU/FDS...")

proporcoes = []

for mes in range(1, 13):
    df_mes = df[df['mes'] == mes]
    
    carga_du = df_mes[df_mes['tipo_dia_modelo'] == 'DU']['carga_mw'].mean()
    carga_fds = df_mes[df_mes['tipo_dia_modelo'] == 'FDS']['carga_mw'].mean()
    
    fator_du = 1.0
    fator_fds = carga_fds / carga_du if carga_du > 0 else 0.88
    
    # Contar dias
    df_mes_diario = df_mes.groupby(['ano', 'mes', 'dia']).agg({
        'tipo_dia_modelo': 'first'
    }).reset_index()
    
    n_du = (df_mes_diario['tipo_dia_modelo'] == 'DU').sum()
    n_fds = (df_mes_diario['tipo_dia_modelo'] == 'FDS').sum()
    
    proporcoes.append({
        'mes': mes,
        'fator_du': fator_du,
        'fator_fds': fator_fds,
        'n_du_hist': n_du,
        'n_fds_hist': n_fds,
        'total_dias_hist': len(df_mes_diario)
    })

df_proporcoes = pd.DataFrame(proporcoes)

print(f"  [OK] Proporções calculadas")
print(f"\n  {'Mês':>4} | {'Fator FDS':>10} | {'Hist DU/FDS':>15}")
print("-"*35)
for _, row in df_proporcoes.iterrows():
    print(f"  {row['mes']:>4.0f} | {row['fator_fds']:>10.3f} | {row['n_du_hist']:>3.0f}/{row['n_fds_hist']:>3.0f}")

# ============================================================================
# 6. SALVAR PARÂMETROS
# ============================================================================
print("\n[6/6] SALVANDO PARÂMETROS...")

df_regressoes.to_parquet(PARAMS_DIR / 'regressoes_v6.parquet', index=False)
print(f"  [OK] Salvo: regressoes_v6.parquet ({len(df_regressoes)} linhas)")

df_perfil_temp.to_parquet(PARAMS_DIR / 'perfil_temperatura_v6.parquet', index=False)
print(f"  [OK] Salvo: perfil_temperatura_v6.parquet")

df_proporcoes.to_parquet(PARAMS_DIR / 'proporcoes_tipo_dia_v6.parquet', index=False)
print(f"  [OK] Salvo: proporcoes_tipo_dia_v6.parquet")

df_temp_ref.to_parquet(PARAMS_DIR / 'temperatura_referencia_v6.parquet', index=False)
print(f"  [OK] Salvo: temperatura_referencia_v6.parquet")

# Metadados
metadata = {
    'data_treinamento': datetime.now().isoformat(),
    'periodo_dados': f"{df['timestamp'].min()} a {df['timestamp'].max()}",
    'n_observacoes': len(df),
    'n_regressoes': len(df_regressoes),
    'versao': 'V6_DU_FDS_constraint',
    'constraint': 'sum(carga_normalizada[24h]) = 24.0 para DU e FDS separadamente',
    'descricao': 'Regressões separadas para DU e FDS com constraint'
}

with open(PARAMS_DIR / 'metadata_v6.pkl', 'wb') as f:
    pickle.dump(metadata, f)
print(f"  [OK] Salvo: metadata_v6.pkl")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO DO TREINAMENTO")
print("="*100)

r2_du = df_regressoes[df_regressoes['tipo_dia_modelo']=='DU']['r2'].mean()
r2_fds = df_regressoes[df_regressoes['tipo_dia_modelo']=='FDS']['r2'].mean()

print(f"""
PARÂMETROS SALVOS EM: {PARAMS_DIR}

REGRESSÕES:
  Total:  {len(df_regressoes)} (288 DU + 288 FDS)
  R2 médio DU:  {r2_du:.4f}
  R2 médio FDS: {r2_fds:.4f}

CONSTRAINT APLICADO:
  Sum(carga_normalizada[24h]) = 24.0 para DU e FDS separadamente
  
PRÓXIMO PASSO:
  Atualizar carga_model_v6.py e fazer backtest!
""")

print("="*100)





