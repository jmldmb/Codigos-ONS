"""
GRID CORRELAÇÃO: TEMPERATURA vs CARGA NORMALIZADA - DU vs FDS
===============================================================

Duas categorias:
- DU: Dias úteis
- FDS: Fim de semana (sábado + domingo + feriados)
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

print("="*100)
print("  GRID CORRELAÇÃO: DIAS ÚTEIS vs FIM DE SEMANA")
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

# Criar categoria FDS (fim de semana = SAB + DOM + FERIADO)
df['tipo_dia_modelo'] = df['tipo_dia_v2'].replace({'SAB': 'FDS', 'DOM': 'FDS', 'FERIADO': 'FDS'})

print(f"  [OK] {len(df):,} horas carregadas")

# Filtrar por tipo de dia
df_du = df[df['tipo_dia_modelo'] == 'DU'].copy()
df_fds = df[df['tipo_dia_modelo'] == 'FDS'].copy()

print(f"  Dias Úteis (DU):     {len(df_du):,} horas")
print(f"  Fim de Semana (FDS): {len(df_fds):,} horas")

# Verificar distribuição por mês
print(f"\n  Distribuição FDS por mês:")
for mes in range(1, 13):
    n_fds = len(df_fds[df_fds['mes'] == mes])
    n_por_hora = n_fds / 24 if n_fds > 0 else 0
    print(f"    Mês {mes:2d}: {n_fds:4d} horas ({n_por_hora:.1f} obs/hora)")

# ============================================================================
# CALCULAR REGRESSÕES PARA DU E FDS
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
            
            if len(df_subset) >= 10:  # Mínimo 10 observações
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
    validas = (~df_result['r2'].isna()).sum()
    print(f"  {nome}: {validas} regressões válidas de 288")
    if validas > 0:
        print(f"    R2 médio: {df_result['r2'].mean():.4f}")
        print(f"    Slope médio: {df_result['slope'].mean():.4f}")
    
    return df_result

df_reg_du = calcular_regressoes(df_du, "Dias Úteis")
df_reg_fds = calcular_regressoes(df_fds, "Fim de Semana")

# ============================================================================
# GERAR GRÁFICOS
# ============================================================================
print("\n[3/3] GERANDO GRÁFICOS...")

# GRÁFICO 1: Grid Mês-Hora para FDS
print("\n  [1/4] Gerando grid para FIM DE SEMANA...")

fig = plt.figure(figsize=(30, 40))
gs = fig.add_gridspec(12, 24, hspace=0.5, wspace=0.4)

for mes in range(1, 13):
    for hora in range(24):
        ax = fig.add_subplot(gs[mes-1, hora])
        
        df_subset = df_fds[(df_fds['mes'] == mes) & (df_fds['hora'] == hora)]
        
        if len(df_subset) >= 10:
            # Sample
            sample = df_subset.sample(min(300, len(df_subset)), random_state=42)
            
            # Scatter
            ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], 
                      alpha=0.5, s=3, color='darkblue', edgecolors='none')
            
            # Regressão
            reg = df_reg_fds[(df_reg_fds['mes'] == mes) & (df_reg_fds['hora'] == hora)].iloc[0]
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
            
            # Mostrar R² e N se for relevante
            if not np.isnan(r2) and r2 > 0.3:
                ax.text(0.5, 0.95, f'{r2:.2f}', 
                       transform=ax.transAxes, fontsize=6,
                       ha='center', va='top',
                       bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
            
            # Mostrar número de observações (pequeno)
            ax.text(0.05, 0.05, f'n={len(df_subset)}', 
                   transform=ax.transAxes, fontsize=5,
                   ha='left', va='bottom', color='gray')
            
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

plt.suptitle('FIM DE SEMANA: Temperatura vs Carga Normalizada por Mês (linhas) e Hora (colunas)\n' + 
             'Verde=R2>0.5, Laranja=R2>0.3, Vermelho=R2<0.3', 
             fontsize=20, fontweight='bold', y=0.998)

plt.savefig(OUTPUT_DIR / '44_grid_fds_mes_hora_normalizada.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 44_grid_fds_mes_hora_normalizada.png")
plt.close()

# GRÁFICO 2: Heatmap comparativo R² (DU vs FDS)
print("  [2/4] Gerando heatmap comparativo DU vs FDS...")

fig, axes = plt.subplots(1, 2, figsize=(18, 10))

# Criar matrizes de R²
r2_matrix_du = df_reg_du.pivot(index='hora', columns='mes', values='r2')
r2_matrix_fds = df_reg_fds.pivot(index='hora', columns='mes', values='r2')

# DU
ax = axes[0]
im = ax.imshow(r2_matrix_du, aspect='auto', cmap='YlOrRd', vmin=0, vmax=0.8)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('DIAS UTEIS (DU)', fontsize=14, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='R2')

# FDS
ax = axes[1]
im = ax.imshow(r2_matrix_fds, aspect='auto', cmap='YlOrRd', vmin=0, vmax=0.8)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('FIM DE SEMANA (FDS)', fontsize=14, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='R2')

plt.suptitle('Comparacao R2: Temperatura vs Carga Normalizada - DU vs FDS', 
            fontsize=16, fontweight='bold', y=0.98)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '45_comparacao_r2_du_vs_fds.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 45_comparacao_r2_du_vs_fds.png")
plt.close()

# GRÁFICO 3: Diferença de R² (DU - FDS)
print("  [3/4] Gerando heatmap de diferenças...")

fig, ax = plt.subplots(figsize=(12, 10))

diff = r2_matrix_du - r2_matrix_fds
im = ax.imshow(diff, aspect='auto', cmap='RdBu_r', vmin=-0.3, vmax=0.3)
ax.set_xlabel('Mes', fontsize=12, fontweight='bold')
ax.set_ylabel('Hora', fontsize=12, fontweight='bold')
ax.set_title('Diferenca R2: DU - FDS\n(Positivo = DU melhor, Negativo = FDS melhor)', 
            fontsize=13, fontweight='bold')
ax.set_xticks(range(12))
ax.set_xticklabels(range(1, 13))
ax.set_yticks(range(24))
plt.colorbar(im, ax=ax, label='Diferenca R2')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '46_diferenca_r2_du_fds.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 46_diferenca_r2_du_fds.png")
plt.close()

# GRÁFICO 4: Scatter comparativo (amostra)
print("  [4/4] Gerando scatter comparativo...")

fig, axes = plt.subplots(2, 6, figsize=(24, 12))
axes = axes.flatten()

for idx, mes in enumerate(range(1, 13)):
    ax = axes[idx]
    
    # Amostra de dados
    df_mes_du = df_du[df_du['mes'] == mes].sample(min(500, len(df_du[df_du['mes'] == mes])), random_state=42)
    df_mes_fds = df_fds[df_fds['mes'] == mes].sample(min(500, len(df_fds[df_fds['mes'] == mes])), random_state=42)
    
    # Scatter
    ax.scatter(df_mes_du['temp_brasil_c'], df_mes_du['carga_normalizada'], 
              alpha=0.3, s=10, color='steelblue', label='DU')
    ax.scatter(df_mes_fds['temp_brasil_c'], df_mes_fds['carga_normalizada'], 
              alpha=0.3, s=10, color='darkblue', label='FDS')
    
    # Título
    r2_du = df_reg_du[df_reg_du['mes'] == mes]['r2'].mean()
    r2_fds = df_reg_fds[df_reg_fds['mes'] == mes]['r2'].mean()
    ax.set_title(f'{meses_nomes[mes]}\nDU R2={r2_du:.3f}, FDS R2={r2_fds:.3f}', 
                fontsize=9, fontweight='bold')
    
    ax.axhline(1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    ax.set_xlabel('Temperatura (C)', fontsize=8)
    ax.set_ylabel('Carga Norm', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=7, loc='best')
    ax.set_ylim([0.7, 1.3])

plt.suptitle('Scatter por Mes: DU (azul claro) vs FDS (azul escuro)', 
            fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '47_scatter_comparativo_du_fds_por_mes.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 47_scatter_comparativo_du_fds_por_mes.png")

# ============================================================================
# SALVAR DADOS
# ============================================================================
print("\n[SALVANDO DADOS]")

df_reg_du['tipo_dia_modelo'] = 'DU'
df_reg_fds['tipo_dia_modelo'] = 'FDS'

df_all = pd.concat([df_reg_du, df_reg_fds], ignore_index=True)
df_all.to_csv(OUTPUT_DIR / 'regressoes_du_fds.csv', index=False)
print(f"  [OK] Salvo: regressoes_du_fds.csv ({len(df_all)} linhas)")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO")
print("="*100)

print(f"""
REGRESSÕES CALCULADAS:
  Dias Úteis (DU):   {(~df_reg_du['r2'].isna()).sum()}/288 válidas
  Fim de Semana (FDS): {(~df_reg_fds['r2'].isna()).sum()}/288 válidas

R2 MÉDIO:
  Dias Úteis (DU):   {df_reg_du['r2'].mean():.4f}
  Fim de Semana (FDS): {df_reg_fds['r2'].mean():.4f}
  Diferença:         {df_reg_fds['r2'].mean() - df_reg_du['r2'].mean():+.4f}

SLOPE MÉDIO (sensibilidade à temperatura):
  Dias Úteis (DU):   {df_reg_du['slope'].mean():+.4f} (%/°C)
  Fim de Semana (FDS): {df_reg_fds['slope'].mean():+.4f} (%/°C)
  Diferença:         {df_reg_fds['slope'].mean() - df_reg_du['slope'].mean():+.4f} (%/°C)

OBSERVAÇÕES POR HORA (média):
  Dias Úteis:   {df_du.groupby(['mes', 'hora']).size().mean():.1f} obs/hora
  Fim de Semana: {df_fds.groupby(['mes', 'hora']).size().mean():.1f} obs/hora

GRÁFICOS GERADOS:
  44_grid_fds_mes_hora_normalizada.png         (Grid detalhado FDS)
  45_comparacao_r2_du_vs_fds.png               (Heatmap comparativo)
  46_diferenca_r2_du_fds.png                   (Diferenças)
  47_scatter_comparativo_du_fds_por_mes.png    (Scatter por mês)

LOCALIZAÇÃO: {OUTPUT_DIR}
""")

print("="*100)





