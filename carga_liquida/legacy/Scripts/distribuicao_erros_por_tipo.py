"""
Distribuição de Erros por Tipo de Componente
=============================================

Classifica cada erro pela componente dominante e analisa distribuições.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Carregar dados processados
CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

def carregar_e_classificar():
    """Carrega dados e classifica erros por tipo."""
    
    print("="*80)
    print("  CLASSIFICAÇÃO DE ERROS POR TIPO DE COMPONENTE")
    print("="*80)
    
    # Carregar CSV gerado anteriormente
    csv_path = CARGA_LIQ_DIR / "Output" / "analise_completa" / "extremos_completos.csv"
    
    if not csv_path.exists():
        print(f"\n[!] Execute primeiro: comparacao_completa_componentes.py")
        return None
    
    print(f"\n[1/3] Carregando dados completos...")
    df = pd.read_csv(csv_path)
    print(f"     Registros: {len(df):,}")
    
    # Calcular contribuições individuais
    print(f"\n[2/3] Calculando contribuições...")
    
    df['contrib_carga'] = df['carga_sim'] - df['carga_real']
    df['contrib_eolica'] = -(df['eolica_pos_sim'] - df['eolica_real'])  # Negativo pois mais eólica reduz CL
    df['contrib_solar'] = -(df['solar_pos_sim'] - df['solar_real'])
    df['contrib_hidro_fd'] = -(df['hidro_fd_sim'] - df['hidro_fd_real'])
    
    # Identificar componente dominante (maior contribuição absoluta)
    df['contrib_abs_carga'] = df['contrib_carga'].abs()
    df['contrib_abs_eolica'] = df['contrib_eolica'].abs()
    df['contrib_abs_solar'] = df['contrib_solar'].abs()
    df['contrib_abs_hidro_fd'] = df['contrib_hidro_fd'].abs()
    
    # Classificar por tipo
    def classificar_erro(row):
        contribs = {
            'Carga': row['contrib_abs_carga'],
            'Eolica': row['contrib_abs_eolica'],
            'Solar': row['contrib_abs_solar'],
            'Hidro FD': row['contrib_abs_hidro_fd']
        }
        return max(contribs, key=contribs.get)
    
    df['tipo_erro_dominante'] = df.apply(classificar_erro, axis=1)
    
    print(f"\n[3/3] Classificação concluída!")
    
    # Estatísticas por tipo
    print(f"\n" + "="*80)
    print(f"  DISTRIBUIÇÃO POR TIPO DE ERRO")
    print("="*80)
    
    tipo_map = {
        'Carga': 'carga',
        'Eolica': 'eolica', 
        'Solar': 'solar',
        'Hidro FD': 'hidro_fd'
    }
    
    for tipo_display, tipo_col in tipo_map.items():
        df_tipo = df[df['tipo_erro_dominante'] == tipo_display]
        pct = len(df_tipo) / len(df) * 100
        media_erro = df_tipo['diff_carga_liq'].mean()
        
        col_contrib = f'contrib_{tipo_col}'
        
        print(f"\n{tipo_display}:")
        print(f"  Frequencia: {len(df_tipo)} casos ({pct:.1f}%)")
        print(f"  Erro medio: {media_erro:,.0f} MW")
        if col_contrib in df_tipo.columns:
            print(f"  Contribuicao media: {df_tipo[col_contrib].mean():,.0f} MW")
    
    return df

def gerar_graficos_distribuicao(df):
    """Gera gráficos de distribuição por tipo."""
    
    print("\n" + "="*80)
    print("  GERANDO GRÁFICOS")
    print("="*80)
    
    output_dir = CARGA_LIQ_DIR / "Output" / "distribuicao_erros"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Pizza + Histogramas por tipo
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
    
    # Pizza
    ax_pizza = fig.add_subplot(gs[0, :])
    contagem = df['tipo_erro_dominante'].value_counts()
    colors = {'Carga': 'green', 'Eolica': 'blue', 'Solar': 'orange', 'Hidro FD': 'skyblue'}
    cores_pizza = [colors[tipo] for tipo in contagem.index]
    
    wedges, texts, autotexts = ax_pizza.pie(contagem.values, labels=contagem.index, autopct='%1.1f%%',
                                            colors=cores_pizza, startangle=90, textprops={'fontsize': 12})
    ax_pizza.set_title('Distribuição dos Erros por Componente Dominante', fontsize=14, fontweight='bold')
    
    # Histogramas por tipo
    tipos = ['Carga', 'Eolica', 'Solar', 'Hidro FD']
    posicoes = [(1, 0), (1, 1), (1, 2), (2, 0)]
    
    for tipo, (row, col) in zip(tipos, posicoes):
        ax = fig.add_subplot(gs[row, col])
        df_tipo = df[df['tipo_erro_dominante'] == tipo]
        
        if len(df_tipo) > 0:
            ax.hist(df_tipo['diff_carga_liq'], bins=30, color=colors[tipo], 
                   alpha=0.7, edgecolor='black')
            ax.axvline(df_tipo['diff_carga_liq'].mean(), color='red', linestyle='--', 
                      linewidth=2, label=f'Média: {df_tipo["diff_carga_liq"].mean():.0f} MW')
            ax.set_title(f'Erro quando {tipo} domina ({len(df_tipo)} casos)', fontweight='bold', fontsize=11)
            ax.set_xlabel('Diferença Carga Líquida (MW)', fontsize=10)
            ax.set_ylabel('Frequência', fontsize=10)
            ax.legend(fontsize=9)
            ax.grid(True, alpha=0.3, axis='y')
    
    # Último subplot: resumo
    ax = fig.add_subplot(gs[2, 1:])
    resumo_data = []
    for tipo in tipos:
        df_tipo = df[df['tipo_erro_dominante'] == tipo]
        if len(df_tipo) > 0:
            resumo_data.append({
                'Tipo': tipo,
                'Casos': len(df_tipo),
                'Erro Médio': df_tipo['diff_carga_liq'].mean(),
                'Contrib Media': df_tipo.get(f"contrib_{tipo.lower().replace(' ', '_')}", pd.Series([np.nan])).mean()
            })
    
    df_resumo = pd.DataFrame(resumo_data)
    x = np.arange(len(df_resumo))
    width = 0.35
    
    ax.bar(x - width/2, df_resumo['Erro Médio'], width, label='Erro Total', alpha=0.8, color='red')
    ax.bar(x + width/2, df_resumo['Contrib Media'], width, label='Contribuicao', alpha=0.8, color='blue')
    ax.set_xlabel('Tipo de Erro Dominante', fontsize=11)
    ax.set_ylabel('MW', fontsize=11)
    ax.set_title('Erro Médio vs Contribuição Média por Tipo', fontweight='bold', fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels(df_resumo['Tipo'], fontsize=10)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(0, color='black', linestyle=':', linewidth=1)
    
    plt.suptitle('Distribuição de Erros por Tipo de Componente Dominante', 
                fontsize=16, fontweight='bold', y=0.995)
    plt.savefig(output_dir / 'distribuicao_por_tipo_erro.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] distribuicao_por_tipo_erro.png")
    plt.close()
    
    # 2. Boxplot das contribuições
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Contribuições de Cada Componente (Top 100 Extremos)', fontsize=16, fontweight='bold')
    
    # Boxplot 1: Carga
    ax = axes[0, 0]
    data_carga = [df[df['tipo_erro_dominante']==t]['contrib_carga'].dropna() for t in tipos if len(df[df['tipo_erro_dominante']==t]) > 0]
    labels_carga = [t for t in tipos if len(df[df['tipo_erro_dominante']==t]) > 0]
    bp = ax.boxplot(data_carga, labels=labels_carga, patch_artist=True)
    for patch, tipo in zip(bp['boxes'], labels_carga):
        patch.set_facecolor(colors[tipo])
    ax.axhline(0, color='red', linestyle=':', linewidth=1)
    ax.set_title('Contribuição: Carga', fontweight='bold')
    ax.set_ylabel('MW', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Boxplot 2: Eólica
    ax = axes[0, 1]
    data_eolica = [df[df['tipo_erro_dominante']==t]['contrib_eolica'].dropna() for t in tipos if len(df[df['tipo_erro_dominante']==t]) > 0]
    bp = ax.boxplot(data_eolica, labels=labels_carga, patch_artist=True)
    for patch, tipo in zip(bp['boxes'], labels_carga):
        patch.set_facecolor(colors[tipo])
    ax.axhline(0, color='red', linestyle=':', linewidth=1)
    ax.set_title('Contribuição: Eólica', fontweight='bold')
    ax.set_ylabel('MW', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Boxplot 3: Solar
    ax = axes[1, 0]
    data_solar = [df[df['tipo_erro_dominante']==t]['contrib_solar'].dropna() for t in tipos if len(df[df['tipo_erro_dominante']==t]) > 0]
    bp = ax.boxplot(data_solar, labels=labels_carga, patch_artist=True)
    for patch, tipo in zip(bp['boxes'], labels_carga):
        patch.set_facecolor(colors[tipo])
    ax.axhline(0, color='red', linestyle=':', linewidth=1)
    ax.set_title('Contribuição: Solar', fontweight='bold')
    ax.set_ylabel('MW', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Boxplot 4: Hidro FD
    ax = axes[1, 1]
    data_hidro = [df[df['tipo_erro_dominante']==t]['contrib_hidro_fd'].dropna() for t in tipos if len(df[df['tipo_erro_dominante']==t]) > 0]
    bp = ax.boxplot(data_hidro, labels=labels_carga, patch_artist=True)
    for patch, tipo in zip(bp['boxes'], labels_carga):
        patch.set_facecolor(colors[tipo])
    ax.axhline(0, color='red', linestyle=':', linewidth=1)
    ax.set_title('Contribuição: Hidro FD', fontweight='bold')
    ax.set_ylabel('MW', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'boxplot_contribuicoes_por_tipo.png', dpi=150, bbox_inches='tight')
    print(f"[OK] boxplot_contribuicoes_por_tipo.png")
    plt.close()
    
    # 3. Heatmap: hora vs tipo de erro (se houver colunas temporais)
    if 'hora' in df.columns and 'mes' in df.columns:
        fig, axes = plt.subplots(1, 2, figsize=(18, 6))
        fig.suptitle('Distribuicao Temporal dos Tipos de Erro', fontsize=16, fontweight='bold')
        
        # Por hora
        ax = axes[0]
        hora_tipo = pd.crosstab(df['hora'], df['tipo_erro_dominante'], normalize='index') * 100
        sns.heatmap(hora_tipo, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax, cbar_kws={'label': '% dos casos'})
        ax.set_title('Tipo de Erro por Hora do Dia', fontweight='bold', fontsize=12)
        ax.set_xlabel('Tipo de Erro Dominante', fontsize=11)
        ax.set_ylabel('Hora', fontsize=11)
        
        # Por mês
        ax = axes[1]
        mes_tipo = pd.crosstab(df['mes'], df['tipo_erro_dominante'], normalize='index') * 100
        sns.heatmap(mes_tipo, annot=True, fmt='.1f', cmap='YlOrRd', ax=ax, cbar_kws={'label': '% dos casos'})
        ax.set_title('Tipo de Erro por Mes', fontweight='bold', fontsize=12)
        ax.set_xlabel('Tipo de Erro Dominante', fontsize=11)
        ax.set_ylabel('Mes', fontsize=11)
        
        plt.tight_layout()
        plt.savefig(output_dir / 'heatmap_erros_temporal.png', dpi=150, bbox_inches='tight')
        print(f"[OK] heatmap_erros_temporal.png")
        plt.close()
    else:
        print(f"[!] Colunas temporais nao encontradas, pulando heatmaps")
    
    # 4. Scatter colorido por tipo de erro
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    
    for tipo in ['Carga', 'Eólica', 'Solar', 'Hidro FD']:
        df_tipo = df[df['tipo_erro_dominante'] == tipo]
        if len(df_tipo) > 0:
            ax.scatter(df_tipo['carga_liq_real'], df_tipo['carga_liq_sim'],
                      label=f'{tipo} ({len(df_tipo)} casos)', alpha=0.6, s=60, 
                      edgecolor='k', linewidth=0.5)
    
    # Linha x=y
    lim_min = min(df['carga_liq_real'].min(), df['carga_liq_sim'].min())
    lim_max = max(df['carga_liq_real'].max(), df['carga_liq_sim'].max())
    ax.plot([lim_min, lim_max], [lim_min, lim_max], 'r--', linewidth=2, label='x=y (perfeito)', alpha=0.7)
    
    ax.set_xlabel('Carga Líquida Real (MW)', fontsize=12)
    ax.set_ylabel('Carga Líquida Simulada (MW)', fontsize=12)
    ax.set_title('Scatter: Real vs Simulado (colorido por tipo de erro dominante)', 
                fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper left')
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_dir / 'scatter_por_tipo_erro.png', dpi=150, bbox_inches='tight')
    print(f"[OK] scatter_por_tipo_erro.png")
    plt.close()
    
    # 5. Violinplot das contribuições
    fig, ax = plt.subplots(1, 1, figsize=(14, 7))
    
    # Preparar dados para violin
    data_violin = []
    labels_violin = []
    
    for tipo in tipos:
        for componente in ['carga', 'eolica', 'solar', 'hidro_fd']:
            df_tipo = df[df['tipo_erro_dominante'] == tipo]
            if len(df_tipo) > 0:
                valores = df_tipo[f'contrib_{componente}'].dropna()
                if len(valores) > 0:
                    data_violin.append(valores)
                    labels_violin.append(f'{tipo[:3]}\n{componente[:3].upper()}')
    
    parts = ax.violinplot(data_violin, positions=range(len(data_violin)), 
                         showmeans=True, showmedians=True)
    
    ax.set_xticks(range(len(labels_violin)))
    ax.set_xticklabels(labels_violin, fontsize=8, rotation=45, ha='right')
    ax.set_ylabel('Contribuição (MW)', fontsize=12)
    ax.set_title('Distribuição das Contribuições por Tipo de Erro', fontsize=14, fontweight='bold')
    ax.axhline(0, color='red', linestyle=':', linewidth=1.5)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'violin_contribuicoes.png', dpi=150, bbox_inches='tight')
    print(f"[OK] violin_contribuicoes.png")
    plt.close()
    
    # 6. Magnitude do erro por tipo
    fig, axes = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Magnitude e Direção do Erro por Tipo', fontsize=16, fontweight='bold')
    
    # Distribuição da diferença absoluta
    ax = axes[0]
    for tipo in tipos:
        df_tipo = df[df['tipo_erro_dominante'] == tipo]
        if len(df_tipo) > 0:
            ax.hist(df_tipo['diff_abs'], bins=20, alpha=0.5, label=f'{tipo}', 
                   edgecolor='black', linewidth=0.5)
    ax.set_xlabel('|Diferença| (MW)', fontsize=11)
    ax.set_ylabel('Frequência', fontsize=11)
    ax.set_title('Distribuição da Magnitude do Erro', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Direção do erro (positivo vs negativo)
    ax = axes[1]
    for tipo in tipos:
        df_tipo = df[df['tipo_erro_dominante'] == tipo]
        if len(df_tipo) > 0:
            positivos = len(df_tipo[df_tipo['diff_carga_liq'] > 0])
            negativos = len(df_tipo[df_tipo['diff_carga_liq'] < 0])
            total = len(df_tipo)
            
            ax.bar(tipo, positivos, label='Superestima' if tipo == tipos[0] else '', 
                  color='green', alpha=0.7)
            ax.bar(tipo, -negativos, label='Subestima' if tipo == tipos[0] else '', 
                  color='red', alpha=0.7)
            
            # Anotações
            if positivos > 0:
                ax.text(tipo, positivos/2, f'{positivos}\n({positivos/total*100:.0f}%)', 
                       ha='center', va='center', fontsize=9, fontweight='bold')
            if negativos > 0:
                ax.text(tipo, -negativos/2, f'{negativos}\n({negativos/total*100:.0f}%)', 
                       ha='center', va='center', fontsize=9, fontweight='bold')
    
    ax.axhline(0, color='black', linewidth=1.5)
    ax.set_ylabel('Número de Casos', fontsize=11)
    ax.set_title('Direção do Erro (Superestima vs Subestima)', fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    plt.tight_layout()
    plt.savefig(output_dir / 'magnitude_direcao_por_tipo.png', dpi=150, bbox_inches='tight')
    print(f"[OK] magnitude_direcao_por_tipo.png")
    plt.close()
    
    print("\n" + "="*80)
    print("  [OK] GRÁFICOS GERADOS!")
    print("="*80)
    print(f"\nResultados em: {output_dir}")
    
    return df

if __name__ == '__main__':
    df = carregar_e_classificar()
    if df is not None:
        df = gerar_graficos_distribuicao(df)
        
        print(f"\n{'='*80}")
        print("  RESUMO FINAL")
        print("="*80)
        print(f"\nDos {len(df)} maiores extremos:")
        print(f"  {(df['tipo_erro_dominante']=='Carga').sum()} casos ({(df['tipo_erro_dominante']=='Carga').sum()/len(df)*100:.1f}%) - Erro dominado por CARGA")
        print(f"  {(df['tipo_erro_dominante']=='Eólica').sum()} casos ({(df['tipo_erro_dominante']=='Eólica').sum()/len(df)*100:.1f}%) - Erro dominado por EÓLICA")
        print(f"  {(df['tipo_erro_dominante']=='Solar').sum()} casos ({(df['tipo_erro_dominante']=='Solar').sum()/len(df)*100:.1f}%) - Erro dominado por SOLAR")
        print(f"  {(df['tipo_erro_dominante']=='Hidro FD').sum()} casos ({(df['tipo_erro_dominante']=='Hidro FD').sum()/len(df)*100:.1f}%) - Erro dominado por HIDRO FD")

