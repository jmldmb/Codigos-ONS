"""
ANÁLISE DE IMPACTO DOS FERIADOS NA CARGA
==========================================
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

print("="*100)
print("  ANÁLISE: IMPACTO DOS FERIADOS NA CARGA ELÉTRICA")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "output" / "analise_historica" / "carga"

# ============================================================================
# 1. CARREGAR DADOS DE CARGA PROCESSADOS
# ============================================================================
print("\n[1/4] CARREGANDO DADOS DE CARGA...")

df = pd.read_parquet(OUTPUT_DIR / "dados_processados_mai2023.parquet")
print(f"  [OK] {len(df):,} registros carregados")

# ============================================================================
# 2. CARREGAR FERIADOS
# ============================================================================
print("\n[2/4] CARREGANDO FERIADOS...")

feriados_path = BASE_DIR / "Data" / "auxiliares" / "feriados_nacionais_brasil.csv"
df_feriados = pd.read_csv(feriados_path)
df_feriados['data'] = pd.to_datetime(df_feriados['data']).dt.date

print(f"  [OK] {len(df_feriados)} feriados carregados")

# Marcar feriados no dataset
df['eh_feriado'] = df['data'].isin(df_feriados['data'].values)

# Merge para pegar nome do feriado
df = df.merge(
    df_feriados.rename(columns={'data': 'data_feriado'}),
    left_on='data',
    right_on='data_feriado',
    how='left'
)

# Criar nova classificação de tipo de dia
df['tipo_dia_v2'] = df['tipo_dia'].copy()
df.loc[df['eh_feriado'], 'tipo_dia_v2'] = 'FERIADO'

print(f"\n  Registros por tipo de dia:")
print(df['tipo_dia_v2'].value_counts().sort_index())

# ============================================================================
# 3. ANÁLISE COMPARATIVA
# ============================================================================
print("\n[3/4] ANÁLISE COMPARATIVA...")

# Estatísticas por tipo
stats = df.groupby('tipo_dia_v2').agg({
    'carga_mw': ['mean', 'std', 'min', 'max', 'count']
}).round(0)

stats.columns = ['media', 'std', 'min', 'max', 'n_horas']
stats = stats.reset_index()

print(f"\n{'Tipo':>10} | {'Carga Média':>12} | {'Std':>10} | {'N Horas':>8} | {'% vs DU':>10}")
print("-"*65)

carga_du = stats[stats['tipo_dia_v2'] == 'DU']['media'].values[0]

for _, row in stats.iterrows():
    tipo = row['tipo_dia_v2']
    media = row['media']
    std = row['std']
    n = row['n_horas']
    pct_vs_du = ((media / carga_du - 1) * 100)
    
    print(f"{tipo:>10} | {media:>10,.0f} MW | {std:>8,.0f} MW | {n:>8.0f} | {pct_vs_du:>+9.1f}%")

# Perfil horário por tipo
print("\n[Gerando perfis horários por tipo...]")
df_perfis = df.groupby(['tipo_dia_v2', 'hora'])['carga_mw'].mean().reset_index()

# Comparar feriados com DU/SAB/DOM
feriado_perfil = df[df['tipo_dia_v2'] == 'FERIADO'].groupby('hora')['carga_mw'].mean()
du_perfil = df[df['tipo_dia_v2'] == 'DU'].groupby('hora')['carga_mw'].mean()
sab_perfil = df[df['tipo_dia_v2'] == 'SAB'].groupby('hora')['carga_mw'].mean()
dom_perfil = df[df['tipo_dia_v2'] == 'DOM'].groupby('hora')['carga_mw'].mean()

# Calcular correlação entre feriado e outros tipos
corr_feriado_du = feriado_perfil.corr(du_perfil)
corr_feriado_sab = feriado_perfil.corr(sab_perfil)
corr_feriado_dom = feriado_perfil.corr(dom_perfil)

print(f"\n[CORRELAÇÃO DE PERFIL HORÁRIO]")
print(f"  Feriado vs DU:  {corr_feriado_du:.4f}")
print(f"  Feriado vs SAB: {corr_feriado_sab:.4f}")
print(f"  Feriado vs DOM: {corr_feriado_dom:.4f}")

if corr_feriado_dom > corr_feriado_sab and corr_feriado_dom > corr_feriado_du:
    print(f"  -> Feriado se comporta MAIS como DOMINGO")
elif corr_feriado_sab > corr_feriado_du:
    print(f"  -> Feriado se comporta MAIS como SABADO")
else:
    print(f"  -> Feriado tem perfil PROPRIO")

# Top 5 feriados com menor/maior carga média
feriados_carga = df[df['eh_feriado']].groupby('data').agg({
    'carga_mw': 'mean',
    'nome': 'first',
    'temp_brasil_c': 'mean'
}).reset_index()

print(f"\n[TOP 5 FERIADOS COM MENOR CARGA]")
print(f"{'Data':^12} | {'Nome':^30} | {'Carga Média':^14} | {'Temp':^8}")
print("-"*75)
for _, row in feriados_carga.nsmallest(5, 'carga_mw').iterrows():
    print(f"{row['data']} | {row['nome']:<30} | {row['carga_mw']:>12,.0f} MW | {row['temp_brasil_c']:>6.1f}C")

print(f"\n[TOP 5 FERIADOS COM MAIOR CARGA]")
print(f"{'Data':^12} | {'Nome':^30} | {'Carga Média':^14} | {'Temp':^8}")
print("-"*75)
for _, row in feriados_carga.nlargest(5, 'carga_mw').iterrows():
    print(f"{row['data']} | {row['nome']:<30} | {row['carga_mw']:>12,.0f} MW | {row['temp_brasil_c']:>6.1f}C")

# ============================================================================
# 4. VISUALIZAÇÕES
# ============================================================================
print("\n[4/4] GERANDO VISUALIZAÇÕES...")

# Figura 1: Perfil horário comparativo
fig, ax = plt.subplots(figsize=(16, 8))
for tipo in ['DU', 'SAB', 'DOM', 'FERIADO']:
    df_tipo = df[df['tipo_dia_v2'] == tipo].groupby('hora')['carga_mw'].mean().reset_index()
    
    cores = {'DU': 'blue', 'SAB': 'orange', 'DOM': 'green', 'FERIADO': 'red'}
    estilos = {'DU': '-', 'SAB': '--', 'DOM': '-.', 'FERIADO': '-'}
    larguras = {'DU': 2, 'SAB': 2, 'DOM': 2, 'FERIADO': 3}
    
    ax.plot(df_tipo['hora'], df_tipo['carga_mw'], 
            color=cores[tipo], linestyle=estilos[tipo], linewidth=larguras[tipo],
            marker='o', markersize=6, label=tipo, alpha=0.8)

ax.set_xlabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_ylabel('Carga Média (MW)', fontsize=13, fontweight='bold')
ax.set_title('Perfil Horário: DU vs SAB vs DOM vs FERIADO', fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(range(0, 24))
ax.legend(fontsize=12, loc='best')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '09_perfil_comparativo_feriados.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 09_perfil_comparativo_feriados.png")

# Figura 2: Boxplot por tipo de dia
fig, ax = plt.subplots(figsize=(12, 7))
df_plot = df[['tipo_dia_v2', 'carga_mw']].copy()
df_plot['tipo_dia_v2'] = pd.Categorical(df_plot['tipo_dia_v2'], 
                                         categories=['DU', 'SAB', 'DOM', 'FERIADO'],
                                         ordered=True)
df_plot.boxplot(column='carga_mw', by='tipo_dia_v2', ax=ax)
ax.set_xlabel('Tipo de Dia', fontsize=13, fontweight='bold')
ax.set_ylabel('Carga (MW)', fontsize=13, fontweight='bold')
ax.set_title('Distribuição de Carga por Tipo de Dia (com Feriados)', fontsize=15, fontweight='bold')
plt.suptitle('')  # Remove título automático
ax.grid(True, alpha=0.3, axis='y')
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '10_boxplot_com_feriados.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 10_boxplot_com_feriados.png")

# Figura 3: Diferença percentual vs DU por hora
fig, ax = plt.subplots(figsize=(16, 8))
for tipo in ['SAB', 'DOM', 'FERIADO']:
    df_tipo = df[df['tipo_dia_v2'] == tipo].groupby('hora')['carga_mw'].mean()
    df_du = df[df['tipo_dia_v2'] == 'DU'].groupby('hora')['carga_mw'].mean()
    
    diff_pct = ((df_tipo - df_du) / df_du * 100)
    
    cores = {'SAB': 'orange', 'DOM': 'green', 'FERIADO': 'red'}
    larguras = {'SAB': 2, 'DOM': 2, 'FERIADO': 3}
    
    ax.plot(diff_pct.index, diff_pct.values, 
            color=cores[tipo], linewidth=larguras[tipo],
            marker='o', markersize=6, label=f'{tipo} vs DU', alpha=0.8)

ax.axhline(0, color='black', linewidth=1, linestyle='--', alpha=0.5)
ax.set_xlabel('Hora do Dia', fontsize=13, fontweight='bold')
ax.set_ylabel('Diferença vs DU (%)', fontsize=13, fontweight='bold')
ax.set_title('Diferença Percentual de Carga vs Dia Útil', fontsize=15, fontweight='bold', pad=20)
ax.set_xticks(range(0, 24))
ax.legend(fontsize=12, loc='best')
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '11_diferenca_pct_vs_du.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 11_diferenca_pct_vs_du.png")

# Figura 4: Carga por feriado individual
fig, ax = plt.subplots(figsize=(16, 8))
feriados_carga_sorted = feriados_carga.sort_values('carga_mw', ascending=False)
cores = plt.cm.RdYlGn_r(np.linspace(0, 1, len(feriados_carga_sorted)))
bars = ax.barh(range(len(feriados_carga_sorted)), feriados_carga_sorted['carga_mw'], 
               color=cores, edgecolor='black', alpha=0.8)
ax.set_yticks(range(len(feriados_carga_sorted)))
ax.set_yticklabels([f"{row['data']} - {row['nome']}" for _, row in feriados_carga_sorted.iterrows()],
                    fontsize=9)
ax.set_xlabel('Carga Média Diária (MW)', fontsize=12, fontweight='bold')
ax.set_title('Carga Média por Feriado (Mai/2023+)', fontsize=14, fontweight='bold')
ax.axvline(carga_du, color='blue', linewidth=2, linestyle='--', alpha=0.7, label=f'DU: {carga_du:,.0f} MW')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='x')
for i, (_, row) in enumerate(feriados_carga_sorted.iterrows()):
    ax.text(row['carga_mw'] + 500, i, f"{row['carga_mw']:,.0f}", 
            va='center', fontsize=9)
plt.tight_layout()
plt.savefig(OUTPUT_DIR / '12_carga_por_feriado.png', dpi=150, bbox_inches='tight')
print(f"  [OK] Salvo: 12_carga_por_feriado.png")

# ============================================================================
# SALVAR DADOS ATUALIZADOS
# ============================================================================
print("\n[SALVANDO] Dados atualizados com feriados...")
df.to_parquet(OUTPUT_DIR / "dados_processados_mai2023_com_feriados.parquet", index=False)
print(f"  [OK] Salvo: dados_processados_mai2023_com_feriados.parquet")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO FINAL: IMPACTO DOS FERIADOS")
print("="*100)

print(f"""
COMPARAÇÃO DE CARGA MÉDIA:
  • DU:       {stats[stats['tipo_dia_v2']=='DU']['media'].values[0]:>10,.0f} MW (baseline)
  • SAB:      {stats[stats['tipo_dia_v2']=='SAB']['media'].values[0]:>10,.0f} MW ({((stats[stats['tipo_dia_v2']=='SAB']['media'].values[0]/carga_du-1)*100):>+6.1f}%)
  • DOM:      {stats[stats['tipo_dia_v2']=='DOM']['media'].values[0]:>10,.0f} MW ({((stats[stats['tipo_dia_v2']=='DOM']['media'].values[0]/carga_du-1)*100):>+6.1f}%)
  • FERIADO:  {stats[stats['tipo_dia_v2']=='FERIADO']['media'].values[0]:>10,.0f} MW ({((stats[stats['tipo_dia_v2']=='FERIADO']['media'].values[0]/carga_du-1)*100):>+6.1f}%)

CORRELAÇÃO DE PERFIL HORÁRIO:
  • Feriado vs DU:  {corr_feriado_du:>6.4f}
  • Feriado vs SAB: {corr_feriado_sab:>6.4f}
  • Feriado vs DOM: {corr_feriado_dom:>6.4f}
  
RECOMENDAÇÃO:
  Feriados {"SÃO PRÓXIMOS DE DOMINGOS" if corr_feriado_dom > 0.95 else "TÊM PERFIL INTERMEDIÁRIO ENTRE SAB E DOM" if corr_feriado_sab > corr_feriado_du else "TÊM PERFIL PRÓPRIO"}
  
TIPOS DE DIA PARA O MODELO V6:
  • DU (Dias Úteis SEM feriados)
  • SAB
  • DOM
  • FERIADO (perfil próprio)
  
Total: 4 tipos de dia
""")

print("="*100)
print(f"\nGráficos salvos em: {OUTPUT_DIR}")
print("="*100)





