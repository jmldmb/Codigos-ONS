"""
GRID CORRELAÇÃO: TEMPERATURA vs CARGA NORMALIZADA - SÁBADO E DOMINGO
======================================================================

Similar ao gráfico 38, mas separado por tipo de dia
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

print("="*100)
print("  GRID CORRELAÇÃO: SÁBADO E DOMINGO")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# CARREGAR DADOS
# ============================================================================
print("\n[1/3] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Calcular carga normalizada
df['carga_media_mes'] = df.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df['carga_normalizada'] = df['carga_mw'] / df['carga_media_mes']

print(f"  [OK] {len(df):,} horas carregadas")

# Filtrar por tipo de dia
df_du = df[df['tipo_dia_v2'] == 'DU'].copy()
df_sab = df[df['tipo_dia_v2'] == 'SAB'].copy()
df_dom = df[df['tipo_dia_v2'] == 'DOM'].copy()

print(f"  Dias Úteis:  {len(df_du):,} horas")
print(f"  Sábados:     {len(df_sab):,} horas")
print(f"  Domingos:    {len(df_dom):,} horas")

# ============================================================================
# CALCULAR REGRESSÕES PARA TODOS OS TIPOS DE DIA
# ============================================================================
print("\n[2/3] CALCULANDO REGRESSÕES POR MÊS-HORA-TIPO_DIA...")

meses_nomes = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

def calcular_regressoes(df_filtrado, nome):
    """Calcula regressões para um tipo de dia"""
    resultados = []
    
    for mes in range(1, 13):
        for hora in range(24):
            df_subset = df_filtrado[(df_filtrado['mes'] == mes) & (df_filtrado['hora'] == hora)]
            
            if len(df_subset) >= 10:  # Mínimo 10 observações (reduzido para SAB/DOM)
                try:
                    slope, intercept, r_val, p_val, _ = stats.linregress(
                        df_subset['temp_brasil_c'],
                        df_subset['carga_normalizada']
                    )
                    r2 = r_val ** 2
                    
                    resultados.append({
                        'mes': mes,
                        'hora': hora,
                        'intercept': intercept,
                        'slope': slope,
                        'r2': r2,
                        'p_value': p_val,
                        'n_obs': len(df_subset)
                    })
                except:
                    resultados.append({
                        'mes': mes,
                        'hora': hora,
                        'intercept': np.nan,
                        'slope': np.nan,
                        'r2': np.nan,
                        'p_value': np.nan,
                        'n_obs': len(df_subset)
                    })
            else:
                resultados.append({
                    'mes': mes,
                    'hora': hora,
                    'intercept': np.nan,
                    'slope': np.nan,
                    'r2': np.nan,
                    'p_value': np.nan,
                    'n_obs': len(df_subset)
                })
    
    df_result = pd.DataFrame(resultados)
    print(f"  {nome}: {(~df_result['r2'].isna()).sum()} regressões válidas de 288")
    print(f"    R2 médio: {df_result['r2'].mean():.4f}")
    print(f"    Slope médio: {df_result['slope'].mean():.4f}")
    
    return df_result

df_reg_du = calcular_regressoes(df_du, "Dias Úteis")
df_reg_sab = calcular_regressoes(df_sab, "Sábados")
df_reg_dom = calcular_regressoes(df_dom, "Domingos")

# ============================================================================
# GERAR GRÁFICOS
# ============================================================================
print("\n[3/3] GERANDO GRÁFICOS...")

# GRÁFICO 1: Grid Mês-Hora para SÁBADOS
print("\n  [1/4] Gerando grid para SÁBADOS...")

fig = plt.figure(figsize=(30, 40))
gs = fig.add_gridspec(12, 24, hspace=0.5, wspace=0.4)

for mes in range(1, 13):
    for hora in range(24):
        ax = fig.add_subplot(gs[mes-1, hora])
        
        df_subset = df_sab[(df_sab['mes'] == mes) & (df_sab['hora'] == hora)]
        
        if len(df_subset) >= 10:
            # Sample
            sample = df_subset.sample(min(200, len(df_subset)), random_state=42)
            
            # Scatter
            ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], 
                      alpha=0.5, s=3, color='orange', edgecolors='none')
            
            # Regressão
            reg = df_reg_sab[(df_reg_sab['mes'] == mes) & (df_reg_sab['hora'] == hora)].iloc[0]
            r2 = reg['r2']
            
            if not np.isnan(r2) and r2 > 0.01:
                x_line = np.linspace(df_subset['temp_brasil_c'].min(), 
                                    df_subset['temp_brasil_c'].max(), 50)
                y_line = reg['slope'] * x_line + reg['intercept']
                
                # Cor baseada em R²
                if r2 > 0.5:
                    color = 'darkgreen'
                    width = 2
                elif r2 > 0.3:
                    color = 'orange'
                    width = 1.5
                else:
                    color = 'red'
                    width = 1
                
                ax.plot(x_line, y_line, color=color, linewidth=width, alpha=0.8)
            
            # Título simplificado
            if mes == 1:  # Primeira linha - mostrar hora
                ax.set_title(f'{hora}h', fontsize=7, fontweight='bold')
            
            if hora == 0:  # Primeira coluna - mostrar mês
                ax.set_ylabel(meses_nomes[mes], fontsize=8, fontweight='bold')
            
            # Mostrar R² se for alto
            if not np.isnan(r2) and r2 > 0.3:
                ax.text(0.5, 0.95, f'{r2:.2f}', 
                       transform=ax.transAxes, fontsize=6,
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
            
            ax.axhline(1.0, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
            ax.set_ylim([0.7, 1.3])
            ax.tick_params(labelsize=5)
            ax.grid(True, alpha=0.2)
        else:
            ax.text(0.5, 0.5, 'Sem\ndados', 
                   transform=ax.transAxes, fontsize=6, 
                   ha='center', va='center', color='gray')
            ax.set_xticks([])
            ax.set_yticks([])

plt.suptitle('SÁBADOS: Temperatura vs Carga Normalizada por Mês (linhas) e Hora (colunas)\n' + 
             'Verde=R2>0.5, Laranja=R2>0.3, Vermelho=R2<0.3', 
             fontsize=20, fontweight='bold', y=0.998)

plt.savefig(OUTPUT_DIR / '40_grid_sabado_mes_hora_normalizada.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 40_grid_sabado_mes_hora_normalizada.png")
plt.close()

# GRÁFICO 2: Grid Mês-Hora para DOMINGOS
print("  [2/4] Gerando grid para DOMINGOS...")

fig = plt.figure(figsize=(30, 40))
gs = fig.add_gridspec(12, 24, hspace=0.5, wspace=0.4)

for mes in range(1, 13):
    for hora in range(24):
        ax = fig.add_subplot(gs[mes-1, hora])
        
        df_subset = df_dom[(df_dom['mes'] == mes) & (df_dom['hora'] == hora)]
        
        if len(df_subset) >= 10:
            # Sample
            sample = df_subset.sample(min(200, len(df_subset)), random_state=42)
            
            # Scatter
            ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], 
                      alpha=0.5, s=3, color='purple', edgecolors='none')
            
            # Regressão
            reg = df_reg_dom[(df_reg_dom['mes'] == mes) & (df_reg_dom['hora'] == hora)].iloc[0]
            r2 = reg['r2']
            
            if not np.isnan(r2) and r2 > 0.01:
                x_line = np.linspace(df_subset['temp_brasil_c'].min(), 
                                    df_subset['temp_brasil_c'].max(), 50)
                y_line = reg['slope'] * x_line + reg['intercept']
                
                # Cor baseada em R²
                if r2 > 0.5:
                    color = 'darkgreen'
                    width = 2
                elif r2 > 0.3:
                    color = 'orange'
                    width = 1.5
                else:
                    color = 'red'
                    width = 1
                
                ax.plot(x_line, y_line, color=color, linewidth=width, alpha=0.8)
            
            # Título simplificado
            if mes == 1:  # Primeira linha - mostrar hora
                ax.set_title(f'{hora}h', fontsize=7, fontweight='bold')
            
            if hora == 0:  # Primeira coluna - mostrar mês
                ax.set_ylabel(meses_nomes[mes], fontsize=8, fontweight='bold')
            
            # Mostrar R² se for alto
            if not np.isnan(r2) and r2 > 0.3:
                ax.text(0.5, 0.95, f'{r2:.2f}', 
                       transform=ax.transAxes, fontsize=6,
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
            
            ax.axhline(1.0, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
            ax.set_ylim([0.7, 1.3])
            ax.tick_params(labelsize=5)
            ax.grid(True, alpha=0.2)
        else:
            ax.text(0.5, 0.5, 'Sem\ndados', 
                   transform=ax.transAxes, fontsize=6, 
                   ha='center', va='center', color='gray')
            ax.set_xticks([])
            ax.set_yticks([])

plt.suptitle('DOMINGOS: Temperatura vs Carga Normalizada por Mês (linhas) e Hora (colunas)\n' + 
             'Verde=R2>0.5, Laranja=R2>0.3, Vermelho=R2<0.3', 
             fontsize=20, fontweight='bold', y=0.998)

plt.savefig(OUTPUT_DIR / '41_grid_domingo_mes_hora_normalizada.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 41_grid_domingo_mes_hora_normalizada.png")
plt.close()

# GRÁFICO 3: Heatmap comparativo R² (lado a lado)
print("  [3/4] Gerando heatmap comparativo...")

fig, axes = plt.subplots(1, 3, figsize=(24, 10))

# Criar matrizes de R²
r2_matrix_du = df_reg_du.pivot(index='hora', columns='mes', values='r2')
r2_matrix_sab = df_reg_sab.pivot(index='hora', columns='mes', values='r2')
r2_matrix_dom = df_reg_dom.pivot(index='hora', columns='mes', values='r2')

# DU
ax = axes[0]
im = ax.imshow(r2_matrix_du, aspect='auto', cmap='YlOrRd', vmin=0, vmax=0.8)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('DIAS UTEIS', fontsize=14, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='R2')

# SAB
ax = axes[1]
im = ax.imshow(r2_matrix_sab, aspect='auto', cmap='YlOrRd', vmin=0, vmax=0.8)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('SABADOS', fontsize=14, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='R2')

# DOM
ax = axes[2]
im = ax.imshow(r2_matrix_dom, aspect='auto', cmap='YlOrRd', vmin=0, vmax=0.8)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('DOMINGOS', fontsize=14, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='R2')

plt.suptitle('Comparacao R2: Temperatura vs Carga Normalizada por Tipo de Dia', 
            fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '42_comparacao_r2_tipo_dia.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 42_comparacao_r2_tipo_dia.png")
plt.close()

# GRÁFICO 4: Diferença de R² (DU - SAB) e (DU - DOM)
print("  [4/4] Gerando heatmap de diferenças...")

fig, axes = plt.subplots(1, 2, figsize=(18, 10))

# DU - SAB
ax = axes[0]
diff_sab = r2_matrix_du - r2_matrix_sab
im = ax.imshow(diff_sab, aspect='auto', cmap='RdBu_r', vmin=-0.3, vmax=0.3)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('Diferenca R2: DU - SABADO\n(Positivo = DU melhor)', fontsize=13, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='Diferenca R2')

# DU - DOM
ax = axes[1]
diff_dom = r2_matrix_du - r2_matrix_dom
im = ax.imshow(diff_dom, aspect='auto', cmap='RdBu_r', vmin=-0.3, vmax=0.3)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('Diferenca R2: DU - DOMINGO\n(Positivo = DU melhor)', fontsize=13, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='Diferenca R2')

plt.suptitle('Onde a correlacao difere mais por tipo de dia?', 
            fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '43_diferenca_r2_tipo_dia.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 43_diferenca_r2_tipo_dia.png")

# ============================================================================
# SALVAR DADOS
# ============================================================================
print("\n[SALVANDO DADOS]")

df_reg_du['tipo_dia'] = 'DU'
df_reg_sab['tipo_dia'] = 'SAB'
df_reg_dom['tipo_dia'] = 'DOM'

df_all = pd.concat([df_reg_du, df_reg_sab, df_reg_dom], ignore_index=True)
df_all.to_csv(OUTPUT_DIR / 'regressoes_por_tipo_dia.csv', index=False)
print(f"  [OK] Salvo: regressoes_por_tipo_dia.csv ({len(df_all)} linhas)")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO")
print("="*100)

print(f"""
REGRESSÕES CALCULADAS:
  Dias Úteis:  {(~df_reg_du['r2'].isna()).sum()}/288 válidas
  Sábados:     {(~df_reg_sab['r2'].isna()).sum()}/288 válidas
  Domingos:    {(~df_reg_dom['r2'].isna()).sum()}/288 válidas

R2 MÉDIO:
  Dias Úteis:  {df_reg_du['r2'].mean():.4f}
  Sábados:     {df_reg_sab['r2'].mean():.4f}
  Domingos:    {df_reg_dom['r2'].mean():.4f}

SLOPE MÉDIO (sensibilidade à temperatura):
  Dias Úteis:  {df_reg_du['slope'].mean():+.4f} (%/°C)
  Sábados:     {df_reg_sab['slope'].mean():+.4f} (%/°C)
  Domingos:    {df_reg_dom['slope'].mean():+.4f} (%/°C)

GRÁFICOS GERADOS:
  40_grid_sabado_mes_hora_normalizada.png     (Grid detalhado sábados)
  41_grid_domingo_mes_hora_normalizada.png    (Grid detalhado domingos)
  42_comparacao_r2_tipo_dia.png               (Comparação lado a lado)
  43_diferenca_r2_tipo_dia.png                (Onde diferem mais)

LOCALIZAÇÃO: {OUTPUT_DIR}
""")

print("="*100)

