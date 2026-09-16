"""
SCATTER PLOTS: TEMPERATURA vs CARGA NORMALIZADA POR MÊS
=========================================================

Versão em scatter plots (grid) do heatmap 28_heatmap_r2_normalizada.png
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

print("="*100)
print("  SCATTER PLOTS: TEMPERATURA vs CARGA NORMALIZADA (por Mês)")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# CARREGAR DADOS
# ============================================================================
print("\n[1/2] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Filtrar apenas dias úteis
df_du = df[(df['tipo_dia_v2'] == 'DU')].copy()

# Calcular carga normalizada
df_du['carga_media_mes'] = df_du.groupby(['ano', 'mes'])['carga_mw'].transform('mean')
df_du['carga_normalizada'] = df_du['carga_mw'] / df_du['carga_media_mes']

print(f"  [OK] {len(df_du):,} horas de dias úteis")
print(f"  Carga normalizada - Média: {df_du['carga_normalizada'].mean():.4f}")
print(f"  Carga normalizada - Std:   {df_du['carga_normalizada'].std():.4f}")

# ============================================================================
# GERAR SCATTER PLOTS POR MÊS (GRID 3x4)
# ============================================================================
print("\n[2/2] GERANDO SCATTER PLOTS POR MÊS...")

meses_nomes = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}

fig, axes = plt.subplots(3, 4, figsize=(24, 18))
axes = axes.flatten()

for mes in range(1, 13):
    ax = axes[mes - 1]
    df_mes = df_du[df_du['mes'] == mes]
    
    # Sample para não ficar muito pesado
    sample = df_mes.sample(min(3000, len(df_mes)), random_state=42)
    
    # Scatter plot
    ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], 
              alpha=0.4, s=15, color='steelblue', edgecolors='none')
    
    # Linha de regressão
    if len(df_mes) >= 50:
        slope, intercept, r_val, p_val, _ = stats.linregress(
            df_mes['temp_brasil_c'], 
            df_mes['carga_normalizada']
        )
        r2 = r_val ** 2
        
        x_line = np.linspace(df_mes['temp_brasil_c'].min(), df_mes['temp_brasil_c'].max(), 100)
        y_line = slope * x_line + intercept
        ax.plot(x_line, y_line, 'r-', linewidth=3, alpha=0.8)
        
        # Título com estatísticas
        ax.set_title(f'{meses_nomes[mes]} (R2={r2:.3f}, slope={slope:+.4f}/C = {slope*100:+.2f}%/C)', 
                    fontsize=11, fontweight='bold')
        
        # Adicionar texto com estatísticas
        temp_min = df_mes['temp_brasil_c'].min()
        temp_max = df_mes['temp_brasil_c'].max()
        temp_mean = df_mes['temp_brasil_c'].mean()
        
        stats_text = f'N={len(df_mes):,}\nT: {temp_min:.1f}-{temp_max:.1f}C\nMedia: {temp_mean:.1f}C'
        ax.text(0.03, 0.97, stats_text, 
               transform=ax.transAxes, fontsize=8, 
               verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    else:
        ax.set_title(f'{meses_nomes[mes]} (poucos dados)', fontsize=11)
    
    ax.set_xlabel('Temperatura (C)', fontsize=10, fontweight='bold')
    ax.set_ylabel('Carga Normalizada', fontsize=10, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.tick_params(labelsize=9)
    
    # Adicionar linha horizontal em y=1 (carga média)
    ax.axhline(1.0, color='gray', linestyle='--', linewidth=1, alpha=0.5)

plt.suptitle('Temperatura vs Carga Normalizada por Mês (Dias Uteis)\nCarga Normalizada = Carga/Média Mensal', 
             fontsize=18, fontweight='bold', y=0.997)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '37_scatter_normalizada_por_mes.png', dpi=150, bbox_inches='tight')
print(f"\n[OK] Salvo: 37_scatter_normalizada_por_mes.png")

# ============================================================================
# SCATTER PLOTS POR MÊS-HORA (GRID MAIOR: 12x24)
# ============================================================================
print("\n[EXTRA] GERANDO GRID MÊS-HORA (12x24)...")

fig = plt.figure(figsize=(30, 40))
gs = fig.add_gridspec(12, 24, hspace=0.5, wspace=0.4)

for mes in range(1, 13):
    for hora in range(24):
        ax = fig.add_subplot(gs[mes-1, hora])
        
        df_subset = df_du[(df_du['mes'] == mes) & (df_du['hora'] == hora)]
        
        if len(df_subset) >= 30:
            # Sample
            sample = df_subset.sample(min(500, len(df_subset)), random_state=42)
            
            # Scatter
            ax.scatter(sample['temp_brasil_c'], sample['carga_normalizada'], 
                      alpha=0.5, s=3, color='steelblue', edgecolors='none')
            
            # Regressão
            try:
                slope, intercept, r_val, _, _ = stats.linregress(
                    df_subset['temp_brasil_c'], 
                    df_subset['carga_normalizada']
                )
                r2 = r_val ** 2
                
                if r2 > 0.01:  # Só plotar se houver alguma correlação
                    x_line = np.linspace(df_subset['temp_brasil_c'].min(), 
                                        df_subset['temp_brasil_c'].max(), 50)
                    y_line = slope * x_line + intercept
                    
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
                if r2 > 0.4:
                    ax.text(0.5, 0.95, f'{r2:.2f}', 
                           transform=ax.transAxes, fontsize=6,
                           ha='center', va='top',
                           bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
            except:
                pass
            
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

plt.suptitle('Grid Completo: Temperatura vs Carga Normalizada por Mês (linhas) e Hora (colunas)\n' + 
             'Verde=R2>0.5, Laranja=R2>0.3, Vermelho=R2<0.3', 
             fontsize=20, fontweight='bold', y=0.998)

plt.savefig(OUTPUT_DIR / '38_grid_mes_hora_normalizada.png', dpi=150, bbox_inches='tight')
print(f"[OK] Salvo: 38_grid_mes_hora_normalizada.png")

# ============================================================================
# RESUMO ESTATÍSTICO POR MÊS
# ============================================================================
print("\n" + "="*100)
print("  RESUMO ESTATÍSTICO POR MÊS")
print("="*100)

print(f"\n{'Mes':>6} | {'Nome':>4} | {'R2':>7} | {'Corr':>7} | {'Slope':>10} | {'Slope %':>9} | {'N obs':>8}")
print("-"*75)

for mes in range(1, 13):
    df_mes = df_du[df_du['mes'] == mes]
    
    if len(df_mes) >= 50:
        corr = df_mes[['temp_brasil_c', 'carga_normalizada']].corr().iloc[0, 1]
        slope, _, r_val, _, _ = stats.linregress(
            df_mes['temp_brasil_c'], 
            df_mes['carga_normalizada']
        )
        r2 = r_val ** 2
        slope_pct = slope * 100
        
        print(f"{mes:>6.0f} | {meses_nomes[mes]:>4} | {r2:>6.4f} | {corr:>+6.4f} | {slope:>+9.4f} | {slope_pct:>+8.2f}% | {len(df_mes):>8,}")

print("\n" + "="*100)
print(f"Gráficos salvos em: {OUTPUT_DIR}")
print("="*100)





