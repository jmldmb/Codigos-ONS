"""
GERAR CURVAS DE EXCEDÊNCIA E Q-Q PLOTS POR MÊS
================================================

Para cada mês:
1. Curva de Excedência (Duration Curve): Real vs Simulado
2. Q-Q Plot: Comparação de quantis Real vs Simulado com P90 destacado
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats

print("="*100)
print("  GERANDO CURVAS DE EXCEDENCIA E Q-Q PLOTS POR MES")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "carga_v6_com_constraint"
OUTPUT_DIR = BACKTEST_DIR / "curvas_excedencia_qq"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CARREGAR DADOS DO BACKTEST
# ============================================================================
print("\n[1/3] CARREGANDO DADOS DO BACKTEST...")

df_backtest = pd.read_csv(BACKTEST_DIR / 'backtest_completo.csv')
df_backtest['timestamp'] = pd.to_datetime(df_backtest['timestamp'])
df_backtest['ano'] = df_backtest['timestamp'].dt.year
df_backtest['mes'] = df_backtest['timestamp'].dt.month

print(f"  [OK] {len(df_backtest):,} horas carregadas")

# Identificar meses únicos
meses_unicos = df_backtest.groupby(['ano', 'mes']).size().reset_index()[['ano', 'mes']]
print(f"  Total de meses: {len(meses_unicos)}")

meses_nomes = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

# ============================================================================
# GERAR CURVAS DE EXCEDÊNCIA POR MÊS
# ============================================================================
print("\n[2/3] GERANDO CURVAS DE EXCEDENCIA...")

graficos_excedencia = 0

for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    # Filtrar dados do mês
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)].copy()
    
    if len(df_mes) < 24:  # Mês incompleto
        print(f"  [{idx+1}/{len(meses_unicos)}] {ano}-{mes:02d} - PULADO (apenas {len(df_mes)} horas)")
        continue
    
    # Ordenar valores para curva de excedência
    carga_real_sorted = np.sort(df_mes['carga_real'].values)[::-1]  # Decrescente
    carga_sim_sorted = np.sort(df_mes['carga_sim'].values)[::-1]
    
    # Percentis de excedência
    n = len(carga_real_sorted)
    excedencia = np.arange(1, n + 1) / n * 100
    
    # Calcular P10, P50, P90
    p10_real = np.percentile(df_mes['carga_real'], 90)
    p50_real = np.percentile(df_mes['carga_real'], 50)
    p90_real = np.percentile(df_mes['carga_real'], 10)
    
    p10_sim = np.percentile(df_mes['carga_sim'], 90)
    p50_sim = np.percentile(df_mes['carga_sim'], 50)
    p90_sim = np.percentile(df_mes['carga_sim'], 10)
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(14, 8))
    
    ax.plot(excedencia, carga_real_sorted, 
           label='Real', color='blue', linewidth=2.5, alpha=0.8)
    ax.plot(excedencia, carga_sim_sorted, 
           label='Simulado V6', color='green', linewidth=2.5, alpha=0.8, linestyle='--')
    
    # Linhas verticais P10, P50, P90
    ax.axvline(10, color='red', linestyle=':', linewidth=1.5, alpha=0.5, label='P90 (10% excedência)')
    ax.axvline(50, color='orange', linestyle=':', linewidth=1.5, alpha=0.5, label='P50 (50% excedência)')
    ax.axvline(90, color='purple', linestyle=':', linewidth=1.5, alpha=0.5, label='P10 (90% excedência)')
    
    ax.set_xlabel('Excedencia (%)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
    ax.set_title(f'Curva de Excedencia: {meses_nomes[mes]} {ano}\n' +
                f'P90 Real={p90_real:,.0f} MW vs Sim={p90_sim:,.0f} MW | ' +
                f'P50 Real={p50_real:,.0f} MW vs Sim={p50_sim:,.0f} MW',
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # Salvar
    filename = f'excedencia_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
    plt.savefig(OUTPUT_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    graficos_excedencia += 1
    print(f"  [{idx+1}/{len(meses_unicos)}] {ano}-{mes:02d} {meses_nomes[mes]:>10} - Salvo: {filename}")

# ============================================================================
# GERAR Q-Q PLOTS POR MÊS
# ============================================================================
print("\n[3/3] GERANDO Q-Q PLOTS...")

graficos_qq = 0

for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    # Filtrar dados do mês
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)].copy()
    
    if len(df_mes) < 24:  # Mês incompleto
        continue
    
    # Calcular quantis
    quantis = np.linspace(0, 100, 101)  # 0%, 1%, 2%, ..., 100%
    quantis_real = np.percentile(df_mes['carga_real'], quantis)
    quantis_sim = np.percentile(df_mes['carga_sim'], quantis)
    
    # P90 (quantil 90%)
    p90_real = np.percentile(df_mes['carga_real'], 90)
    p90_sim = np.percentile(df_mes['carga_sim'], 90)
    erro_p90 = abs(p90_sim - p90_real)
    erro_p90_pct = erro_p90 / p90_real * 100
    
    # R² entre quantis
    r2_quantis = stats.pearsonr(quantis_real, quantis_sim)[0] ** 2
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(10, 10))
    
    # Linha 1:1 (perfeito)
    min_val = min(quantis_real.min(), quantis_sim.min())
    max_val = max(quantis_real.max(), quantis_sim.max())
    ax.plot([min_val, max_val], [min_val, max_val], 
           'k--', linewidth=2, alpha=0.5, label='Linha 1:1 (perfeito)')
    
    # Q-Q plot
    ax.scatter(quantis_real, quantis_sim, 
              c=quantis, cmap='viridis', s=50, alpha=0.7, edgecolors='black', linewidth=0.5)
    
    # Destacar P90
    idx_p90 = np.argmin(np.abs(quantis - 90))
    ax.scatter([quantis_real[idx_p90]], [quantis_sim[idx_p90]], 
              color='red', s=300, marker='*', edgecolors='darkred', linewidth=2,
              label=f'P90: Real={p90_real:,.0f} vs Sim={p90_sim:,.0f} MW', zorder=5)
    
    # Adicionar linhas de referência para P90
    ax.axvline(p90_real, color='red', linestyle=':', linewidth=1.5, alpha=0.3)
    ax.axhline(p90_sim, color='red', linestyle=':', linewidth=1.5, alpha=0.3)
    
    ax.set_xlabel('Quantis Real (MW)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Quantis Simulado (MW)', fontsize=12, fontweight='bold')
    ax.set_title(f'Q-Q Plot: {meses_nomes[mes]} {ano}\n' +
                f'R2={r2_quantis:.4f} | Erro P90={erro_p90:,.0f} MW ({erro_p90_pct:.2f}%)',
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='upper left')
    ax.grid(True, alpha=0.3)
    
    # Garantir aspecto quadrado
    ax.set_aspect('equal', adjustable='box')
    
    # Colorbar
    cbar = plt.colorbar(ax.collections[0], ax=ax, label='Percentil (%)')
    cbar.set_label('Percentil (%)', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    
    # Salvar
    filename = f'qq_plot_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
    plt.savefig(OUTPUT_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    graficos_qq += 1
    print(f"  [{idx+1}/{len(meses_unicos)}] {ano}-{mes:02d} {meses_nomes[mes]:>10} - Erro P90={erro_p90_pct:5.2f}% - Salvo: {filename}")

# ============================================================================
# GERAR RESUMO DE ERROS P90
# ============================================================================
print("\n[BONUS] GERANDO RESUMO DE ERROS P90...")

resumo_p90 = []

for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)].copy()
    
    if len(df_mes) >= 24:
        p90_real = np.percentile(df_mes['carga_real'], 90)
        p90_sim = np.percentile(df_mes['carga_sim'], 90)
        erro_p90 = p90_sim - p90_real
        erro_p90_pct = erro_p90 / p90_real * 100
        
        resumo_p90.append({
            'ano': ano,
            'mes': mes,
            'mes_nome': meses_nomes[mes],
            'p90_real': p90_real,
            'p90_sim': p90_sim,
            'erro_p90_mw': erro_p90,
            'erro_p90_pct': erro_p90_pct
        })

df_resumo_p90 = pd.DataFrame(resumo_p90)
df_resumo_p90.to_csv(OUTPUT_DIR / 'resumo_erros_p90.csv', index=False)

print(f"  [OK] Salvo: resumo_erros_p90.csv")

# Estatísticas gerais
print(f"\n  ESTATISTICAS P90:")
print(f"    Erro medio:  {df_resumo_p90['erro_p90_pct'].mean():+6.2f}%")
print(f"    Erro mediano: {df_resumo_p90['erro_p90_pct'].median():+6.2f}%")
print(f"    Desvio padrao: {df_resumo_p90['erro_p90_pct'].std():6.2f}%")
print(f"    Max erro abs: {df_resumo_p90['erro_p90_pct'].abs().max():6.2f}%")

# ============================================================================
# GERAR ÍNDICE HTML
# ============================================================================
print("\n[HTML] GERANDO INDICE HTML...")

periodo = f"{df_backtest['timestamp'].min()} ate {df_backtest['timestamp'].max()}"

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Curvas de Excedencia e Q-Q Plots - Modelo V6</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }}
        h1 {{
            color: #333;
            text-align: center;
        }}
        .container {{
            max-width: 1600px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .month-section {{
            margin-bottom: 50px;
            border-bottom: 3px solid #eee;
            padding-bottom: 30px;
        }}
        .month-title {{
            font-size: 26px;
            font-weight: bold;
            color: #2c5aa0;
            margin-bottom: 15px;
        }}
        .graphs-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-top: 20px;
        }}
        .graph-box {{
            border: 2px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            background-color: #fafafa;
        }}
        .graph-box h3 {{
            margin-top: 0;
            font-size: 18px;
            color: #555;
        }}
        img {{
            width: 100%%;
            height: auto;
            border-radius: 5px;
        }}
        .summary {{
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 30px;
        }}
        .summary table {{
            width: 100%%;
            border-collapse: collapse;
            margin-top: 10px;
        }}
        .summary th, .summary td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        .summary th {{
            background-color: #2c5aa0;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Curvas de Excedencia e Q-Q Plots - Modelo V6</h1>
        
        <div class="summary">
            <h2>Resumo Geral</h2>
            <strong>Total de meses analisados:</strong> {graficos_excedencia}<br>
            <strong>Periodo:</strong> {periodo}<br>
            <strong>Modelo:</strong> V6 com regressoes separadas DU/FDS + Constraint<br><br>
            
            <h3>Estatisticas Erro P90:</h3>
            <table>
                <tr>
                    <th>Metrica</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td>Erro Medio P90</td>
                    <td>{df_resumo_p90['erro_p90_pct'].mean():+.2f}%</td>
                </tr>
                <tr>
                    <td>Erro Mediano P90</td>
                    <td>{df_resumo_p90['erro_p90_pct'].median():+.2f}%</td>
                </tr>
                <tr>
                    <td>Desvio Padrao</td>
                    <td>{df_resumo_p90['erro_p90_pct'].std():.2f}%</td>
                </tr>
                <tr>
                    <td>Max Erro Abs P90</td>
                    <td>{df_resumo_p90['erro_p90_pct'].abs().max():.2f}%</td>
                </tr>
            </table>
        </div>
"""

# Adicionar cada mês
for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)]
    
    if len(df_mes) >= 24:
        filename_exc = f'excedencia_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
        filename_qq = f'qq_plot_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
        
        p90_real = np.percentile(df_mes['carga_real'], 90)
        p90_sim = np.percentile(df_mes['carga_sim'], 90)
        erro_p90_pct = (p90_sim - p90_real) / p90_real * 100
        
        html_content += f"""
        <div class="month-section">
            <div class="month-title">{meses_nomes[mes]} {ano}</div>
            <p><strong>P90 Real:</strong> {p90_real:,.0f} MW | 
               <strong>P90 Sim:</strong> {p90_sim:,.0f} MW | 
               <strong>Erro P90:</strong> {erro_p90_pct:+.2f}%</p>
            
            <div class="graphs-container">
                <div class="graph-box">
                    <h3>Curva de Excedencia</h3>
                    <img src="{filename_exc}" alt="Excedencia {meses_nomes[mes]} {ano}">
                </div>
                <div class="graph-box">
                    <h3>Q-Q Plot</h3>
                    <img src="{filename_qq}" alt="Q-Q Plot {meses_nomes[mes]} {ano}">
                </div>
            </div>
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

with open(OUTPUT_DIR / 'index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"  [OK] Salvo: index.html")

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("\n" + "="*100)
print("  RESUMO")
print("="*100)

print(f"""
GRAFICOS GERADOS:
  - {graficos_excedencia} Curvas de Excedencia
  - {graficos_qq} Q-Q Plots
  - 1 Resumo CSV (erros P90)
  - 1 Indice HTML

LOCALIZACAO: {OUTPUT_DIR}

COMO VISUALIZAR:
  Abrir index.html no navegador!
""")

print("="*100)





