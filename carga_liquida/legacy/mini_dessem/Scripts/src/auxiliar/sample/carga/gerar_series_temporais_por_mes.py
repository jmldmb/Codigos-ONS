"""
GERAR SÉRIES TEMPORAIS POR MÊS
================================

Cria um gráfico de série temporal (Real vs Simulado) para cada mês
dos dados de treinamento
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

print("="*100)
print("  GERANDO SÉRIES TEMPORAIS POR MÊS")
print("="*100)

BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
BACKTEST_DIR = BASE_DIR / "output" / "sample" / "carga_v6_com_constraint"
SERIES_DIR = BACKTEST_DIR / "series_temporais_por_mes"
SERIES_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# CARREGAR DADOS DO BACKTEST
# ============================================================================
print("\n[1/2] CARREGANDO DADOS DO BACKTEST...")

df_backtest = pd.read_csv(BACKTEST_DIR / 'backtest_completo.csv')
df_backtest['timestamp'] = pd.to_datetime(df_backtest['timestamp'])
df_backtest['ano'] = df_backtest['timestamp'].dt.year
df_backtest['mes'] = df_backtest['timestamp'].dt.month

print(f"  [OK] {len(df_backtest):,} horas carregadas")

# Identificar meses únicos
meses_unicos = df_backtest.groupby(['ano', 'mes']).size().reset_index()[['ano', 'mes']]
print(f"  Total de meses: {len(meses_unicos)}")

# ============================================================================
# GERAR GRÁFICO PARA CADA MÊS
# ============================================================================
print("\n[2/2] GERANDO GRÁFICOS POR MÊS...")

meses_nomes = {
    1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
    5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
    9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
}

graficos_gerados = 0

for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    # Filtrar dados do mês
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)].copy()
    df_mes = df_mes.sort_values('timestamp')
    
    if len(df_mes) < 24:  # Mês incompleto
        print(f"  [{idx+1}/{len(meses_unicos)}] {ano}-{mes:02d} - PULADO (apenas {len(df_mes)} horas)")
        continue
    
    # Calcular métricas do mês
    erro_pct = ((df_mes['carga_sim'] - df_mes['carga_real']) / df_mes['carga_real'] * 100).abs()
    mape_mes = erro_pct.mean()
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(20, 8))
    
    ax.plot(df_mes['timestamp'], df_mes['carga_real'], 
           label='Real', color='blue', linewidth=2, alpha=0.7)
    ax.plot(df_mes['timestamp'], df_mes['carga_sim'], 
           label='Simulado V6', color='green', linewidth=2, alpha=0.7, linestyle='--')
    
    ax.set_xlabel('Data/Hora', fontsize=12, fontweight='bold')
    ax.set_ylabel('Carga (MW)', fontsize=12, fontweight='bold')
    ax.set_title(f'Serie Temporal: {meses_nomes[mes]} {ano}\n' + 
                f'MAPE = {mape_mes:.2f}% | N = {len(df_mes)} horas', 
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=12, loc='best')
    ax.grid(True, alpha=0.3)
    
    # Rotacionar labels do eixo x
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    # Salvar
    filename = f'serie_temporal_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
    plt.savefig(SERIES_DIR / filename, dpi=150, bbox_inches='tight')
    plt.close()
    
    graficos_gerados += 1
    print(f"  [{idx+1}/{len(meses_unicos)}] {ano}-{mes:02d} {meses_nomes[mes]:>10} - MAPE={mape_mes:5.2f}% - Salvo: {filename}")

# ============================================================================
# GERAR ÍNDICE HTML (BÔNUS)
# ============================================================================
print("\n[BÔNUS] GERANDO ÍNDICE HTML...")

periodo = f"{df_backtest['timestamp'].min()} até {df_backtest['timestamp'].max()}"

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Séries Temporais por Mês - Modelo V6</title>
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
            max-width: 1400px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .month-section {{
            margin-bottom: 40px;
            border-bottom: 2px solid #eee;
            padding-bottom: 20px;
        }}
        .month-title {{
            font-size: 24px;
            font-weight: bold;
            color: #2c5aa0;
            margin-bottom: 10px;
        }}
        img {{
            width: 100%%;
            max-width: 1200px;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 5px;
            margin: 10px 0;
        }}
        .summary {{
            background-color: #e8f4f8;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Séries Temporais por Mês - Modelo V6</h1>
        
        <div class="summary">
            <strong>Total de gráficos:</strong> {graficos_gerados}<br>
            <strong>Período:</strong> {periodo}<br>
            <strong>Modelo:</strong> V6 com regressões separadas DU/FDS + Constraint
        </div>
"""

# Adicionar cada gráfico
for idx, row in meses_unicos.iterrows():
    ano = int(row['ano'])
    mes = int(row['mes'])
    
    df_mes = df_backtest[(df_backtest['ano'] == ano) & (df_backtest['mes'] == mes)]
    
    if len(df_mes) >= 24:
        filename = f'serie_temporal_{ano}_{mes:02d}_{meses_nomes[mes]}.png'
        erro_pct = ((df_mes['carga_sim'] - df_mes['carga_real']) / df_mes['carga_real'] * 100).abs()
        mape_mes = erro_pct.mean()
        
        html_content += f"""
        <div class="month-section">
            <div class="month-title">{meses_nomes[mes]} {ano}</div>
            <p><strong>MAPE:</strong> {mape_mes:.2f}% | <strong>Observações:</strong> {len(df_mes)} horas</p>
            <img src="{filename}" alt="{meses_nomes[mes]} {ano}">
        </div>
"""

html_content += """
    </div>
</body>
</html>
"""

with open(SERIES_DIR / 'index.html', 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"  [OK] Salvo: index.html (índice navegável)")

# ============================================================================
# RESUMO
# ============================================================================
print("\n" + "="*100)
print("  RESUMO")
print("="*100)

print(f"""
GRÁFICOS GERADOS: {graficos_gerados}

LOCALIZAÇÃO: {SERIES_DIR}

ARQUIVOS:
  - {graficos_gerados} gráficos PNG (um por mês)
  - index.html (índice navegável)

COMO VISUALIZAR:
  1. Abrir index.html no navegador para ver todos os gráficos
  2. Ou abrir PNGs individuais por mês
""")

print("="*100)

