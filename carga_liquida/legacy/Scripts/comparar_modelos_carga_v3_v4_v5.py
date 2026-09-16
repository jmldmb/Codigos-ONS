"""
Comparação de Modelos de Carga: V3 vs V4 vs V5
================================================

Compara o desempenho dos três modelos em dados históricos.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
import warnings
warnings.filterwarnings('ignore')

# Adicionar path para importar modelos
sys.path.insert(0, str(Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem\Scripts\src")))

from auxiliar.sample.carga.carga_model_v3 import sample_day_v2, fit_stage1_monthly_to_daily, fit_stage2_daily_to_hourly, _load_temperatura as load_temp_v3
from auxiliar.sample.carga.carga_model_v4 import sample_day_v4
from auxiliar.sample.carga.carga_model_v5 import sample_day_v5, fit_modelo_v5

# Configuração visual
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (18, 12)
plt.rcParams['font.size'] = 10

CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "comparacao_modelos"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def carregar_dados_reais():
    """Carrega dados reais para validação."""
    
    print("\n[1/4] Carregando dados reais...")
    
    path = CARGA_LIQ_DIR / "Output" / "analise_completa" / "comparacao_completa.csv"
    df = pd.read_csv(path)
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Usar carga_real
    if 'carga_real' in df.columns:
        df['carga'] = df['carga_real']
    else:
        df['carga'] = df['carga_bruta_real']
    
    # Features
    df['hora'] = df['din_instante'].dt.hour
    df['mes'] = df['din_instante'].dt.month
    df['ano'] = df['din_instante'].dt.year
    df['dia'] = df['din_instante'].dt.day
    df['data'] = df['din_instante'].dt.date
    
    print(f"     Registros: {len(df):,}")
    print(f"     Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    
    return df

def carregar_modelos():
    """Carrega e treina os 3 modelos."""
    
    print("\n[2/4] Carregando modelos...")
    
    # V3
    print("     [V3] Carregando...")
    s1_v3 = fit_stage1_monthly_to_daily()
    s2_profiles_v3, s2_ar_v3 = fit_stage2_daily_to_hourly()
    temp_v3 = load_temp_v3()
    print("     [V3] OK")
    
    # V4 usa mesmos parâmetros que v3
    print("     [V4] Carregando...")
    s1_v4 = s1_v3
    s2_profiles_v4 = s2_profiles_v3
    s2_ar_v4 = s2_ar_v3
    temp_v4 = temp_v3
    print("     [V4] OK")
    
    # V5
    print("     [V5] Treinando modelo híbrido...")
    perfis_v5, temp_v5, params_v5 = fit_modelo_v5()
    print("     [V5] OK")
    
    return {
        'v3': (s1_v3, s2_profiles_v3, s2_ar_v3, temp_v3),
        'v4': (s1_v4, s2_profiles_v4, s2_ar_v4, temp_v4),
        'v5': (perfis_v5, temp_v5, params_v5)
    }

def gerar_previsoes_amostra(df_real, modelos, n_dias=100):
    """Gera previsões para uma amostra de dias."""
    
    print(f"\n[3/4] Gerando previsões para {n_dias} dias...")
    
    # Selecionar amostra aleatória de dias
    dias_unicos = df_real['data'].unique()
    np.random.seed(42)
    dias_amostra = np.random.choice(dias_unicos, size=min(n_dias, len(dias_unicos)), replace=False)
    
    # Filtrar dados reais
    df_amostra = df_real[df_real['data'].isin(dias_amostra)].copy()
    
    resultados = []
    
    for i, data in enumerate(dias_amostra):
        if (i + 1) % 20 == 0:
            print(f"     Processando dia {i+1}/{len(dias_amostra)}...")
        
        ts = pd.Timestamp(data)
        ano, mes, dia = ts.year, ts.month, ts.day
        
        # Dados reais do dia
        df_dia_real = df_amostra[df_amostra['data'] == data].sort_values('hora')
        
        if len(df_dia_real) != 24:
            continue
        
        carga_real = df_dia_real['carga'].values
        
        try:
            # V3
            s1, s2_prof, s2_ar, temp = modelos['v3']
            carga_mes = df_real[df_real['mes'] == mes]['carga'].mean()
            carga_mes_lag = carga_mes * 0.98
            temp_mes = temp[temp['timestamp'].dt.month == mes]
            temp_media = temp_mes['temp_brasil_c'].mean() if len(temp_mes) > 0 else 25.0
            temp_max = temp_mes['temp_brasil_c'].max() if len(temp_mes) > 0 else 30.0
            
            df_v3 = sample_day_v2(
                carga_mes, carga_mes_lag, temp_media, temp_max,
                ano, mes, dia, s1, s2_prof, s2_ar, seed=42
            )
            carga_v3 = df_v3['val_carga'].values
            
            # V4
            s1, s2_prof, s2_ar, temp = modelos['v4']
            df_v4 = sample_day_v4(
                carga_mes, carga_mes_lag, temp_media, temp_max,
                ano, mes, dia, s1, s2_prof, s2_ar, seed=42
            )
            carga_v4 = df_v4['val_carga'].values
            
            # V5
            perfis, temp, params = modelos['v5']
            df_v5 = sample_day_v5(
                ano, mes, dia, perfis, temp, params, seed=42
            )
            carga_v5 = df_v5['val_carga'].values
            
            # Calcular erros
            erro_v3 = carga_v3 - carga_real
            erro_v4 = carga_v4 - carga_real
            erro_v5 = carga_v5 - carga_real
            
            # Armazenar
            for h in range(24):
                resultados.append({
                    'data': data,
                    'ano': ano,
                    'mes': mes,
                    'dia': dia,
                    'hora': h,
                    'carga_real': carga_real[h],
                    'carga_v3': carga_v3[h],
                    'carga_v4': carga_v4[h],
                    'carga_v5': carga_v5[h],
                    'erro_v3': erro_v3[h],
                    'erro_v4': erro_v4[h],
                    'erro_v5': erro_v5[h],
                })
                
        except Exception as e:
            print(f"     [!] Erro no dia {data}: {e}")
            continue
    
    df_resultados = pd.DataFrame(resultados)
    
    print(f"     [OK] {len(df_resultados)} registros gerados")
    
    return df_resultados

def analise_comparativa(df):
    """Análise comparativa dos 3 modelos."""
    
    print("\n[4/4] Análise comparativa...")
    
    # Métricas globais
    mae_v3 = df['erro_v3'].abs().mean()
    mae_v4 = df['erro_v4'].abs().mean()
    mae_v5 = df['erro_v5'].abs().mean()
    
    rmse_v3 = np.sqrt((df['erro_v3']**2).mean())
    rmse_v4 = np.sqrt((df['erro_v4']**2).mean())
    rmse_v5 = np.sqrt((df['erro_v5']**2).mean())
    
    bias_v3 = df['erro_v3'].mean()
    bias_v4 = df['erro_v4'].mean()
    bias_v5 = df['erro_v5'].mean()
    
    print(f"\n{'='*80}")
    print(f"  MÉTRICAS GLOBAIS")
    print(f"{'='*80}")
    print(f"\n{'Modelo':>10} | {'MAE (MW)':>12} | {'RMSE (MW)':>12} | {'Viés (MW)':>12} | {'vs V4':>10}")
    print("-" * 75)
    print(f"{'V3':>10} | {mae_v3:12,.0f} | {rmse_v3:12,.0f} | {bias_v3:+12,.0f} | {(mae_v3/mae_v4-1)*100:+9.1f}%")
    print(f"{'V4':>10} | {mae_v4:12,.0f} | {rmse_v4:12,.0f} | {bias_v4:+12,.0f} |")
    print(f"{'V5':>10} | {mae_v5:12,.0f} | {rmse_v5:12,.0f} | {bias_v5:+12,.0f} | {(mae_v5/mae_v4-1)*100:+9.1f}%")
    
    # Métricas por hora
    print(f"\n{'='*80}")
    print(f"  ERRO POR HORA DO DIA")
    print(f"{'='*80}")
    print(f"\n{'Hora':>4} | {'MAE V3':>10} | {'MAE V4':>10} | {'MAE V5':>10} | {'V5 vs V4':>12}")
    print("-" * 60)
    
    for h in range(24):
        df_h = df[df['hora'] == h]
        mae_v3_h = df_h['erro_v3'].abs().mean()
        mae_v4_h = df_h['erro_v4'].abs().mean()
        mae_v5_h = df_h['erro_v5'].abs().mean()
        melhoria = (mae_v5_h / mae_v4_h - 1) * 100
        
        print(f"{h:4d} | {mae_v3_h:10,.0f} | {mae_v4_h:10,.0f} | {mae_v5_h:10,.0f} | {melhoria:+11.1f}%")
    
    # Gráficos
    gerar_graficos_comparacao(df, mae_v3, mae_v4, mae_v5)

def gerar_graficos_comparacao(df, mae_v3, mae_v4, mae_v5):
    """Gera gráficos de comparação."""
    
    print("\n     Gerando gráficos...")
    
    # Gráfico 1: Métricas globais
    fig, axes = plt.subplots(2, 3, figsize=(18, 12))
    fig.suptitle('Comparação Modelos V3 vs V4 vs V5', fontsize=16, fontweight='bold', y=0.995)
    
    # 1.1: MAE por modelo
    ax = axes[0, 0]
    modelos = ['V3', 'V4', 'V5']
    maes = [mae_v3, mae_v4, mae_v5]
    cores = ['lightblue', 'orange', 'lightgreen']
    bars = ax.bar(modelos, maes, color=cores, alpha=0.8, edgecolor='black', linewidth=2)
    ax.set_ylabel('MAE (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Absoluto Médio', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    
    for bar, val in zip(bars, maes):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:,.0f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    # 1.2: Erro por hora - V3
    ax = axes[0, 1]
    erro_v3_hora = df.groupby('hora')['erro_v3'].mean()
    ax.bar(range(24), erro_v3_hora.values, alpha=0.8, color='lightblue', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'V3: Erro por Hora\nMAE = {mae_v3:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 4))
    
    # 1.3: Erro por hora - V4
    ax = axes[0, 2]
    erro_v4_hora = df.groupby('hora')['erro_v4'].mean()
    ax.bar(range(24), erro_v4_hora.values, alpha=0.8, color='orange', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'V4: Erro por Hora\nMAE = {mae_v4:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 4))
    
    # 1.4: Erro por hora - V5
    ax = axes[1, 0]
    erro_v5_hora = df.groupby('hora')['erro_v5'].mean()
    ax.bar(range(24), erro_v5_hora.values, alpha=0.8, color='lightgreen', edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('Erro (MW)', fontsize=11, fontweight='bold')
    ax.set_title(f'V5: Erro por Hora\nMAE = {mae_v5:,.0f} MW', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 4))
    
    # 1.5: Comparação MAE por hora
    ax = axes[1, 1]
    x = np.arange(24)
    width = 0.25
    mae_v3_h = df.groupby('hora')['erro_v3'].apply(lambda x: x.abs().mean())
    mae_v4_h = df.groupby('hora')['erro_v4'].apply(lambda x: x.abs().mean())
    mae_v5_h = df.groupby('hora')['erro_v5'].apply(lambda x: x.abs().mean())
    
    ax.bar(x - width, mae_v3_h.values, width, label='V3', alpha=0.8, color='lightblue', edgecolor='black')
    ax.bar(x, mae_v4_h.values, width, label='V4', alpha=0.8, color='orange', edgecolor='black')
    ax.bar(x + width, mae_v5_h.values, width, label='V5', alpha=0.8, color='lightgreen', edgecolor='black')
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('MAE (MW)', fontsize=11, fontweight='bold')
    ax.set_title('Comparação: MAE por Hora', fontsize=12, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 4))
    
    # 1.6: Melhoria percentual V5 vs V4
    ax = axes[1, 2]
    melhoria = ((mae_v5_h - mae_v4_h) / mae_v4_h * 100).values
    cores_melhoria = ['green' if m < 0 else 'red' for m in melhoria]
    ax.bar(range(24), melhoria, color=cores_melhoria, alpha=0.8, edgecolor='black')
    ax.axhline(0, color='black', linestyle='-', linewidth=2)
    ax.set_xlabel('Hora', fontsize=11, fontweight='bold')
    ax.set_ylabel('Melhoria V5 vs V4 (%)', fontsize=11, fontweight='bold')
    ax.set_title('Melhoria Percentual por Hora', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 4))
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'comparacao_v3_v4_v5.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     [OK] comparacao_v3_v4_v5.png")
    
    # Gráfico 2: Distribuições de erro
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle('Distribuição dos Erros', fontsize=16, fontweight='bold')
    
    for i, (modelo, erro_col, cor) in enumerate([
        ('V3', 'erro_v3', 'lightblue'),
        ('V4', 'erro_v4', 'orange'),
        ('V5', 'erro_v5', 'lightgreen')
    ]):
        ax = axes[i]
        ax.hist(df[erro_col], bins=50, alpha=0.7, color=cor, edgecolor='black')
        ax.axvline(0, color='red', linestyle='--', linewidth=2)
        ax.axvline(df[erro_col].mean(), color='green', linestyle='--', linewidth=2,
                   label=f'Média = {df[erro_col].mean():.0f} MW')
        ax.set_xlabel('Erro (MW)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Frequência', fontsize=11, fontweight='bold')
        ax.set_title(f'{modelo}: MAE = {df[erro_col].abs().mean():,.0f} MW', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'distribuicao_erros_v3_v4_v5.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"     [OK] distribuicao_erros_v3_v4_v5.png")

def main():
    """Executa comparação completa."""
    
    print("\n" + "="*80)
    print("  COMPARAÇÃO DE MODELOS: V3 vs V4 vs V5")
    print("="*80)
    
    df_real = carregar_dados_reais()
    modelos = carregar_modelos()
    df_resultados = gerar_previsoes_amostra(df_real, modelos, n_dias=100)
    
    # Salvar resultados
    csv_path = OUTPUT_DIR / "resultados_comparacao_v3_v4_v5.csv"
    df_resultados.to_csv(csv_path, index=False)
    print(f"\n[OK] Resultados salvos: {csv_path}")
    
    analise_comparativa(df_resultados)
    
    print("\n" + "="*80)
    print("  COMPARAÇÃO CONCLUÍDA!")
    print("="*80)
    print(f"\nResultados em: {OUTPUT_DIR}")
    print("\nArquivos gerados:")
    print("  - resultados_comparacao_v3_v4_v5.csv")
    print("  - comparacao_v3_v4_v5.png")
    print("  - distribuicao_erros_v3_v4_v5.png")
    
    print("\n[OK] Análise concluída!")

if __name__ == "__main__":
    main()






