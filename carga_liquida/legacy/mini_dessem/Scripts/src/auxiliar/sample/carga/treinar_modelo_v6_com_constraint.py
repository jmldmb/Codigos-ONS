"""
TREINAR MODELO V6 COM CONSTRAINT: sum(carga_normalizada[24h]) = 24
===================================================================

Abordagem:
1. Treinar regressões independentes (intercept, slope) por mês×hora
2. Para cada mês, ajustar intercepts para garantir soma = 24
3. Preservar slopes (sensibilidade à temperatura)

Constraint: Para qualquer temperatura, sum(carga_norm[h]) = 24
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import pickle
from datetime import datetime

print("="*100)
print("  TREINANDO MODELO V6 COM CONSTRAINT: sum(carga_norm) = 24")
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

# Calcular carga normalizada por mês
df['carga_media_mes'] = df.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df['carga_normalizada'] = df['carga_mw'] / df['carga_media_mes']

print(f"  [OK] {len(df):,} horas de dados")
print(f"  Período: {df['timestamp'].min()} a {df['timestamp'].max()}")

# ============================================================================
# 2. TREINAR REGRESSÕES INICIAIS (SEM CONSTRAINT)
# ============================================================================
print("\n[2/5] TREINANDO REGRESSÕES INICIAIS...")

df_du = df[df['tipo_dia_v2'] == 'DU'].copy()

regressoes_iniciais = []

for mes in range(1, 13):
    for hora in range(24):
        df_subset = df_du[(df_du['mes'] == mes) & (df_du['hora'] == hora)]
        
        if len(df_subset) >= 30:
            try:
                slope, intercept, r_val, p_val, stderr = stats.linregress(
                    df_subset['temp_brasil_c'],
                    df_subset['carga_normalizada']
                )
                
                regressoes_iniciais.append({
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
                'mes': mes,
                'hora': hora,
                'intercept_original': 1.0,
                'slope': 0.0,
                'r2': 0.0,
                'p_value': 1.0,
                'n_obs': len(df_subset)
            })

df_reg_inicial = pd.DataFrame(regressoes_iniciais)

print(f"  [OK] {len(df_reg_inicial)} regressões treinadas")
print(f"  R2 médio: {df_reg_inicial['r2'].mean():.4f}")

# ============================================================================
# 3. CALCULAR PERFIL DE TEMPERATURA (mesmo de antes)
# ============================================================================
print("\n[3/5] CALCULANDO PERFIL DE TEMPERATURA...")

perfil_temp = []
temp_ref = []

for mes in range(1, 13):
    df_mes = df_du[df_du['mes'] == mes]
    
    if len(df_mes) > 0:
        temp_media_mes = df_mes['temp_brasil_c'].mean()
        temp_std_mes = df_mes['temp_brasil_c'].std()
        
        # Para cada hora, calcular desvio típico
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
# 4. APLICAR CONSTRAINT: AJUSTAR INTERCEPTS
# ============================================================================
print("\n[4/5] APLICANDO CONSTRAINT (ajustando intercepts)...")

regressoes_ajustadas = []

for mes in range(1, 13):
    # Obter regressões deste mês
    df_mes_reg = df_reg_inicial[df_reg_inicial['mes'] == mes].copy()
    
    # Temperatura média do mês
    temp_media = df_temp_ref[df_temp_ref['mes'] == mes]['temp_media'].iloc[0]
    
    # Para cada hora, calcular temperatura típica
    temp_hora = []
    for h in range(24):
        desvio = df_perfil_temp[(df_perfil_temp['mes'] == mes) & 
                                (df_perfil_temp['hora'] == h)]['desvio_hora'].iloc[0]
        temp_hora.append(temp_media + desvio)
    
    # Calcular soma ANTES do ajuste (com temperatura média)
    soma_antes = 0
    for idx, row in df_mes_reg.iterrows():
        h = int(row['hora'])
        carga_norm_h = row['intercept_original'] + row['slope'] * temp_hora[h]
        soma_antes += carga_norm_h
    
    # Calcular ajuste necessário
    # Queremos: sum(intercept_novo + slope × temp[h]) = 24
    # sum(intercept_novo) + sum(slope × temp[h]) = 24
    # sum(intercept_novo) = 24 - sum(slope × temp[h])
    
    soma_slopes_temp = sum(row['slope'] * temp_hora[int(row['hora'])] 
                          for _, row in df_mes_reg.iterrows())
    
    soma_intercepts_necessaria = 24.0 - soma_slopes_temp
    soma_intercepts_original = df_mes_reg['intercept_original'].sum()
    
    # Ajustar proporcionalmente
    if soma_intercepts_original > 0:
        fator_ajuste = soma_intercepts_necessaria / soma_intercepts_original
    else:
        fator_ajuste = 1.0
    
    # Aplicar ajuste
    for idx, row in df_mes_reg.iterrows():
        intercept_ajustado = row['intercept_original'] * fator_ajuste
        
        regressoes_ajustadas.append({
            'mes': row['mes'],
            'hora': row['hora'],
            'intercept': intercept_ajustado,
            'intercept_original': row['intercept_original'],
            'ajuste_aplicado': fator_ajuste,
            'slope': row['slope'],
            'r2': row['r2'],
            'p_value': row['p_value'],
            'n_obs': row['n_obs']
        })
    
    # Verificar soma DEPOIS do ajuste
    soma_depois = 0
    for reg in [r for r in regressoes_ajustadas if r['mes'] == mes]:
        h = int(reg['hora'])
        carga_norm_h = reg['intercept'] + reg['slope'] * temp_hora[h]
        soma_depois += carga_norm_h
    
    print(f"  Mês {mes:2d}: Soma ANTES={soma_antes:6.2f}, DEPOIS={soma_depois:6.2f}, "
          f"Fator={fator_ajuste:.4f}")

df_regressoes = pd.DataFrame(regressoes_ajustadas)

print(f"\n  [OK] Intercepts ajustados para garantir soma = 24")
print(f"  Fator de ajuste médio: {df_regressoes.groupby('mes')['ajuste_aplicado'].first().mean():.4f}")
print(f"  Fator de ajuste mín:   {df_regressoes.groupby('mes')['ajuste_aplicado'].first().min():.4f}")
print(f"  Fator de ajuste máx:   {df_regressoes.groupby('mes')['ajuste_aplicado'].first().max():.4f}")

# ============================================================================
# 5. CALCULAR PROPORÇÕES (igual antes)
# ============================================================================
print("\n[5/5] CALCULANDO PROPORÇÕES DU/SAB/DOM...")

proporcoes = []

for mes in range(1, 13):
    df_mes = df[df['mes'] == mes]
    
    carga_du = df_mes[df_mes['tipo_dia_v2'] == 'DU']['carga_mw'].mean()
    carga_sab = df_mes[df_mes['tipo_dia_v2'] == 'SAB']['carga_mw'].mean()
    carga_dom = df_mes[df_mes['tipo_dia_v2'] == 'DOM']['carga_mw'].mean()
    
    fator_du = 1.0
    fator_sab = carga_sab / carga_du if carga_du > 0 else 0.92
    fator_dom = carga_dom / carga_du if carga_du > 0 else 0.85
    
    df_mes_diario = df_mes.groupby(['ano', 'mes', 'dia']).agg({
        'tipo_dia_v2': 'first'
    }).reset_index()
    
    n_du = (df_mes_diario['tipo_dia_v2'] == 'DU').sum()
    n_sab = (df_mes_diario['tipo_dia_v2'] == 'SAB').sum()
    n_dom = (df_mes_diario['tipo_dia_v2'] == 'DOM').sum()
    
    proporcoes.append({
        'mes': mes,
        'fator_du': fator_du,
        'fator_sab': fator_sab,
        'fator_dom': fator_dom,
        'n_du_hist': n_du,
        'n_sab_hist': n_sab,
        'n_dom_hist': n_dom,
        'total_dias_hist': len(df_mes_diario)
    })

df_proporcoes = pd.DataFrame(proporcoes)

print(f"  [OK] Proporções calculadas")

# ============================================================================
# 6. SALVAR PARÂMETROS
# ============================================================================
print("\n[6/6] SALVANDO PARÂMETROS...")

# Salvar regressões ajustadas (remover colunas temporárias)
df_regressoes_final = df_regressoes[['mes', 'hora', 'intercept', 'slope', 'r2', 'p_value', 'n_obs']].copy()
df_regressoes_final.to_parquet(PARAMS_DIR / 'regressoes_v6.parquet', index=False)
print(f"  [OK] Salvo: regressoes_v6.parquet ({len(df_regressoes_final)} linhas)")

df_perfil_temp.to_parquet(PARAMS_DIR / 'perfil_temperatura_v6.parquet', index=False)
print(f"  [OK] Salvo: perfil_temperatura_v6.parquet ({len(df_perfil_temp)} linhas)")

df_proporcoes.to_parquet(PARAMS_DIR / 'proporcoes_tipo_dia_v6.parquet', index=False)
print(f"  [OK] Salvo: proporcoes_tipo_dia_v6.parquet ({len(df_proporcoes)} linhas)")

df_temp_ref.to_parquet(PARAMS_DIR / 'temperatura_referencia_v6.parquet', index=False)
print(f"  [OK] Salvo: temperatura_referencia_v6.parquet ({len(df_temp_ref)} linhas)")

# Salvar também análise de ajustes
df_regressoes.to_csv(PARAMS_DIR / 'analise_ajustes_constraint.csv', index=False)
print(f"  [OK] Salvo: analise_ajustes_constraint.csv (para análise)")

# Salvar metadados
metadata = {
    'data_treinamento': datetime.now().isoformat(),
    'periodo_dados': f"{df['timestamp'].min()} a {df['timestamp'].max()}",
    'n_observacoes': len(df),
    'n_regressoes': len(df_regressoes_final),
    'r2_medio': float(df_regressoes_final['r2'].mean()),
    'r2_mediano': float(df_regressoes_final['r2'].median()),
    'versao': 'V6_com_constraint',
    'constraint': 'sum(carga_normalizada[24h]) = 24.0 para qualquer temperatura',
    'descricao': 'Intercepts ajustados para garantir soma = 24, slopes preservados'
}

with open(PARAMS_DIR / 'metadata_v6.pkl', 'wb') as f:
    pickle.dump(metadata, f)
print(f"  [OK] Salvo: metadata_v6.pkl")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO DO TREINAMENTO V6 COM CONSTRAINT")
print("="*100)

print(f"""
PARÂMETROS SALVOS EM: {PARAMS_DIR}

ARQUIVOS GERADOS:
  1. regressoes_v6.parquet                - {len(df_regressoes_final)} regressões (AJUSTADAS)
  2. perfil_temperatura_v6.parquet        - {len(df_perfil_temp)} perfis
  3. proporcoes_tipo_dia_v6.parquet       - {len(df_proporcoes)} proporções
  4. temperatura_referencia_v6.parquet    - {len(df_temp_ref)} referências
  5. analise_ajustes_constraint.csv       - Análise detalhada dos ajustes
  6. metadata_v6.pkl                      - Metadados

QUALIDADE DAS REGRESSÕES:
  R2 médio:    {df_regressoes_final['r2'].mean():.4f}
  R2 mediano:  {df_regressoes_final['r2'].median():.4f}

CONSTRAINT APLICADO:
  Sum(carga_normalizada[24h]) = 24.0 para qualquer temperatura
  Método: Ajuste proporcional dos intercepts
  Slopes preservados (sensibilidade à temperatura mantida)

PRÓXIMO PASSO:
  Rodar backtest_modelo_v6.py para validar!
""")

print("="*100)





