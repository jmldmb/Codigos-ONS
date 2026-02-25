"""
Calibração de Parâmetros: Modelo Hidro FD
==========================================

Script para testar e otimizar os parâmetros do modelo de regressão,
focando em reduzir o erro médio horário.

Estratégia:
1. Analisar erros sistemáticos por hora
2. Otimizar peso_hora usando regressão linear
3. Testar diferentes configurações
4. Comparar resultados com modelo original
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from sklearn.linear_model import LinearRegression
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (18, 12)

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
MINI_DESSEM_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
ENA_FILE = MINI_DESSEM_DIR / "Data" / "ENA" / "ENA" / "ENA_HISTORICO.xlsx"
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "calibracao_hidro_fd"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# ===== PARÂMETROS ORIGINAIS =====
PARAMS_ORIGINAIS = {
    'intercept': 3563,
    'ghr': 0.33,
    'ena': 0.15,
    'peso_mes': {
        1: 1944, 2: 2737, 3: 4870, 4: 6687, 5: 5241, 6: 2677,
        7: 1062, 8: -467, 9: -1353, 10: -2544, 11: -1036, 12: 0
    },
    'peso_hora': {
        0: -166, 1: -197, 2: -195, 3: -320, 4: -502, 5: -601,
        6: -530, 7: -363, 8: -183, 9: -159, 10: 11, 11: 589,
        12: 998, 13: 1566, 14: 2290, 15: 2961, 16: 3129, 17: 2816,
        18: 2444, 19: 1975, 20: 1449, 21: 704, 22: 275, 23: 0
    },
    'peso_weekday': 1352,
    'peso_fds': 1523
}

def carregar_dados_completos():
    """Carrega todos os dados necessários."""
    
    print("\n" + "="*80)
    print("  CARREGANDO DADOS")
    print("="*80 + "\n")
    
    # ENA
    print("Carregando ENA...")
    df_ena = pd.read_excel(ENA_FILE)
    df_ena['data_dia'] = pd.to_datetime(df_ena['Data']).dt.date
    df_ena['ena_mwmed'] = df_ena['ena_armazenavel_regiao_mwmed']
    df_ena = df_ena[['data_dia', 'ena_mwmed']]
    
    # FD e R
    print("Carregando FD e R...")
    path_hist = CARGA_LIQ_DIR / "Output" / "carga_liquida_historica.parquet"
    df = pd.read_parquet(path_hist)
    
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    df['ano'] = df['din_instante'].dt.year
    df['mes'] = df['din_instante'].dt.month
    df['hora'] = df['din_instante'].dt.hour
    df['dia_semana'] = df['din_instante'].dt.dayofweek
    df['data_dia'] = df['din_instante'].dt.date
    df['is_weekday'] = df['dia_semana'] < 5
    
    df['FD'] = pd.to_numeric(df['FD'], errors='coerce')
    df['R'] = pd.to_numeric(df['R'], errors='coerce')
    df = df.dropna(subset=['FD', 'R'])
    
    # Merge
    print("Fazendo merge...")
    df = pd.merge(df, df_ena, on='data_dia', how='left')
    df = df.dropna(subset=['ena_mwmed'])
    
    print(f"  [OK] {len(df):,} registros carregados\n")
    
    return df

def calcular_fd_com_params(df, params):
    """Calcula FD usando parâmetros específicos."""
    
    fd_previsto = []
    
    for _, row in df.iterrows():
        mes = int(row['mes'])
        hora = int(row['hora'])
        is_weekday = row['is_weekday']
        R = row['R']
        ENA = row['ena_mwmed']
        
        fd = (
            params['intercept'] +
            params['ghr'] * R +
            params['ena'] * ENA +
            params['peso_mes'][mes] +
            params['peso_hora'][hora] +
            (params['peso_weekday'] if is_weekday else params['peso_fds'])
        )
        
        fd_previsto.append(fd)
    
    return np.array(fd_previsto)

def calcular_metricas(fd_real, fd_previsto):
    """Calcula métricas de desempenho."""
    
    erro = fd_previsto - fd_real
    erro_abs = np.abs(erro)
    
    mae = erro_abs.mean()
    rmse = np.sqrt((erro**2).mean())
    mape = (erro_abs / fd_real).mean() * 100
    bias = erro.mean()
    r2 = np.corrcoef(fd_real, fd_previsto)[0, 1] ** 2
    
    return {
        'mae': mae,
        'rmse': rmse,
        'mape': mape,
        'bias': bias,
        'r2': r2
    }

def analisar_erro_por_hora(df):
    """Analisa erro sistemático por hora."""
    
    print("\n" + "="*80)
    print("  ANÁLISE DE ERRO POR HORA")
    print("="*80 + "\n")
    
    # Calcular com parâmetros originais
    df['FD_previsto_orig'] = calcular_fd_com_params(df, PARAMS_ORIGINAIS)
    df['erro_orig'] = df['FD_previsto_orig'] - df['FD']
    
    # Erro médio por hora
    erro_por_hora = df.groupby('hora').agg({
        'erro_orig': ['mean', 'std', 'count'],
        'FD': 'mean'
    }).reset_index()
    erro_por_hora.columns = ['hora', 'erro_medio', 'erro_std', 'count', 'fd_medio']
    
    print("Erro Médio por Hora (Parâmetros Originais):")
    print("-" * 80)
    print(f"{'Hora':<6} {'Erro Médio (MW)':<18} {'Desvio':<15} {'% do FD Médio':<15}")
    print("-" * 80)
    
    for _, row in erro_por_hora.iterrows():
        pct = (row['erro_medio'] / row['fd_medio']) * 100
        print(f"{int(row['hora']):>4}   {row['erro_medio']:>15,.0f}   {row['erro_std']:>12,.0f}   {pct:>12,.2f}%")
    
    return erro_por_hora, df

def calibrar_parametros_hora_regressao(df):
    """
    Calibra peso_hora usando regressão linear.
    
    Estratégia: Para cada hora, calcular o ajuste necessário
    baseado no erro médio observado.
    """
    
    print("\n" + "="*80)
    print("  CALIBRAÇÃO: MÉTODO 1 - AJUSTE POR ERRO MÉDIO")
    print("="*80 + "\n")
    
    # Calcular erro médio por hora
    erro_por_hora = df.groupby('hora')['erro_orig'].mean()
    
    # Criar novos parâmetros ajustando peso_hora
    params_calibrados_v1 = PARAMS_ORIGINAIS.copy()
    params_calibrados_v1['peso_hora'] = {}
    
    for hora in range(24):
        # Ajustar peso_hora subtraindo o erro médio
        peso_original = PARAMS_ORIGINAIS['peso_hora'][hora]
        erro_medio = erro_por_hora[hora]
        
        # Novo peso = peso original - erro médio (para compensar)
        novo_peso = peso_original - erro_medio
        params_calibrados_v1['peso_hora'][hora] = novo_peso
    
    print("Novos Pesos Horários (Método 1):")
    print("-" * 80)
    print(f"{'Hora':<6} {'Original':<12} {'Erro Médio':<15} {'Novo':<12} {'Delta':<12}")
    print("-" * 80)
    
    for hora in range(24):
        orig = PARAMS_ORIGINAIS['peso_hora'][hora]
        novo = params_calibrados_v1['peso_hora'][hora]
        erro = erro_por_hora[hora]
        delta = novo - orig
        print(f"{hora:>4}   {orig:>10,.0f}   {erro:>12,.0f}   {novo:>10,.0f}   {delta:>10,.0f}")
    
    return params_calibrados_v1

def calibrar_parametros_hora_otimizacao(df):
    """
    Calibra peso_hora usando otimização global.
    
    Minimiza MAE total mantendo os outros parâmetros fixos.
    """
    
    print("\n" + "="*80)
    print("  CALIBRAÇÃO: MÉTODO 2 - OTIMIZAÇÃO GLOBAL")
    print("="*80 + "\n")
    
    print("Otimizando pesos horários para minimizar MAE...")
    
    # Função objetivo: MAE
    def objetivo(pesos_hora):
        params_temp = PARAMS_ORIGINAIS.copy()
        params_temp['peso_hora'] = {h: pesos_hora[h] for h in range(24)}
        
        fd_pred = calcular_fd_com_params(df, params_temp)
        mae = np.abs(fd_pred - df['FD'].values).mean()
        
        return mae
    
    # Valores iniciais (pesos originais)
    x0 = [PARAMS_ORIGINAIS['peso_hora'][h] for h in range(24)]
    
    # Otimização
    print("  Executando otimização (pode levar alguns minutos)...")
    result = minimize(
        objetivo,
        x0,
        method='L-BFGS-B',
        options={'maxiter': 100, 'disp': False}
    )
    
    # Criar parâmetros otimizados
    params_calibrados_v2 = PARAMS_ORIGINAIS.copy()
    params_calibrados_v2['peso_hora'] = {h: result.x[h] for h in range(24)}
    
    print(f"  [OK] Otimização concluída! MAE final: {result.fun:,.0f} MW\n")
    
    print("Novos Pesos Horários (Método 2):")
    print("-" * 80)
    print(f"{'Hora':<6} {'Original':<12} {'Otimizado':<12} {'Delta':<12}")
    print("-" * 80)
    
    for hora in range(24):
        orig = PARAMS_ORIGINAIS['peso_hora'][hora]
        novo = params_calibrados_v2['peso_hora'][hora]
        delta = novo - orig
        print(f"{hora:>4}   {orig:>10,.0f}   {novo:>10,.0f}   {delta:>10,.0f}")
    
    return params_calibrados_v2

def calibrar_parametros_hora_suavizado(df, fator_suavizacao=0.7):
    """
    Calibra peso_hora com suavização para evitar overfitting.
    
    Usa fator de suavização: novo = original + fator * ajuste
    """
    
    print("\n" + "="*80)
    print(f"  CALIBRAÇÃO: MÉTODO 3 - AJUSTE SUAVIZADO (fator={fator_suavizacao})")
    print("="*80 + "\n")
    
    # Calcular erro médio por hora
    erro_por_hora = df.groupby('hora')['erro_orig'].mean()
    
    # Criar novos parâmetros com suavização
    params_calibrados_v3 = PARAMS_ORIGINAIS.copy()
    params_calibrados_v3['peso_hora'] = {}
    
    for hora in range(24):
        peso_original = PARAMS_ORIGINAIS['peso_hora'][hora]
        erro_medio = erro_por_hora[hora]
        
        # Ajuste suavizado
        ajuste = -erro_medio * fator_suavizacao
        novo_peso = peso_original + ajuste
        params_calibrados_v3['peso_hora'][hora] = novo_peso
    
    print("Novos Pesos Horários (Método 3):")
    print("-" * 80)
    print(f"{'Hora':<6} {'Original':<12} {'Ajuste':<12} {'Novo':<12} {'Delta':<12}")
    print("-" * 80)
    
    for hora in range(24):
        orig = PARAMS_ORIGINAIS['peso_hora'][hora]
        novo = params_calibrados_v3['peso_hora'][hora]
        ajuste = -erro_por_hora[hora] * fator_suavizacao
        delta = novo - orig
        print(f"{hora:>4}   {orig:>10,.0f}   {ajuste:>10,.0f}   {novo:>10,.0f}   {delta:>10,.0f}")
    
    return params_calibrados_v3

def comparar_modelos(df, params_dict):
    """Compara diferentes configurações de parâmetros."""
    
    print("\n" + "="*80)
    print("  COMPARAÇÃO DE MODELOS")
    print("="*80 + "\n")
    
    resultados = {}
    
    for nome, params in params_dict.items():
        print(f"Testando: {nome}...")
        
        fd_previsto = calcular_fd_com_params(df, params)
        metricas = calcular_metricas(df['FD'].values, fd_previsto)
        
        # Erro por hora
        df[f'fd_pred_{nome}'] = fd_previsto
        df[f'erro_{nome}'] = fd_previsto - df['FD']
        erro_hora = df.groupby('hora')[f'erro_{nome}'].agg(['mean', 'std']).reset_index()
        
        resultados[nome] = {
            'params': params,
            'metricas': metricas,
            'erro_hora': erro_hora
        }
    
    # Tabela comparativa
    print("\n" + "="*80)
    print("MÉTRICAS GERAIS - COMPARAÇÃO")
    print("="*80)
    print(f"{'Modelo':<25} {'MAE (MW)':<12} {'MAPE (%)':<12} {'Bias (MW)':<12} {'R²':<10}")
    print("-" * 80)
    
    for nome, res in resultados.items():
        m = res['metricas']
        print(f"{nome:<25} {m['mae']:>10,.0f}   {m['mape']:>10,.2f}   {m['bias']:>10,.0f}   {m['r2']:>8,.4f}")
    
    return resultados

def gerar_graficos_comparacao(df, resultados):
    """Gera gráficos comparativos."""
    
    print("\n" + "="*80)
    print("  GERANDO GRÁFICOS COMPARATIVOS")
    print("="*80 + "\n")
    
    # 1. Erro médio por hora - Todos os modelos
    fig, axes = plt.subplots(2, 2, figsize=(20, 14))
    fig.suptitle('Comparação de Calibrações: Erro por Hora', 
                 fontsize=16, fontweight='bold', y=0.995)
    
    # 1.1 Erro médio absoluto
    ax = axes[0, 0]
    for nome, res in resultados.items():
        erro_hora = res['erro_hora']
        ax.plot(erro_hora['hora'], erro_hora['mean'].abs(), 'o-', 
               label=nome, linewidth=2, markersize=6)
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('|Erro Médio| (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Absoluto Médio por Hora', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # 1.2 Erro médio (com sinal)
    ax = axes[0, 1]
    for nome, res in resultados.items():
        erro_hora = res['erro_hora']
        ax.plot(erro_hora['hora'], erro_hora['mean'], 'o-', 
               label=nome, linewidth=2, markersize=6)
    
    ax.axhline(0, color='black', linestyle='--', linewidth=1)
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro Médio (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Médio por Hora (com sinal)', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # 1.3 Desvio padrão do erro
    ax = axes[1, 0]
    for nome, res in resultados.items():
        erro_hora = res['erro_hora']
        ax.plot(erro_hora['hora'], erro_hora['std'], 'o-', 
               label=nome, linewidth=2, markersize=6)
    
    ax.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
    ax.set_ylabel('Desvio Padrão do Erro (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Variabilidade do Erro por Hora', fontsize=13, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # 1.4 Métricas gerais (barras)
    ax = axes[1, 1]
    modelos = list(resultados.keys())
    maes = [resultados[m]['metricas']['mae'] for m in modelos]
    
    x_pos = np.arange(len(modelos))
    bars = ax.bar(x_pos, maes, alpha=0.7, edgecolor='black')
    
    # Colorir baseado em melhoria
    mae_original = resultados['Original']['metricas']['mae']
    for i, (bar, mae) in enumerate(zip(bars, maes)):
        if mae < mae_original:
            bar.set_color('lightgreen')
        else:
            bar.set_color('lightcoral')
        
        # Adicionar valor
        ax.text(bar.get_x() + bar.get_width()/2., mae,
               f'{mae:,.0f}', ha='center', va='bottom', fontsize=10)
    
    ax.set_xticks(x_pos)
    ax.set_xticklabels(modelos, rotation=15, ha='right')
    ax.set_ylabel('MAE (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Comparação de MAE Total', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparacao_calibracoes.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] comparacao_calibracoes.png")
    
    # 2. Comparação de pesos horários
    fig, ax = plt.subplots(1, 1, figsize=(18, 8))
    
    horas = range(24)
    peso_original = [PARAMS_ORIGINAIS['peso_hora'][h] for h in horas]
    
    ax.plot(horas, peso_original, 'o-', label='Original', 
           linewidth=3, markersize=8, color='black', alpha=0.7)
    
    cores = ['red', 'blue', 'green']
    for i, (nome, res) in enumerate(list(resultados.items())[1:]):  # Pular 'Original'
        pesos = [res['params']['peso_hora'][h] for h in horas]
        ax.plot(horas, pesos, 'o--', label=nome, 
               linewidth=2, markersize=6, alpha=0.7, color=cores[i % len(cores)])
    
    ax.axhline(0, color='black', linestyle=':', linewidth=1)
    ax.set_xlabel('Hora do Dia', fontsize=13, fontweight='bold')
    ax.set_ylabel('Peso Horário', fontsize=13, fontweight='bold')
    ax.set_title('Comparação de Pesos Horários: Original vs Calibrados', 
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=11, loc='best')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparacao_pesos_horarios.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print("  [OK] comparacao_pesos_horarios.png")

def salvar_parametros_recomendados(resultados):
    """Salva os melhores parâmetros encontrados."""
    
    print("\n" + "="*80)
    print("  SALVANDO PARÂMETROS RECOMENDADOS")
    print("="*80 + "\n")
    
    # Encontrar melhor modelo (menor MAE)
    melhor_nome = min(resultados.keys(), 
                     key=lambda k: resultados[k]['metricas']['mae'])
    melhor_params = resultados[melhor_nome]['params']
    
    print(f"Melhor modelo: {melhor_nome}")
    print(f"MAE: {resultados[melhor_nome]['metricas']['mae']:,.0f} MW")
    print(f"MAPE: {resultados[melhor_nome]['metricas']['mape']:.2f}%")
    print(f"R²: {resultados[melhor_nome]['metricas']['r2']:.4f}")
    
    # Salvar em formato Python
    output_file = OUTPUT_DIR / 'parametros_calibrados_recomendados.py'
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('Parâmetros Calibrados RECOMENDADOS para Modelo Hidro FD\n')
        f.write('========================================================\n\n')
        f.write(f'Método de calibração: {melhor_nome}\n')
        f.write(f'MAE: {resultados[melhor_nome]["metricas"]["mae"]:,.0f} MW\n')
        f.write(f'MAPE: {resultados[melhor_nome]["metricas"]["mape"]:.2f}%\n')
        f.write(f'R²: {resultados[melhor_nome]["metricas"]["r2"]:.4f}\n')
        f.write('\nPara usar no mini_dessem, copie o dicionário abaixo para config.py\n')
        f.write('"""\n\n')
        
        f.write('REGRESSION_PARAMS_CALIBRADO = {\n')
        f.write(f"    'intercept': {melhor_params['intercept']},\n")
        f.write(f"    'ghr': {melhor_params['ghr']},\n")
        f.write(f"    'ena': {melhor_params['ena']},\n")
        
        # peso_mes
        f.write("    'peso_mes': {\n")
        for mes in range(1, 13):
            f.write(f"        {mes}: {melhor_params['peso_mes'][mes]:.0f},\n")
        f.write("    },\n")
        
        # peso_hora
        f.write("    'peso_hora': {\n")
        for hora in range(24):
            f.write(f"        {hora}: {melhor_params['peso_hora'][hora]:.2f},\n")
        f.write("    },\n")
        
        f.write(f"    'peso_weekday': {melhor_params['peso_weekday']},\n")
        f.write(f"    'peso_fds': {melhor_params['peso_fds']}\n")
        f.write('}\n')
    
    print(f"\n  [OK] Parâmetros salvos em: parametros_calibrados_recomendados.py")
    
    # Também salvar comparação em CSV
    df_comp = pd.DataFrame([
        {
            'modelo': nome,
            'mae': res['metricas']['mae'],
            'rmse': res['metricas']['rmse'],
            'mape': res['metricas']['mape'],
            'bias': res['metricas']['bias'],
            'r2': res['metricas']['r2']
        }
        for nome, res in resultados.items()
    ])
    
    df_comp.to_csv(OUTPUT_DIR / 'comparacao_modelos.csv', index=False)
    print("  [OK] Comparação salva em: comparacao_modelos.csv")

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  CALIBRAÇÃO DE PARÂMETROS HIDRO FD")
    print("="*80)
    
    # Carregar dados
    df = carregar_dados_completos()
    
    # Analisar erro por hora
    erro_por_hora, df = analisar_erro_por_hora(df)
    
    # Testar diferentes métodos de calibração
    params_v1 = calibrar_parametros_hora_regressao(df)
    params_v2 = calibrar_parametros_hora_otimizacao(df)
    params_v3 = calibrar_parametros_hora_suavizado(df, fator_suavizacao=0.7)
    
    # Comparar modelos
    params_dict = {
        'Original': PARAMS_ORIGINAIS,
        'Calibrado V1 (Ajuste Erro)': params_v1,
        'Calibrado V2 (Otimização)': params_v2,
        'Calibrado V3 (Suavizado 70%)': params_v3
    }
    
    resultados = comparar_modelos(df, params_dict)
    
    # Gerar gráficos
    gerar_graficos_comparacao(df, resultados)
    
    # Salvar parâmetros recomendados
    salvar_parametros_recomendados(resultados)
    
    print("\n" + "="*80)
    print("  CALIBRAÇÃO CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados salvos em: {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    for arquivo in sorted(OUTPUT_DIR.glob('*')):
        print(f"  - {arquivo.name}")
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()





