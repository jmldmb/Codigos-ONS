"""
Análise de Carga Energética - ONS
Script baseado no notebook estável Carga.ipynb
Foco: 2 gráficos principais
1. Comparativa horária para períodos de datas selecionadas
2. Comparação YoY com médias trimestrais (anos configuráveis)
"""

import os
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import yaml

def load_config():
    """Carrega configurações do arquivo YAML"""
    config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def download_data(config):
    """Baixa dados do ONS"""
    print("Baixando dados do ONS...")
    
    # Criar pasta se não existir
    raw_data_folder = os.path.join(os.path.dirname(__file__), config['directories']['raw_data'])
    if not os.path.exists(raw_data_folder):
        os.makedirs(raw_data_folder)
    
    # Anos para baixar (baseado na configuração YoY + ano anterior para comparação horária)
    current_year = config['charts']['yoy_growth']['year1']
    previous_year = config['charts']['yoy_growth']['year2']
    two_years_ago = previous_year - 1  # Para ter dados do ano anterior para comparação horária
    
    years_to_download = [current_year, previous_year, two_years_ago]
    
    # URLs para diferentes tipos de dados
    urls = {
        'daily': config['data_sources']['base_url'].format('{}'),
        'hourly': "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/curva-carga-ho/CURVA_CARGA_{}.csv"
    }
    
    # Baixar dados dos anos configurados
    for year in years_to_download:
        # Baixar dados diários
        daily_url = urls['daily'].format(year)
        daily_file_path = os.path.join(raw_data_folder, f"CARGA_ENERGIA_{year}.csv")
        
        try:
            print(f"Baixando dados diários de {year}...")
            response = requests.get(daily_url, verify=False)
            
            if response.status_code == 200:
                with open(daily_file_path, 'wb') as file:
                    file.write(response.content)
                print(f"✓ Dados diários de {year} baixados com sucesso!")
            else:
                print(f"✗ Falha ao baixar dados diários de {year}. Status: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Erro ao baixar dados diários de {year}: {e}")
        
        # Baixar dados horários
        hourly_url = urls['hourly'].format(year)
        hourly_file_path = os.path.join(raw_data_folder, f"CURVA_CARGA_{year}.csv")
        
        try:
            print(f"Baixando dados horários de {year}...")
            response = requests.get(hourly_url, verify=False)
            
            if response.status_code == 200:
                with open(hourly_file_path, 'wb') as file:
                    file.write(response.content)
                print(f"✓ Dados horários de {year} baixados com sucesso!")
            else:
                print(f"✗ Falha ao baixar dados horários de {year}. Status: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Erro ao baixar dados horários de {year}: {e}")

def load_and_process_data(config):
    """Carrega e processa os dados"""
    print("Carregando e processando dados...")
    
    # Caminho para pasta de dados
    raw_data_folder = os.path.join(os.path.dirname(__file__), config['directories']['raw_data'])
    
    # Listar arquivos CSV de curva de carga (dados horários)
    csv_files_hourly = [f for f in os.listdir(raw_data_folder) 
                        if f.startswith('CURVA_CARGA_') and f.endswith('.csv')]
    
    # Listar arquivos CSV de carga diária
    csv_files_daily = [f for f in os.listdir(raw_data_folder) 
                       if f.startswith('CARGA_ENERGIA_') and f.endswith('.csv')]
    
    if not csv_files_hourly:
        print("✗ Nenhum arquivo de dados horários encontrado!")
        return None
    
    if not csv_files_daily:
        print("✗ Nenhum arquivo de dados diários encontrado!")
        return None
    
    # Carregar dados horários para gráfico de comparação horária
    print("Carregando dados horários...")
    dfs_hourly = []
    for file in csv_files_hourly:
        file_path = os.path.join(raw_data_folder, file)
        print(f"Carregando arquivo horário: {file}")
        df = pd.read_csv(file_path, sep=';')
        print(f"  - Registros: {len(df)}")
        dfs_hourly.append(df)
    
    # Carregar dados diários para gráfico YoY
    print("Carregando dados diários...")
    dfs_daily = []
    for file in csv_files_daily:
        file_path = os.path.join(raw_data_folder, file)
        print(f"Carregando arquivo diário: {file}")
        df = pd.read_csv(file_path, sep=';')
        print(f"  - Registros: {len(df)}")
        dfs_daily.append(df)
    
    # Consolidar dados horários
    consolidated_hourly = pd.concat(dfs_hourly, ignore_index=True)
    print(f"Total de registros horários consolidados: {len(consolidated_hourly)}")
    
    # Consolidar dados diários
    consolidated_daily = pd.concat(dfs_daily, ignore_index=True)
    print(f"Total de registros diários consolidados: {len(consolidated_daily)}")
    
    # Processar dados horários
    grouped_hourly = consolidated_hourly.groupby('din_instante')['val_cargaenergiahomwmed'].sum().reset_index()
    grouped_hourly['din_instante'] = pd.to_datetime(grouped_hourly['din_instante'])
    
    # Adicionar colunas úteis para dados horários
    grouped_hourly['year'] = grouped_hourly['din_instante'].dt.year
    grouped_hourly['day_of_year'] = grouped_hourly['din_instante'].dt.dayofyear
    grouped_hourly['hour'] = grouped_hourly['din_instante'].dt.hour
    grouped_hourly['date'] = grouped_hourly['din_instante'].dt.date
    grouped_hourly['month'] = grouped_hourly['din_instante'].dt.month
    grouped_hourly['quarter'] = grouped_hourly['din_instante'].dt.quarter
    
    # Processar dados diários
    grouped_daily = consolidated_daily.groupby('din_instante')['val_cargaenergiamwmed'].sum().reset_index()
    grouped_daily['din_instante'] = pd.to_datetime(grouped_daily['din_instante'])
    
    # Adicionar colunas úteis para dados diários
    grouped_daily['year'] = grouped_daily['din_instante'].dt.year
    grouped_daily['day_of_year'] = grouped_daily['din_instante'].dt.dayofyear
    grouped_daily['date'] = grouped_daily['din_instante'].dt.date
    grouped_daily['month'] = grouped_daily['din_instante'].dt.month
    grouped_daily['quarter'] = grouped_daily['din_instante'].dt.quarter
    
    # Verificar distribuição de horas
    print(f"Distribuição de horas: {grouped_hourly['hour'].value_counts().sort_index().to_dict()}")
    
    # Remover valores zero se configurado
    if config['processing']['remove_zeros']:
        grouped_hourly = grouped_hourly[grouped_hourly['val_cargaenergiahomwmed'] > 0]
        grouped_daily = grouped_daily[grouped_daily['val_cargaenergiamwmed'] > 0]
    
    print(f"✓ Dados horários processados: {len(grouped_hourly)} registros")
    print(f"✓ Dados diários processados: {len(grouped_daily)} registros")
    
    # Retornar ambos os datasets
    return {
        'hourly': grouped_hourly,
        'daily': grouped_daily
    }

def plot_hourly_comparison(df, config):
    """Gráfico 1: Comparativa horária para períodos selecionados com médias diárias"""
    if not config['charts']['hourly_comparison']['enabled']:
        print("⚠️ Gráfico de comparação horária desabilitado na configuração")
        return
    
    print("Gerando gráfico de comparação horária...")
    
    # Criar pasta de saída
    output_folder = os.path.join(os.path.dirname(__file__), config['directories']['output_charts'])
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Lógica para determinar as datas de comparação
    unique_dates = sorted(df['hourly']['date'].unique())
    
    if len(unique_dates) < 2:
        print("✗ Não há dados suficientes para comparação horária")
        return
    
    # Encontrar o último dia disponível
    latest_date = unique_dates[-1]
    
    # Calcular o mesmo dia do ano anterior
    latest_date_dt = pd.to_datetime(latest_date)
    previous_year_date = latest_date_dt.replace(year=latest_date_dt.year - 1).date()
    
    # Verificar se temos dados para o mesmo dia do ano anterior
    if previous_year_date in unique_dates:
        period1 = str(latest_date)
        period2 = str(previous_year_date)
        print(f"Comparando: {period1} (último dia disponível) vs {period2} (mesmo dia ano anterior)")
    else:
        # Se não temos o mesmo dia do ano anterior, usar as duas últimas datas disponíveis
        period1 = str(unique_dates[-2])
        period2 = str(unique_dates[-1])
        print(f"⚠️ Mesmo dia do ano anterior não encontrado. Usando últimas duas datas: {period1} vs {period2}")
    
    # Filtrar dados das datas selecionadas
    data1 = df['hourly'][df['hourly']['date'] == pd.to_datetime(period1).date()]
    data2 = df['hourly'][df['hourly']['date'] == pd.to_datetime(period2).date()]
    
    # Debug: verificar se há dados
    print(f"Dados encontrados para {period1}: {len(data1)} registros")
    print(f"Dados encontrados para {period2}: {len(data2)} registros")
    
    if data1.empty or data2.empty:
        print("✗ Não há dados suficientes para comparação horária")
        return
    
    # Ordenar dados por hora
    data1 = data1.sort_values('hour')
    data2 = data2.sort_values('hour')
    
    # Verificar se há dados para todas as horas
    print(f"Horas disponíveis para {period1}: {sorted(data1['hour'].unique())}")
    print(f"Horas disponíveis para {period2}: {sorted(data2['hour'].unique())}")
    
    # Calcular médias diárias
    media1 = data1['val_cargaenergiahomwmed'].mean()
    media2 = data2['val_cargaenergiahomwmed'].mean()
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plotar dados horários reais
    ax.plot(data1['hour'], data1['val_cargaenergiahomwmed'], 
            label=f'{period1}', linewidth=2, marker='o', color='blue')
    ax.plot(data2['hour'], data2['val_cargaenergiahomwmed'], 
            label=f'{period2}', linewidth=2, marker='s', color='orange')
    
    # Plotar médias diárias como linhas horizontais tracejadas
    ax.axhline(y=media1, color='blue', linestyle='--', alpha=0.7, 
               label=f'Média {period1}: {media1:.1f} MW')
    ax.axhline(y=media2, color='orange', linestyle='--', alpha=0.7, 
               label=f'Média {period2}: {media2:.1f} MW')
    
    ax.set_xlabel('Hora do dia')
    ax.set_ylabel('Carga (MW médios)')
    ax.set_title('Comparativo de Carga Horária com Médias Diárias')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Configurar eixo X para mostrar todas as horas
    ax.set_xticks(range(0, 24))
    
    # Salvar gráfico
    filename = f"comparacao_horaria.{config['output']['format']}"
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath, dpi=config['output']['dpi'], bbox_inches='tight')
    plt.close()
    
    print(f"✓ Gráfico salvo: {filepath}")

def plot_yoy_comparison(df, config):
    """Gráfico 2: Comparação YoY apenas com crescimento percentual e médias trimestrais"""
    if not config['charts']['yoy_growth']['enabled']:
        print("⚠️ Gráfico de crescimento YoY desabilitado na configuração")
        return
    
    print("Gerando gráfico de comparação YoY...")
    
    # Criar pasta de saída
    output_folder = os.path.join(os.path.dirname(__file__), config['directories']['output_charts'])
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    # Obter configurações
    year1 = config['charts']['yoy_growth']['year1']
    year2 = config['charts']['yoy_growth']['year2']
    window = config['charts']['yoy_growth']['moving_average_window']
    
    # Filtrar dados dos anos configurados
    df_filtered = df['daily'][df['daily']['year'].isin([year1, year2])]
    
    if df_filtered.empty:
        print("✗ Não há dados para os anos configurados")
        return
    
    # Separar dados por ano
    df_year1 = df_filtered[df_filtered['year'] == year1]
    df_year2 = df_filtered[df_filtered['year'] == year2]
    
    # Encontrar dias em comum
    common_days = set(df_year1['day_of_year']).intersection(set(df_year2['day_of_year']))
    
    if len(common_days) == 0:
        print("✗ Não há dias em comum entre os anos")
        return
    
    # Filtrar dados comuns
    df_year1_common = df_year1[df_year1['day_of_year'].isin(common_days)].set_index('day_of_year')
    df_year2_common = df_year2[df_year2['day_of_year'].isin(common_days)].set_index('day_of_year')
    
    # Calcular médias móveis
    df_year1_common['moving_avg'] = df_year1_common['val_cargaenergiamwmed'].rolling(window=window).mean()
    df_year2_common['moving_avg'] = df_year2_common['val_cargaenergiamwmed'].rolling(window=window).mean()
    
    # Remover valores zero antes de calcular o crescimento
    df_year1_common = df_year1_common[df_year1_common['moving_avg'] > 0]
    df_year2_common = df_year2_common[df_year2_common['moving_avg'] > 0]
    
    # Encontrar dias em comum após remoção de zeros
    common_days_clean = df_year1_common.index.intersection(df_year2_common.index)
    
    if len(common_days_clean) == 0:
        print("✗ Não há dados válidos para comparação")
        return
    
    # Filtrar dados finais
    df_year1_final = df_year1_common.loc[common_days_clean]
    df_year2_final = df_year2_common.loc[common_days_clean]
    
    # Calcular crescimento YoY
    growth = ((df_year1_final['moving_avg'] - df_year2_final['moving_avg']) / 
              df_year2_final['moving_avg']) * 100
    
    # Calcular médias trimestrais do crescimento
    growth_df = pd.DataFrame({
        'day_of_year': growth.index,
        'growth_percent': growth.values,
        'quarter': pd.to_datetime(f'{year1}-01-01') + pd.to_timedelta(growth.index - 1, unit='D')
    })
    growth_df['quarter'] = growth_df['quarter'].dt.quarter
    
    # Calcular médias por trimestre
    quarterly_means = growth_df.groupby('quarter')['growth_percent'].mean()
    
    # Obter a data do último valor disponível
    last_day_of_year = growth.index.max()
    # Converter dia do ano para data usando uma abordagem mais segura
    last_date = pd.to_datetime(f'{year1}-01-01') + pd.Timedelta(days=int(last_day_of_year) - 1)
    last_date_str = last_date.strftime('%d/%m/%Y')
    
    # Criar gráfico
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Plotar crescimento YoY
    ax.plot(growth.index, growth, label=f'Crescimento {year1} vs {year2} (Média Móvel {window} dias)', 
            linewidth=2, color='red')
    
    # Plotar médias trimestrais apenas no período do trimestre
    colors = ['blue', 'green', 'purple', 'brown']
    for quarter, mean_value in quarterly_means.items():
        if not pd.isna(mean_value):
            # Filtrar dados do trimestre
            quarter_data = growth_df[growth_df['quarter'] == quarter]
            if not quarter_data.empty:
                quarter_start = quarter_data['day_of_year'].min()
                quarter_end = quarter_data['day_of_year'].max()
                
                # Plotar linha horizontal apenas no período do trimestre
                ax.hlines(y=mean_value, xmin=quarter_start, xmax=quarter_end, 
                         color=colors[quarter-1], linestyle='--', alpha=0.7,
                         label=f'Q{quarter} mean = {mean_value:.1f}%')
    
    ax.set_xlabel('Dia do Ano')
    ax.set_ylabel('Crescimento (%)')
    ax.set_title(f'Demanda Energética - Crescimento YoY ({year1} vs {year2}) - Última data: {last_date_str}')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Salvar gráfico
    filename = f"crescimento_yoy_{year1}_vs_{year2}.{config['output']['format']}"
    filepath = os.path.join(output_folder, filename)
    plt.savefig(filepath, dpi=config['output']['dpi'], bbox_inches='tight')
    plt.close()
    
    print(f"✓ Gráfico salvo: {filepath}")

def main():
    """Função principal"""
    print("=== ANÁLISE DE CARGA ENERGÉTICA - ONS ===")
    
    # Carregar configuração
    config = load_config()
    
    print(f"Anos para comparação YoY: {config['charts']['yoy_growth']['year1']} vs {config['charts']['yoy_growth']['year2']}")
    print("Períodos para comparação horária: Último dia disponível vs mesmo dia ano anterior")
    print()
    
    # 1. Baixar dados
    download_data(config)
    print()
    
    # 2. Carregar e processar dados
    df = load_and_process_data(config)
    if df is None:
        print("✗ Erro ao carregar dados. Encerrando...")
        return
    print()
    
    # 3. Gerar gráfico de comparação horária
    plot_hourly_comparison(df, config)
    print()
    
    # 4. Gerar gráfico de comparação YoY
    plot_yoy_comparison(df, config)
    print()
    
    print("=== ANÁLISE CONCLUÍDA ===")

if __name__ == "__main__":
    main() 