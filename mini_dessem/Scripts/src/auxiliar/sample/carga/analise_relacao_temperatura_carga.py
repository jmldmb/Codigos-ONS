"""
ANÁLISE: RELAÇÃO TEMPERATURA x CARGA
=====================================

Objetivo: Testar diferentes modelos para ajuste de temperatura:
1. Linear
2. Quadrático (U-shaped)
3. Por faixas de temperatura
4. Spline

Autor: Modelo V6
Data: 2025-11-05
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from scipy.interpolate import UnivariateSpline
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import warnings
warnings.filterwarnings('ignore')

print("="*100)
print("  ANÁLISE: RELAÇÃO TEMPERATURA x CARGA")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/6] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

print(f"  [OK] {len(df):,} registros com temperatura")

# Calcular temperatura média DIÁRIA para cada hora
df['temp_media_dia'] = df.groupby('data')['temp_brasil_c'].transform('mean')
df['desvio_temp_dia'] = df['temp_brasil_c'] - df['temp_media_dia']

# Remover efeitos de hora e tipo de dia para isolar efeito temperatura
# Normalizar carga por hora e tipo de dia
df_norm = df.groupby(['hora', 'tipo_dia_v2'])['carga_mw'].transform('mean')
df['carga_normalizada'] = df['carga_mw'] - df_norm

print(f"\n  Estatísticas de desvio de temperatura (hora vs média do dia):")
print(f"    Média: {df['desvio_temp_dia'].mean():>8.2f}°C (deveria ser ~0)")
print(f"    Std:   {df['desvio_temp_dia'].std():>8.2f}°C")
print(f"    Min:   {df['desvio_temp_dia'].min():>8.2f}°C")
print(f"    Max:   {df['desvio_temp_dia'].max():>8.2f}°C")

# ============================================================================
# 2. ANÁLISE POR MÊS
# ============================================================================
print("\n[2/6] ANALISANDO CORRELAÇÃO POR MÊS...")

correlacoes_mes = []
for mes in range(1, 13):
    df_mes = df[df['mes'] == mes]
    if len(df_mes) > 100:
        # Correlação temperatura absoluta vs carga
        corr_abs = df_mes[['temp_brasil_c', 'carga_mw']].corr().iloc[0, 1]
        
        # Correlação desvio temperatura (hora vs dia) vs carga normalizada
        corr_desvio = df_mes[['desvio_temp_dia', 'carga_normalizada']].corr().iloc[0, 1]
        
        correlacoes_mes.append({
            'mes': mes,
            'corr_abs': corr_abs,
            'corr_desvio': corr_desvio,
            'n_obs': len(df_mes),
            'temp_media': df_mes['temp_brasil_c'].mean(),
            'temp_std': df_mes['temp_brasil_c'].std()
        })

df_corr = pd.DataFrame(correlacoes_mes)

print(f"\n{'Mês':>4} | {'Temp Média':>11} | {'Corr (Abs)':>11} | {'Corr (Desvio)':>14} | {'N Obs':>8}")
print("-"*70)
for _, row in df_corr.iterrows():
    print(f"{row['mes']:>4} | {row['temp_media']:>9.1f}°C | {row['corr_abs']:>+10.4f} | {row['corr_desvio']:>+13.4f} | {row['n_obs']:>8.0f}")

# ============================================================================
# 3. TESTAR MODELOS DIFERENTES
# ============================================================================
print("\n[3/6] TESTANDO MODELOS DE TEMPERATURA...")

# Preparar dados para modelagem
# Usar apenas horas com desvio significativo
df_model = df[['temp_brasil_c', 'desvio_temp_dia', 'carga_mw', 'carga_normalizada', 
               'mes', 'hora', 'tipo_dia_v2']].copy()

resultados_modelos = []

print("\n  Testando modelos por mês...")

for mes in range(1, 13):
    df_mes = df_model[df_model['mes'] == mes].copy()
    
    if len(df_mes) < 100:
        continue
    
    X_abs = df_mes['temp_brasil_c'].values
    X_desvio = df_mes['desvio_temp_dia'].values
    y = df_mes['carga_normalizada'].values
    
    # Modelo 1: Linear (desvio)
    try:
        slope_1, intercept_1, r_1, p_1, se_1 = stats.linregress(X_desvio, y)
        y_pred_1 = slope_1 * X_desvio + intercept_1
        r2_1 = r2_score(y, y_pred_1)
        mae_1 = mean_absolute_error(y, y_pred_1)
    except:
        r2_1, mae_1, slope_1 = 0, 999999, 0
    
    # Modelo 2: Quadrático (desvio)
    try:
        coef_2 = np.polyfit(X_desvio, y, 2)
        y_pred_2 = np.polyval(coef_2, X_desvio)
        r2_2 = r2_score(y, y_pred_2)
        mae_2 = mean_absolute_error(y, y_pred_2)
    except:
        r2_2, mae_2, coef_2 = 0, 999999, [0, 0, 0]
    
    # Modelo 3: Por faixas (temperatura absoluta)
    try:
        bins = [-np.inf, 15, 20, 25, np.inf]
        labels = ['frio', 'ameno', 'quente', 'muito_quente']
        df_mes['faixa_temp'] = pd.cut(df_mes['temp_brasil_c'], bins=bins, labels=labels)
        
        efeito_faixas = df_mes.groupby('faixa_temp')['carga_normalizada'].mean().to_dict()
        df_mes['y_pred_3'] = df_mes['faixa_temp'].map(efeito_faixas)
        
        y_pred_3 = df_mes['y_pred_3'].values
        r2_3 = r2_score(y, y_pred_3)
        mae_3 = mean_absolute_error(y, y_pred_3)
    except:
        r2_3, mae_3 = 0, 999999
    
    resultados_modelos.append({
        'mes': mes,
        'n_obs': len(df_mes),
        'linear_r2': r2_1,
        'linear_mae': mae_1,
        'linear_coef': slope_1,
        'quad_r2': r2_2,
        'quad_mae': mae_2,
        'quad_coef_a': coef_2[0],
        'quad_coef_b': coef_2[1],
        'faixas_r2': r2_3,
        'faixas_mae': mae_3
    })

df_resultados = pd.DataFrame(resultados_modelos)

print(f"\n{'Mês':>4} | {'N Obs':>8} | {'Linear R²':>11} | {'Quad R²':>9} | {'Faixas R²':>11} | {'Melhor':>10}")
print("-"*75)
for _, row in df_resultados.iterrows():
    melhor = 'Linear' if row['linear_r2'] >= row['quad_r2'] and row['linear_r2'] >= row['faixas_r2'] else \
             'Quad' if row['quad_r2'] >= row['faixas_r2'] else 'Faixas'
    
    print(f"{row['mes']:>4} | {row['n_obs']:>8.0f} | {row['linear_r2']:>10.4f} | "
          f"{row['quad_r2']:>8.4f} | {row['faixas_r2']:>10.4f} | {melhor:>10}")

# Resumo geral
print(f"\n[RESUMO GERAL]")
print(f"  Melhor modelo por mês:")
print(f"    Linear:  {(df_resultados['linear_r2'] >= df_resultados[['quad_r2', 'faixas_r2']].max(axis=1)).sum()} meses")
print(f"    Quadrático: {(df_resultados['quad_r2'] >= df_resultados[['linear_r2', 'faixas_r2']].max(axis=1)).sum()} meses")
print(f"    Faixas:  {(df_resultados['faixas_r2'] >= df_resultados[['linear_r2', 'quad_r2']].max(axis=1)).sum()} meses")

print(f"\n  R² médio:")
print(f"    Linear:     {df_resultados['linear_r2'].mean():.4f}")
print(f"    Quadrático: {df_resultados['quad_r2'].mean():.4f}")
print(f"    Faixas:     {df_resultados['faixas_r2'].mean():.4f}")

# ============================================================================
# 4. ANÁLISE GRÁFICA
# ============================================================================
print("\n[4/6] GERANDO VISUALIZAÇÕES...")

# Figura 1: Scatter temperatura vs carga normalizada (por mês)
fig, axes = plt.subplots(3, 4, figsize=(20, 15))
axes = axes.flatten()

for i, mes in enumerate(range(1, 13)):
    ax = axes[i]
    df_mes = df_model[df_model['mes'] == mes]
    
    if len(df_mes) > 0:
        # Scatter
        ax.scatter(df_mes['desvio_temp_dia'], df_mes['carga_normalizada'], 
                  alpha=0.3, s=5, color='steelblue')
        
        # Linha de tendência linear
        if len(df_mes) > 10:
            z = np.polyfit(df_mes['desvio_temp_dia'], df_mes['carga_normalizada'], 1)
            p = np.poly1d(z)
            x_line = np.linspace(df_mes['desvio_temp_dia'].min(), 
                                df_mes['desvio_temp_dia'].max(), 100)
            ax.plot(x_line, p(x_line), 'r-', linewidth=2, label=f'Linear (R²={df_resultados[df_resultados["mes"]==mes]["linear_r2"].values[0]:.3f})')
            
            # Linha quadrática
            z2 = np.polyfit(df_mes['desvio_temp_dia'], df_mes['carga_normalizada'], 2)
            p2 = np.poly1d(z2)
            ax.plot(x_line, p2(x_line), 'g--', linewidth=2, label=f'Quad (R²={df_resultados[df_resultados["mes"]==mes]["quad_r2"].values[0]:.3f})')
        
        ax.set_title(f'Mês {mes}', fontsize=11, fontweight='bold')
        ax.set_xlabel('Desvio Temp vs Dia (°C)', fontsize=9)
        ax.set_ylabel('Carga Normalizada (MW)', fontsize=9)
        ax.legend(fontsize=8, loc='best')
        ax.grid(True, alpha=0.3)

plt.suptitle('Relação Temperatura x Carga (por mês) - Linear vs Quadrático', 
             fontsize=14, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '13_temperatura_carga_por_mes.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 13_temperatura_carga_por_mes.png")

# Figura 2: Comparação de R² dos modelos
fig, ax = plt.subplots(figsize=(14, 7))
x = np.arange(len(df_resultados))
width = 0.25

ax.bar(x - width, df_resultados['linear_r2'], width, label='Linear', alpha=0.8, color='steelblue')
ax.bar(x, df_resultados['quad_r2'], width, label='Quadrático', alpha=0.8, color='green')
ax.bar(x + width, df_resultados['faixas_r2'], width, label='Por Faixas', alpha=0.8, color='orange')

ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('R² (Coeficiente de Determinação)', fontsize=12, fontweight='bold')
ax.set_title('Comparação de Modelos de Temperatura por Mês', fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(df_resultados['mes'])
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(0, color='black', linewidth=0.8)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '14_comparacao_modelos_temperatura.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 14_comparacao_modelos_temperatura.png")

# Figura 3: Coeficientes lineares por mês
fig, ax = plt.subplots(figsize=(14, 7))
ax.bar(df_resultados['mes'], df_resultados['linear_coef'], color='steelblue', 
       alpha=0.8, edgecolor='black')
ax.axhline(0, color='red', linewidth=2, linestyle='--', alpha=0.7)
ax.set_xlabel('Mês', fontsize=12, fontweight='bold')
ax.set_ylabel('Coeficiente Linear (MW/°C)', fontsize=12, fontweight='bold')
ax.set_title('Sensibilidade da Carga à Temperatura por Mês', fontsize=14, fontweight='bold')
ax.set_xticks(df_resultados['mes'])
ax.grid(True, alpha=0.3, axis='y')

for i, row in df_resultados.iterrows():
    ax.text(row['mes'], row['linear_coef'] + 20, f"{row['linear_coef']:.0f}", 
            ha='center', fontsize=9, fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '15_coeficientes_temperatura_mes.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 15_coeficientes_temperatura_mes.png")

# Figura 4: Análise global (todos os meses juntos)
fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Subplot 1: Temperatura absoluta vs Carga
ax = axes[0]
sample = df.sample(min(10000, len(df)), random_state=42)
scatter = ax.scatter(sample['temp_brasil_c'], sample['carga_mw'], 
                    c=sample['mes'], cmap='tab10', alpha=0.4, s=10)
ax.set_xlabel('Temperatura (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Temperatura Absoluta vs Carga (colorido por mês)', fontsize=13, fontweight='bold')
plt.colorbar(scatter, ax=ax, label='Mês')
ax.grid(True, alpha=0.3)

# Subplot 2: Desvio temperatura vs Carga normalizada
ax = axes[1]
sample = df.sample(min(10000, len(df)), random_state=42)
scatter = ax.scatter(sample['desvio_temp_dia'], sample['carga_normalizada'], 
                    c=sample['mes'], cmap='tab10', alpha=0.4, s=10)

# Fit global
z_global = np.polyfit(df['desvio_temp_dia'], df['carga_normalizada'], 1)
p_global = np.poly1d(z_global)
x_line = np.linspace(df['desvio_temp_dia'].min(), df['desvio_temp_dia'].max(), 100)
ax.plot(x_line, p_global(x_line), 'r-', linewidth=3, label=f'Linear Global (coef={z_global[0]:.1f} MW/°C)')

ax.set_xlabel('Desvio Temperatura vs Dia (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Carga Normalizada (MW)', fontsize=12, fontweight='bold')
ax.set_title('Desvio de Temperatura vs Carga Normalizada', fontsize=13, fontweight='bold')
plt.colorbar(scatter, ax=ax, label='Mês')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '16_analise_global_temperatura.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 16_analise_global_temperatura.png")

# ============================================================================
# 5. ANÁLISE POR FAIXA DE TEMPERATURA
# ============================================================================
print("\n[5/6] ANÁLISE POR FAIXA DE TEMPERATURA...")

# Criar faixas de temperatura absoluta
df['faixa_temp_abs'] = pd.cut(df['temp_brasil_c'], 
                               bins=[-np.inf, 15, 18, 21, 24, 27, np.inf],
                               labels=['<15°C', '15-18°C', '18-21°C', '21-24°C', '24-27°C', '>27°C'])

stats_faixas = df.groupby('faixa_temp_abs').agg({
    'carga_mw': ['mean', 'std', 'count'],
    'temp_brasil_c': 'mean'
}).round(0)

print(f"\n{'Faixa Temp':^12} | {'Carga Média':>12} | {'Std':>10} | {'N Obs':>8} | {'Temp Média':>11}")
print("-"*70)
for faixa in stats_faixas.index:
    row = stats_faixas.loc[faixa]
    print(f"{faixa:^12} | {row[('carga_mw', 'mean')]:>10,.0f} MW | "
          f"{row[('carga_mw', 'std')]:>8,.0f} MW | {row[('carga_mw', 'count')]:>8.0f} | "
          f"{row[('temp_brasil_c', 'mean')]:>9.1f}°C")

# ============================================================================
# 6. RECOMENDAÇÃO FINAL
# ============================================================================
print("\n[6/6] GERANDO RECOMENDAÇÃO...")

# Calcular qual modelo é melhor em média
media_r2_linear = df_resultados['linear_r2'].mean()
media_r2_quad = df_resultados['quad_r2'].mean()
media_r2_faixas = df_resultados['faixas_r2'].mean()

melhor_modelo = 'Linear' if media_r2_linear >= media_r2_quad and media_r2_linear >= media_r2_faixas else \
                'Quadrático' if media_r2_quad >= media_r2_faixas else 'Por Faixas'

print("\n" + "="*100)
print("  RECOMENDACAO FINAL: MODELO DE TEMPERATURA")
print("="*100)

print(f"""
COMPARACAO DE MODELOS (R2 medio):
  - Linear:     {media_r2_linear:.4f}
  - Quadratico: {media_r2_quad:.4f}
  - Por Faixas: {media_r2_faixas:.4f}

COEFICIENTE LINEAR MEDIO: {df_resultados['linear_coef'].mean():.1f} MW/C
  (Para cada 1 C de diferenca da temperatura horaria vs media do dia)

ANALISE POR MES:
  - Meses com melhor ajuste linear: {df_corr['corr_desvio'].abs().nlargest(3).index.tolist()}
  - Meses com pior ajuste: {df_corr['corr_desvio'].abs().nsmallest(3).index.tolist()}

RECOMENDACAO: {"[OK] MODELO " + melhor_modelo.upper()}
""")

if melhor_modelo == 'Linear':
    print("""
IMPLEMENTACAO RECOMENDADA:
  Para cada hora h do dia d no mês m:
  
  temp_media_dia_d = mean(temp_hora_0_a_23)
  desvio_temp_h = temp_hora_h - temp_media_dia_d
  ajuste_temp_h = coef_linear_mes_m * desvio_temp_h
  
  carga_h = carga_mensal_mwmed * fator_tipo_dia * perfil_hora_h * (1 + ajuste_temp_h / carga_base)
  
COEFICIENTES POR MES (MW/C):
""")
    for _, row in df_resultados.iterrows():
        print(f"  Mes {row['mes']:>2}: {row['linear_coef']:>7.1f} MW/C (R2={row['linear_r2']:.4f})")

elif melhor_modelo == 'Quadrático':
    print("""
IMPLEMENTACAO RECOMENDADA:
  ajuste_temp_h = a * (desvio_temp_h)^2 + b * desvio_temp_h
  
COEFICIENTES POR MES:
""")
    for _, row in df_resultados.iterrows():
        print(f"  Mes {row['mes']:>2}: a={row['quad_coef_a']:>8.2f}, b={row['quad_coef_b']:>7.1f} (R2={row['quad_r2']:.4f})")

else:
    print("""
IMPLEMENTACAO RECOMENDADA:
  Usar lookup table por faixa de temperatura
""")

print("\n" + "="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar resultados
df_resultados.to_csv(OUTPUT_DIR / 'analise_modelos_temperatura.csv', index=False)
print(f"\n[OK] Resultados salvos: analise_modelos_temperatura.csv")

