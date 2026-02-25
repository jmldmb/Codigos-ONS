"""
Gráficos Scatter: Carga Líquida vs Curtailment - Separados por Mês
====================================================================

Gera 12 gráficos scatter (um para cada mês) mostrando a relação entre
carga líquida e curtailment para o ano de 2025.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import calendar

# Configuração
sns.set_style('whitegrid')
plt.rcParams['figure.figsize'] = (10, 8)

# Diretórios
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")
INPUT_FILE = CARGA_LIQ_DIR / "Output" / "analise_carga_curtailment" / "carga_curtailment_merged.csv"
OUTPUT_DIR = CARGA_LIQ_DIR / "Output" / "analise_carga_curtailment" / "scatter_por_mes"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

# Ano de interesse
ANO = 2025

def carregar_dados():
    """Carrega dados do CSV."""
    print(f"\n{'='*80}")
    print(f"  CARREGANDO DADOS")
    print(f"{'='*80}\n")
    
    print(f"Lendo arquivo: {INPUT_FILE.name}")
    df = pd.read_csv(INPUT_FILE)
    
    # Converter din_instante para datetime
    df['din_instante'] = pd.to_datetime(df['din_instante'])
    
    # Garantir que as colunas estão em formato numérico
    df['carga_liq_mw'] = pd.to_numeric(df['carga_liq_mw'], errors='coerce')
    df['curtailment_mw'] = pd.to_numeric(df['curtailment_mw'], errors='coerce')
    df['ano'] = pd.to_numeric(df['ano'], errors='coerce')
    df['mes'] = pd.to_numeric(df['mes'], errors='coerce')
    
    print(f"Total de registros: {len(df):,}")
    print(f"Período: {df['din_instante'].min()} até {df['din_instante'].max()}")
    
    return df

def filtrar_ano(df, ano):
    """Filtra dados para um ano específico."""
    df_ano = df[df['ano'] == ano].copy()
    
    if len(df_ano) == 0:
        print(f"\n[AVISO] Nenhum dado encontrado para o ano {ano}")
        return None
    
    print(f"\nDados para {ano}:")
    print(f"  Registros: {len(df_ano):,}")
    print(f"  Carga Líquida - Média: {df_ano['carga_liq_mw'].mean():,.0f} MW")
    print(f"  Curtailment - Média: {df_ano['curtailment_mw'].mean():,.2f} MW")
    print(f"  Meses disponíveis: {sorted(df_ano['mes'].unique())}")
    
    return df_ano

def gerar_scatter_por_mes(df_ano, ano):
    """Gera 12 gráficos scatter, um para cada mês."""
    
    print(f"\n{'='*80}")
    print(f"  GERANDO GRÁFICOS POR MÊS - {ano}")
    print(f"{'='*80}\n")
    
    # Nomes dos meses em português
    meses_pt = {
        1: 'Janeiro', 2: 'Fevereiro', 3: 'Março', 4: 'Abril',
        5: 'Maio', 6: 'Junho', 7: 'Julho', 8: 'Agosto',
        9: 'Setembro', 10: 'Outubro', 11: 'Novembro', 12: 'Dezembro'
    }
    
    graficos_gerados = 0
    
    for mes in range(1, 13):
        # Filtrar dados do mês
        df_mes = df_ano[df_ano['mes'] == mes].copy()
        
        if len(df_mes) == 0:
            print(f"  [{mes:02d}] {meses_pt[mes]:<12} - Sem dados disponíveis")
            continue
        
        # Remover valores NaN
        df_mes = df_mes.dropna(subset=['carga_liq_mw', 'curtailment_mw'])
        
        if len(df_mes) == 0:
            print(f"  [{mes:02d}] {meses_pt[mes]:<12} - Sem dados válidos")
            continue
        
        # Criar figura
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Scatter plot
        scatter = ax.scatter(
            df_mes['carga_liq_mw'],
            df_mes['curtailment_mw'],
            c=df_mes['hora'],  # Cor baseada na hora
            cmap='viridis',
            alpha=0.6,
            s=50,
            edgecolors='k',
            linewidth=0.5
        )
        
        # Colorbar
        cbar = plt.colorbar(scatter, ax=ax)
        cbar.set_label('Hora do Dia', fontsize=12)
        
        # Estatísticas
        corr = df_mes['carga_liq_mw'].corr(df_mes['curtailment_mw'])
        carga_media = df_mes['carga_liq_mw'].mean()
        curtail_media = df_mes['curtailment_mw'].mean()
        
        # Título e labels
        ax.set_xlabel('Carga Líquida (MW)', fontsize=13, fontweight='bold')
        ax.set_ylabel('Curtailment (MW)', fontsize=13, fontweight='bold')
        ax.set_title(
            f'Carga Líquida vs Curtailment - {meses_pt[mes]} {ano}\n' +
            f'Correlação: {corr:.3f} | Registros: {len(df_mes):,}',
            fontsize=14,
            fontweight='bold',
            pad=15
        )
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # Texto com estatísticas
        texto_stats = f'Carga Média: {carga_media:,.0f} MW\n'
        texto_stats += f'Curtailment Médio: {curtail_media:,.2f} MW'
        ax.text(
            0.02, 0.98,
            texto_stats,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        )
        
        plt.tight_layout()
        
        # Salvar figura
        nome_arquivo = f'scatter_carga_vs_curtailment_{ano}_{mes:02d}_{meses_pt[mes]}.png'
        caminho_arquivo = OUTPUT_DIR / nome_arquivo
        plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight')
        plt.close()
        
        graficos_gerados += 1
        print(f"  [{mes:02d}] {meses_pt[mes]:<12} - [OK] Grafico salvo ({len(df_mes):,} pontos)")
    
    return graficos_gerados

def gerar_grafico_grade_completa(df_ano, ano):
    """Gera um único gráfico com grade 3x4 mostrando todos os meses."""
    
    print(f"\n{'='*80}")
    print(f"  GERANDO GRÁFICO COM GRADE COMPLETA - {ano}")
    print(f"{'='*80}\n")
    
    # Nomes dos meses em português
    meses_pt = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr',
        5: 'Mai', 6: 'Jun', 7: 'Jul', 8: 'Ago',
        9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    
    # Criar figura com subplots 3x4
    fig, axes = plt.subplots(3, 4, figsize=(20, 15))
    fig.suptitle(
        f'Carga Líquida vs Curtailment - {ano} (Por Mês)',
        fontsize=18,
        fontweight='bold',
        y=0.995
    )
    
    axes = axes.flatten()
    
    for mes in range(1, 13):
        ax = axes[mes - 1]
        
        # Filtrar dados do mês
        df_mes = df_ano[df_ano['mes'] == mes].copy()
        df_mes = df_mes.dropna(subset=['carga_liq_mw', 'curtailment_mw'])
        
        if len(df_mes) == 0:
            ax.text(0.5, 0.5, 'Sem dados', 
                   ha='center', va='center',
                   transform=ax.transAxes,
                   fontsize=14, color='gray')
            ax.set_xlabel('Carga Líquida (MW)', fontsize=10)
            ax.set_ylabel('Curtailment (MW)', fontsize=10)
            ax.set_title(f'{meses_pt[mes]}', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            continue
        
        # Scatter plot
        scatter = ax.scatter(
            df_mes['carga_liq_mw'],
            df_mes['curtailment_mw'],
            c=df_mes['hora'],
            cmap='viridis',
            alpha=0.5,
            s=20,
            edgecolors='k',
            linewidth=0.3
        )
        
        # Estatísticas
        corr = df_mes['carga_liq_mw'].corr(df_mes['curtailment_mw'])
        
        # Título e labels
        ax.set_xlabel('Carga Líquida (MW)', fontsize=10)
        ax.set_ylabel('Curtailment (MW)', fontsize=10)
        ax.set_title(
            f'{meses_pt[mes]} (R={corr:.2f})',
            fontsize=11,
            fontweight='bold'
        )
        
        # Grid
        ax.grid(True, alpha=0.3, linestyle='--')
    
    # Colorbar compartilhada
    fig.subplots_adjust(right=0.92)
    cbar_ax = fig.add_axes([0.94, 0.15, 0.02, 0.7])
    cbar = fig.colorbar(scatter, cax=cbar_ax)
    cbar.set_label('Hora do Dia', fontsize=12)
    
    plt.tight_layout(rect=[0, 0, 0.92, 0.99])
    
    # Salvar figura
    nome_arquivo = f'scatter_carga_vs_curtailment_{ano}_grade_completa.png'
    caminho_arquivo = OUTPUT_DIR / nome_arquivo
    plt.savefig(caminho_arquivo, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"  [OK] Grafico de grade completa salvo")

def main():
    """Função principal."""
    
    print("\n" + "="*80)
    print("  SCATTER: CARGA LÍQUIDA VS CURTAILMENT - POR MÊS")
    print("="*80)
    
    # Carregar dados
    df = carregar_dados()
    
    # Filtrar ano
    df_ano = filtrar_ano(df, ANO)
    
    if df_ano is None:
        print(f"\n[ERRO] Não foi possível gerar gráficos para {ANO}")
        return
    
    # Gerar gráficos individuais por mês
    n_graficos = gerar_scatter_por_mes(df_ano, ANO)
    
    # Gerar gráfico com grade completa
    gerar_grafico_grade_completa(df_ano, ANO)
    
    print(f"\n{'='*80}")
    print(f"  CONCLUÍDO!")
    print(f"{'='*80}\n")
    print(f"  Total de gráficos gerados: {n_graficos + 1}")
    print(f"  Diretório de saída: {OUTPUT_DIR}")
    print(f"\n  Arquivos gerados:")
    print(f"    - {n_graficos} gráficos individuais (um por mês)")
    print(f"    - 1 gráfico com grade completa (todos os meses)")
    
    # Listar arquivos
    print(f"\n  Gráficos salvos:")
    for arquivo in sorted(OUTPUT_DIR.glob(f'scatter_carga_vs_curtailment_{ANO}_*.png')):
        print(f"    - {arquivo.name}")
    
    print(f"\n{'='*80}\n")

if __name__ == "__main__":
    main()

