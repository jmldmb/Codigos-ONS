"""
COMPARAÇÃO: DIAS QUENTES vs FRIOS (mesmo mês, mesmo tipo de dia)
===================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

print("="*100)
print("  COMPARAÇÃO: DIAS ÚTEIS QUENTES vs FRIOS (MESMO MÊS)")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS
# ============================================================================
print("\n[1/3] CARREGANDO DADOS...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet")
df = df[df['temp_brasil_c'].notna()].copy()

# Filtrar apenas dias úteis (sem feriados)
df_du = df[(df['tipo_dia_v2'] == 'DU')].copy()

print(f"  [OK] {len(df_du):,} horas de dias úteis")

# ============================================================================
# 2. IDENTIFICAR DIAS EXTREMOS POR MÊS
# ============================================================================
print("\n[2/3] IDENTIFICANDO DIAS EXTREMOS...")

# Calcular temperatura média diária
df_du['temp_media_dia'] = df_du.groupby('data')['temp_brasil_c'].transform('mean')

# Para cada mês/ano, pegar os dias com temp média mais alta e mais baixa
comparacoes = []

for ano in df_du['ano'].unique():
    for mes in range(1, 13):
        df_mes = df_du[(df_du['ano'] == ano) & (df_du['mes'] == mes)].copy()
        
        if len(df_mes) < 48:  # Pelo menos 2 dias completos
            continue
        
        # Agrupar por dia
        df_dias = df_mes.groupby('data').agg({
            'temp_media_dia': 'first',
            'carga_mw': 'mean',
            'temp_brasil_c': ['mean', 'min', 'max']
        }).reset_index()
        
        df_dias.columns = ['data', 'temp_media', 'carga_media', 'temp_mean', 'temp_min', 'temp_max']
        
        if len(df_dias) < 5:  # Precisa ter pelo menos 5 dias
            continue
        
        # Dia mais quente e mais frio
        dia_quente = df_dias.nlargest(1, 'temp_media').iloc[0]
        dia_frio = df_dias.nsmallest(1, 'temp_media').iloc[0]
        
        diff_temp = dia_quente['temp_media'] - dia_frio['temp_media']
        
        if diff_temp < 5:  # Diferença mínima de 5°C
            continue
        
        diff_carga = dia_quente['carga_media'] - dia_frio['carga_media']
        diff_carga_pct = (diff_carga / dia_frio['carga_media']) * 100
        
        comparacoes.append({
            'ano': ano,
            'mes': mes,
            'data_quente': dia_quente['data'],
            'temp_quente': dia_quente['temp_media'],
            'carga_quente': dia_quente['carga_media'],
            'data_frio': dia_frio['data'],
            'temp_frio': dia_frio['temp_media'],
            'carga_frio': dia_frio['carga_media'],
            'diff_temp': diff_temp,
            'diff_carga': diff_carga,
            'diff_carga_pct': diff_carga_pct
        })

df_comp = pd.DataFrame(comparacoes)
df_comp = df_comp.sort_values('diff_temp', ascending=False)

print(f"\n  [INFO] Encontrados {len(df_comp)} pares de dias para comparação")

# Mostrar top 10 maiores diferenças de temperatura
print(f"\n{'Ano':>5} | {'Mes':>4} | {'Data Quente':^12} | {'Temp':>7} | {'Carga':>10} | {'Data Frio':^12} | {'Temp':>7} | {'Carga':>10} | {'Delta T':>8} | {'Delta Carga':>12}")
print("-"*140)

for _, row in df_comp.head(10).iterrows():
    print(f"{row['ano']:>5.0f} | {row['mes']:>4.0f} | {str(row['data_quente']):^12} | {row['temp_quente']:>6.1f}C | "
          f"{row['carga_quente']:>8,.0f} MW | {str(row['data_frio']):^12} | {row['temp_frio']:>6.1f}C | "
          f"{row['carga_frio']:>8,.0f} MW | {row['diff_temp']:>+7.1f}C | {row['diff_carga']:>+10,.0f} MW ({row['diff_carga_pct']:+.1f}%)")

# ============================================================================
# 3. ANÁLISE DETALHADA DE EXEMPLOS
# ============================================================================
print("\n[3/3] ANÁLISE DETALHADA DE EXEMPLOS...")

# Pegar os 3 casos mais extremos
casos_analise = df_comp.head(3)

fig, axes = plt.subplots(len(casos_analise), 1, figsize=(18, 6*len(casos_analise)))

if len(casos_analise) == 1:
    axes = [axes]

for idx, (_, caso) in enumerate(casos_analise.iterrows()):
    ax = axes[idx]
    
    # Buscar perfis horários
    perfil_quente = df_du[df_du['data'] == caso['data_quente']].sort_values('hora')[['hora', 'carga_mw', 'temp_brasil_c']]
    perfil_frio = df_du[df_du['data'] == caso['data_frio']].sort_values('hora')[['hora', 'carga_mw', 'temp_brasil_c']]
    
    # Plot carga
    ax2 = ax.twinx()
    
    line1 = ax.plot(perfil_quente['hora'], perfil_quente['carga_mw'], 
                    'o-', linewidth=3, markersize=8, color='red', 
                    label=f"Quente ({caso['data_quente']}, {caso['temp_quente']:.1f}C)", alpha=0.8)
    
    line2 = ax.plot(perfil_frio['hora'], perfil_frio['carga_mw'], 
                    's-', linewidth=3, markersize=8, color='blue', 
                    label=f"Frio ({caso['data_frio']}, {caso['temp_frio']:.1f}C)", alpha=0.8)
    
    # Plot temperatura no eixo direito
    line3 = ax2.plot(perfil_quente['hora'], perfil_quente['temp_brasil_c'], 
                     '--', linewidth=2, color='darkred', 
                     label=f"Temp Dia Quente", alpha=0.6)
    
    line4 = ax2.plot(perfil_frio['hora'], perfil_frio['temp_brasil_c'], 
                     '--', linewidth=2, color='darkblue', 
                     label=f"Temp Dia Frio", alpha=0.6)
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold', color='black')
    ax2.set_ylabel('Temperatura (C)', fontsize=12, fontweight='bold', color='gray')
    
    ax.set_title(f"Mes {caso['mes']}/{caso['ano']:.0f} - Delta Temp: {caso['diff_temp']:+.1f}C | Delta Carga: {caso['diff_carga']:+.0f} MW ({caso['diff_carga_pct']:+.1f}%)", 
                fontsize=14, fontweight='bold', pad=15)
    
    ax.set_xticks(range(0, 24))
    ax.grid(True, alpha=0.3)
    
    # Combinar legendas
    lines = line1 + line2 + line3 + line4
    labels = [l.get_label() for l in lines]
    ax.legend(lines, labels, fontsize=10, loc='upper left')
    
    # Adicionar texto com estatísticas
    textstr = f"Carga Media Quente: {caso['carga_quente']:,.0f} MW\n"
    textstr += f"Carga Media Frio:   {caso['carga_frio']:,.0f} MW\n"
    textstr += f"Diferenca:          {caso['diff_carga']:+,.0f} MW ({caso['diff_carga_pct']:+.1f}%)"
    
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props)
    
    # Calcular diferença hora a hora
    perfil_diff = pd.merge(
        perfil_quente[['hora', 'carga_mw', 'temp_brasil_c']],
        perfil_frio[['hora', 'carga_mw', 'temp_brasil_c']],
        on='hora',
        suffixes=('_quente', '_frio')
    )
    perfil_diff['diff_carga'] = perfil_diff['carga_mw_quente'] - perfil_diff['carga_mw_frio']
    perfil_diff['diff_temp'] = perfil_diff['temp_brasil_c_quente'] - perfil_diff['temp_brasil_c_frio']
    
    print(f"\n[CASO {idx+1}] Mes {caso['mes']}/{caso['ano']:.0f} - Delta Temp Medio: {caso['diff_temp']:+.1f}C")
    print(f"  Dia Quente: {caso['data_quente']} ({caso['temp_quente']:.1f}C) - Carga: {caso['carga_quente']:,.0f} MW")
    print(f"  Dia Frio:   {caso['data_frio']} ({caso['temp_frio']:.1f}C) - Carga: {caso['carga_frio']:,.0f} MW")
    print(f"  Diferenca:  {caso['diff_carga']:+,.0f} MW ({caso['diff_carga_pct']:+.1f}%)")
    
    print(f"\n  Perfil hora a hora:")
    print(f"  {'Hora':>6} | {'Temp Quente':>12} | {'Temp Frio':>12} | {'Delta T':>10} | {'Carga Quente':>13} | {'Carga Frio':>13} | {'Delta Carga':>13} | {'Delta %':>10}")
    print("  " + "-"*120)
    
    for _, h in perfil_diff.iterrows():
        print(f"  {h['hora']:>6.0f} | {h['temp_brasil_c_quente']:>10.1f}C | {h['temp_brasil_c_frio']:>10.1f}C | "
              f"{h['diff_temp']:>+9.1f}C | {h['carga_mw_quente']:>11,.0f} MW | {h['carga_mw_frio']:>11,.0f} MW | "
              f"{h['diff_carga']:>+11,.0f} MW | {(h['diff_carga']/h['carga_mw_frio']*100):>+9.1f}%")
    
    # Correlação entre diff_temp e diff_carga hora a hora
    corr_hora = perfil_diff[['diff_temp', 'diff_carga']].corr().iloc[0, 1]
    print(f"\n  Correlacao (diff_temp x diff_carga) hora a hora: {corr_hora:+.4f}")

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '17_comparacao_dias_quente_frio.png', dpi=150, bbox_inches='tight')
print(f"\n[OK] Grafico salvo: 17_comparacao_dias_quente_frio.png")

# ============================================================================
# RESUMO ESTATÍSTICO GERAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO ESTATISTICO GERAL")
print("="*100)

print(f"\nTotal de pares analisados: {len(df_comp)}")
print(f"\nDIFERENCAS DE TEMPERATURA:")
print(f"  Media:   {df_comp['diff_temp'].mean():>8.1f}C")
print(f"  Mediana: {df_comp['diff_temp'].median():>8.1f}C")
print(f"  Min:     {df_comp['diff_temp'].min():>8.1f}C")
print(f"  Max:     {df_comp['diff_temp'].max():>8.1f}C")

print(f"\nDIFERENCAS DE CARGA (em MW):")
print(f"  Media:   {df_comp['diff_carga'].mean():>+10,.0f} MW")
print(f"  Mediana: {df_comp['diff_carga'].median():>+10,.0f} MW")
print(f"  Std:     {df_comp['diff_carga'].std():>10,.0f} MW")
print(f"  Min:     {df_comp['diff_carga'].min():>+10,.0f} MW")
print(f"  Max:     {df_comp['diff_carga'].max():>+10,.0f} MW")

print(f"\nDIFERENCAS DE CARGA (em %):")
print(f"  Media:   {df_comp['diff_carga_pct'].mean():>+8.1f}%")
print(f"  Mediana: {df_comp['diff_carga_pct'].median():>+8.1f}%")
print(f"  Std:     {df_comp['diff_carga_pct'].std():>8.1f}%")
print(f"  Min:     {df_comp['diff_carga_pct'].min():>+8.1f}%")
print(f"  Max:     {df_comp['diff_carga_pct'].max():>+8.1f}%")

# Correlação geral
corr_geral = df_comp[['diff_temp', 'diff_carga']].corr().iloc[0, 1]
corr_geral_pct = df_comp[['diff_temp', 'diff_carga_pct']].corr().iloc[0, 1]

print(f"\nCORRELACAO GERAL:")
print(f"  diff_temp x diff_carga (MW):  {corr_geral:>+8.4f}")
print(f"  diff_temp x diff_carga (%):   {corr_geral_pct:>+8.4f}")

# Regressão linear
from scipy import stats
slope, intercept, r_value, p_value, std_err = stats.linregress(df_comp['diff_temp'], df_comp['diff_carga'])

print(f"\nREGRESSAO LINEAR (diff_carga = a * diff_temp + b):")
print(f"  Coeficiente (a): {slope:>+10.1f} MW/C")
print(f"  Intercepto (b):  {intercept:>+10.1f} MW")
print(f"  R-squared:       {r_value**2:>10.4f}")
print(f"  P-value:         {p_value:>10.6f}")

print(f"\nINTERPRETACAO:")
print(f"  Para cada 1 C de diferenca de temperatura entre 2 dias uteis do mesmo mes,")
print(f"  a carga varia em media {slope:+.1f} MW ({slope/80000*100:+.2f}% da carga media)")

# Gráfico scatter geral
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# Subplot 1: diff_temp vs diff_carga
ax = axes[0]
ax.scatter(df_comp['diff_temp'], df_comp['diff_carga'], alpha=0.6, s=50, color='steelblue')
x_line = np.linspace(df_comp['diff_temp'].min(), df_comp['diff_temp'].max(), 100)
y_line = slope * x_line + intercept
ax.plot(x_line, y_line, 'r-', linewidth=2, label=f'y = {slope:.1f}x + {intercept:.1f}\nR2 = {r_value**2:.4f}')
ax.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
ax.axvline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
ax.set_xlabel('Diferenca de Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Diferenca de Carga (MW)', fontsize=12, fontweight='bold')
ax.set_title('Diferenca de Temperatura vs Diferenca de Carga\n(Dias Uteis do Mesmo Mes)', 
             fontsize=13, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3)

# Subplot 2: diff_temp vs diff_carga_pct
ax = axes[1]
ax.scatter(df_comp['diff_temp'], df_comp['diff_carga_pct'], alpha=0.6, s=50, color='darkgreen')
slope2, intercept2, r_value2, _, _ = stats.linregress(df_comp['diff_temp'], df_comp['diff_carga_pct'])
x_line = np.linspace(df_comp['diff_temp'].min(), df_comp['diff_temp'].max(), 100)
y_line = slope2 * x_line + intercept2
ax.plot(x_line, y_line, 'r-', linewidth=2, label=f'y = {slope2:.2f}x + {intercept2:.2f}\nR2 = {r_value2**2:.4f}')
ax.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
ax.axvline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
ax.set_xlabel('Diferenca de Temperatura (C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Diferenca de Carga (%)', fontsize=12, fontweight='bold')
ax.set_title('Diferenca de Temperatura vs Diferenca de Carga (%)\n(Dias Uteis do Mesmo Mes)', 
             fontsize=13, fontweight='bold')
ax.legend(fontsize=11, loc='best')
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / '18_scatter_diff_temp_carga.png', dpi=150, bbox_inches='tight')
print(f"[OK] Grafico salvo: 18_scatter_diff_temp_carga.png")

print("\n" + "="*100)
print(f"Graficos salvos em: {OUTPUT_DIR}")
print("="*100)

# Salvar dados
df_comp.to_csv(OUTPUT_DIR / 'comparacao_dias_quente_frio.csv', index=False)
print(f"\n[OK] Dados salvos: comparacao_dias_quente_frio.csv")





