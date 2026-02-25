"""
Análise de Dia Específico
==========================

Permite analisar em detalhe qualquer dia específico da série histórica.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import sys
from datetime import datetime

CARGA_LIQ_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\carga_liquida")

def carregar_base_completa():
    """Carrega base completa com todos os componentes."""
    
    # PRIORIZAR arquivo completo (tem carga bruta)
    csv_completo = CARGA_LIQ_DIR / "Output" / "analise_completa" / "comparacao_completa.csv"
    
    if csv_completo.exists():
        print("\n[1/1] Carregando base completa (COM carga bruta)...")
        df = pd.read_csv(csv_completo)
        df['din_instante'] = pd.to_datetime(df['din_instante'])
        
        # Verificar colunas disponíveis
        print(f"     Colunas disponiveis: {len(df.columns)}")
        
        # Renomear para padronizar
        rename_map = {}
        
        # Carga bruta
        if 'carga_real' in df.columns:
            rename_map['carga_real'] = 'carga_bruta_real'
        if 'carga_sim' in df.columns:
            rename_map['carga_sim'] = 'carga_bruta_sim'
        
        # Carga líquida
        if 'carga_liq_real' not in df.columns and 'carga_liquida_historica' in df.columns:
            rename_map['carga_liquida_historica'] = 'carga_liq_real'
        if 'carga_liq_sim' not in df.columns and 'carga_liquida' in df.columns:
            rename_map['carga_liquida'] = 'carga_liq_sim'
        
        # Hidro
        if 'hidro_r_real' not in df.columns and 'R' in df.columns:
            rename_map['R'] = 'hidro_r_real'
        if 'hidro_r_sim' not in df.columns and 'val_gerhidro_reservatorio' in df.columns:
            rename_map['val_gerhidro_reservatorio'] = 'hidro_r_sim'
        
        # Térmica
        if 'termica_flex_real' not in df.columns and 'termica_flexivel' in df.columns:
            rename_map['termica_flexivel'] = 'termica_flex_real'
        if 'termica_flex_sim' not in df.columns and 'val_term_despacho' in df.columns:
            rename_map['val_term_despacho'] = 'termica_flex_sim'
        
        df = df.rename(columns=rename_map)
        
        # Calcular diferenças
        if 'carga_bruta_real' in df.columns and 'carga_bruta_sim' in df.columns:
            df['diff_carga_bruta'] = df['carga_bruta_sim'] - df['carga_bruta_real']
        else:
            df['diff_carga_bruta'] = None
            
        df['diff_carga_liq'] = df['carga_liq_sim'] - df['carga_liq_real']
        df['diff_hidro_r'] = df['hidro_r_sim'] - df['hidro_r_real']
        df['diff_termica'] = df['termica_flex_sim'] - df['termica_flex_real']
        
        return df
        
    else:
        print("\n[!] Arquivo completo nao encontrado!")
        print(f"    Esperado: {csv_completo}")
        print("\n    Execute primeiro: comparacao_completa_componentes.py")
        return None

def analisar_dia(df, data_str):
    """Analisa um dia específico."""
    
    try:
        data = pd.to_datetime(data_str)
    except:
        print(f"\n[!] Data invalida: {data_str}")
        print("    Use formato: YYYY-MM-DD (ex: 2023-09-25)")
        return None
    
    # Filtrar dia
    df_dia = df[df['din_instante'].dt.date == data.date()].copy()
    
    if len(df_dia) == 0:
        print(f"\n[!] Sem dados para {data_str}")
        print(f"    Periodo disponivel: {df['din_instante'].min().date()} ate {df['din_instante'].max().date()}")
        return None
    
    df_dia = df_dia.sort_values('din_instante').reset_index(drop=True)
    df_dia['hora'] = df_dia['din_instante'].dt.hour
    
    print("\n" + "="*100)
    print(f"  ANALISE DO DIA: {data.strftime('%d/%m/%Y (%A)')}")
    print("="*100)
    
    # Estatísticas do dia
    print(f"\nREGISTROS: {len(df_dia)} horas")
    
    # Verificar se tem carga bruta
    has_carga_bruta = df_dia['carga_bruta_real'].notna().all()
    
    if has_carga_bruta:
        print(f"\n{'='*100}")
        print(f"CARGA BRUTA (TOTAL):")
        print(f"{'='*100}")
        print(f"  Real Media:          {df_dia['carga_bruta_real'].mean():>10,.0f} MW")
        print(f"  Simulado Media:      {df_dia['carga_bruta_sim'].mean():>10,.0f} MW")
        print(f"  Diferenca Media:     {df_dia['diff_carga_bruta'].mean():>10,.0f} MW ({df_dia['diff_carga_bruta'].mean() / df_dia['carga_bruta_real'].mean() * 100:>6.1f}%)")
        print(f"  Min Real/Sim:        {df_dia['carga_bruta_real'].min():>10,.0f} / {df_dia['carga_bruta_sim'].min():>10,.0f} MW")
        print(f"  Max Real/Sim:        {df_dia['carga_bruta_real'].max():>10,.0f} / {df_dia['carga_bruta_sim'].max():>10,.0f} MW")
    
    print(f"\n{'='*100}")
    print(f"CARGA LIQUIDA:")
    print(f"{'='*100}")
    print(f"  Real Media:          {df_dia['carga_liq_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:      {df_dia['carga_liq_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca Media:     {df_dia['diff_carga_liq'].mean():>10,.0f} MW ({df_dia['diff_carga_liq'].mean() / df_dia['carga_liq_real'].mean() * 100:>6.1f}%)")
    print(f"  Min Real/Sim:        {df_dia['carga_liq_real'].min():>10,.0f} / {df_dia['carga_liq_sim'].min():>10,.0f} MW")
    print(f"  Max Real/Sim:        {df_dia['carga_liq_real'].max():>10,.0f} / {df_dia['carga_liq_sim'].max():>10,.0f} MW")
    
    print(f"\n{'='*100}")
    print(f"HIDRO RESERVATORIO:")
    print(f"{'='*100}")
    print(f"  Real Media:          {df_dia['hidro_r_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:      {df_dia['hidro_r_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca Media:     {df_dia['diff_hidro_r'].mean():>10,.0f} MW ({df_dia['diff_hidro_r'].mean() / df_dia['hidro_r_real'].mean() * 100:>6.1f}%)")
    print(f"  Min Real/Sim:        {df_dia['hidro_r_real'].min():>10,.0f} / {df_dia['hidro_r_sim'].min():>10,.0f} MW")
    print(f"  Max Real/Sim:        {df_dia['hidro_r_real'].max():>10,.0f} / {df_dia['hidro_r_sim'].max():>10,.0f} MW")
    
    print(f"\n{'='*100}")
    print(f"TERMICA FLEXIVEL:")
    print(f"{'='*100}")
    print(f"  Real Media:          {df_dia['termica_flex_real'].mean():>10,.0f} MW")
    print(f"  Simulado Media:      {df_dia['termica_flex_sim'].mean():>10,.0f} MW")
    print(f"  Diferenca Media:     {df_dia['diff_termica'].mean():>10,.0f} MW")
    if df_dia['termica_flex_real'].mean() > 10:
        print(f"  Erro Percentual:     {df_dia['diff_termica'].mean() / df_dia['termica_flex_real'].mean() * 100:>6.1f}%")
    print(f"  Min Real/Sim:        {df_dia['termica_flex_real'].min():>10,.0f} / {df_dia['termica_flex_sim'].min():>10,.0f} MW")
    print(f"  Max Real/Sim:        {df_dia['termica_flex_real'].max():>10,.0f} / {df_dia['termica_flex_sim'].max():>10,.0f} MW")
    
    # Tabela hora a hora
    print(f"\n{'='*100}")
    print(f"DETALHAMENTO HORA A HORA:")
    print(f"{'='*100}")
    
    if has_carga_bruta:
        print(f"{'Hora':>4} | {'CB Real':>10} | {'CB Sim':>10} | {'Erro CB':>10} | {'CL Real':>10} | {'CL Sim':>10} | {'Erro CL':>10} | {'HR Real':>10} | {'HR Sim':>10} | {'T Real':>8} | {'T Sim':>8}")
        print(f"{'-'*4}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
        
        for _, row in df_dia.iterrows():
            hora = int(row['hora'])
            print(f"{hora:4d} | {row['carga_bruta_real']:10,.0f} | {row['carga_bruta_sim']:10,.0f} | "
                  f"{row['diff_carga_bruta']:10,.0f} | {row['carga_liq_real']:10,.0f} | {row['carga_liq_sim']:10,.0f} | "
                  f"{row['diff_carga_liq']:10,.0f} | {row['hidro_r_real']:10,.0f} | {row['hidro_r_sim']:10,.0f} | "
                  f"{row['termica_flex_real']:8,.0f} | {row['termica_flex_sim']:8,.0f}")
    else:
        print(f"{'Hora':>4} | {'CL Real':>10} | {'CL Sim':>10} | {'Erro CL':>10} | {'HR Real':>10} | {'HR Sim':>10} | {'Erro HR':>10} | {'T Real':>8} | {'T Sim':>8}")
        print(f"{'-'*4}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*10}-+-{'-'*8}-+-{'-'*8}")
        
        for _, row in df_dia.iterrows():
            hora = int(row['hora'])
            print(f"{hora:4d} | {row['carga_liq_real']:10,.0f} | {row['carga_liq_sim']:10,.0f} | "
                  f"{row['diff_carga_liq']:10,.0f} | {row['hidro_r_real']:10,.0f} | {row['hidro_r_sim']:10,.0f} | "
                  f"{row['diff_hidro_r']:10,.0f} | {row['termica_flex_real']:8,.0f} | {row['termica_flex_sim']:8,.0f}")
    
    # Identificar pior hora
    idx_pior = df_dia['diff_carga_liq'].abs().idxmax()
    pior_hora = df_dia.loc[idx_pior]
    
    print(f"\n{'='*100}")
    print(f"PIOR HORA DO DIA:")
    print(f"{'='*100}")
    print(f"  Hora: {int(pior_hora['hora'])}h")
    if has_carga_bruta:
        print(f"  Erro Carga Bruta: {pior_hora['diff_carga_bruta']:,.0f} MW ({pior_hora['diff_carga_bruta'] / pior_hora['carga_bruta_real'] * 100:.1f}%)")
    print(f"  Erro Carga Liquida: {pior_hora['diff_carga_liq']:,.0f} MW ({pior_hora['diff_carga_liq'] / pior_hora['carga_liq_real'] * 100:.1f}%)")
    print(f"  Erro Hidro R: {pior_hora['diff_hidro_r']:,.0f} MW")
    print(f"  Erro Termica: {pior_hora['diff_termica']:,.0f} MW")
    
    return df_dia

def gerar_graficos_dia(df_dia, data_str):
    """Gera gráficos para o dia."""
    
    data = pd.to_datetime(data_str)
    
    print(f"\n{'='*100}")
    print(f"GERANDO GRAFICOS...")
    print(f"{'='*100}")
    
    output_dir = CARGA_LIQ_DIR / "Output" / "analise_dias"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    data_filename = data.strftime('%Y%m%d')
    
    # Verificar se tem carga bruta
    has_carga_bruta = df_dia['carga_bruta_real'].notna().all()
    
    # 1. Comparação Real vs Simulado
    n_plots = 4 if has_carga_bruta else 3
    fig, axes = plt.subplots(n_plots, 1, figsize=(16, 4 + n_plots * 3))
    fig.suptitle(f'Analise do Dia: {data.strftime("%d/%m/%Y (%A)")}', 
                 fontsize=16, fontweight='bold')
    
    horas = df_dia['hora'].values
    idx = 0
    
    # Carga Bruta (se disponível)
    if has_carga_bruta:
        ax = axes[idx]
        ax.plot(horas, df_dia['carga_bruta_real'].values, 'o-', linewidth=2.5, markersize=8, 
               label='Real', color='darkgreen')
        ax.plot(horas, df_dia['carga_bruta_sim'].values, 's--', linewidth=2.5, markersize=8, 
               label='Simulado', color='lightgreen')
        ax.fill_between(horas, df_dia['carga_bruta_real'].values, df_dia['carga_bruta_sim'].values,
                         alpha=0.3, color='red', label='Diferenca')
        ax.set_ylabel('MW', fontsize=12, fontweight='bold')
        ax.set_title(f'Carga Bruta (Erro medio: {df_dia["diff_carga_bruta"].mean():,.0f} MW)', 
                    fontweight='bold', fontsize=13)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 2))
        idx += 1
    
    # Carga Líquida
    ax = axes[idx]
    idx += 1
    ax.plot(horas, df_dia['carga_liq_real'].values, 'o-', linewidth=2.5, markersize=8, 
           label='Real', color='blue')
    ax.plot(horas, df_dia['carga_liq_sim'].values, 's--', linewidth=2.5, markersize=8, 
           label='Simulado', color='orange')
    ax.fill_between(horas, df_dia['carga_liq_real'].values, df_dia['carga_liq_sim'].values,
                     alpha=0.3, color='red', label='Diferenca')
    ax.set_ylabel('MW', fontsize=12, fontweight='bold')
    ax.set_title(f'Carga Liquida (Erro medio: {df_dia["diff_carga_liq"].mean():,.0f} MW)', 
                fontweight='bold', fontsize=13)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # Hidro R
    ax = axes[idx]
    idx += 1
    ax.plot(horas, df_dia['hidro_r_real'].values, 'o-', linewidth=2.5, markersize=8, 
           label='Real', color='blue')
    ax.plot(horas, df_dia['hidro_r_sim'].values, 's--', linewidth=2.5, markersize=8, 
           label='Simulado', color='orange')
    ax.fill_between(horas, df_dia['hidro_r_real'].values, df_dia['hidro_r_sim'].values,
                     alpha=0.3, color='red', label='Diferenca')
    ax.set_ylabel('MW', fontsize=12, fontweight='bold')
    ax.set_title(f'Hidro Reservatorio (Erro medio: {df_dia["diff_hidro_r"].mean():,.0f} MW)', 
                fontweight='bold', fontsize=13)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    # Térmica
    ax = axes[idx]
    ax.plot(horas, df_dia['termica_flex_real'].values, 'o-', linewidth=2.5, markersize=8, 
           label='Real', color='blue')
    ax.plot(horas, df_dia['termica_flex_sim'].values, 's--', linewidth=2.5, markersize=8, 
           label='Simulado', color='orange')
    ax.fill_between(horas, df_dia['termica_flex_real'].values, df_dia['termica_flex_sim'].values,
                     alpha=0.3, color='red', label='Diferenca')
    ax.set_xlabel('Hora', fontsize=12, fontweight='bold')
    ax.set_ylabel('MW', fontsize=12, fontweight='bold')
    ax.set_title(f'Termica Flexivel (Erro medio: {df_dia["diff_termica"].mean():,.0f} MW)', 
                fontweight='bold', fontsize=13)
    ax.legend(loc='best', fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(output_dir / f'dia_{data_filename}_comparacao.png', dpi=150, bbox_inches='tight')
    print(f"\n[OK] dia_{data_filename}_comparacao.png")
    plt.close()
    
    # 2. Erros
    has_carga_bruta = df_dia['carga_bruta_real'].notna().all()
    n_error_plots = 3 if has_carga_bruta else 2
    fig, axes = plt.subplots(n_error_plots, 1, figsize=(16, n_error_plots * 4))
    fig.suptitle(f'Erros - {data.strftime("%d/%m/%Y (%A)")}', 
                 fontsize=16, fontweight='bold')
    
    idx = 0
    
    # Erro Carga Bruta (se disponível)
    if has_carga_bruta:
        ax = axes[idx]
        ax.bar(horas, df_dia['diff_carga_bruta'].values, width=0.7,
               color='darkgreen', alpha=0.8, edgecolor='black')
        ax.axhline(0, color='green', linestyle=':', linewidth=2)
        ax.set_ylabel('Erro Carga Bruta (MW)', fontsize=12, fontweight='bold')
        ax.set_title('Erro Carga Bruta por Hora', fontweight='bold', fontsize=13)
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_xticks(range(0, 24, 2))
        idx += 1
    
    # Erro CL e Hidro R
    ax = axes[idx]
    idx += 1
    width = 0.35
    x = np.arange(len(horas))
    
    bars1 = ax.bar(x - width/2, df_dia['diff_carga_liq'].values, width, 
                   label='Erro CL', color='purple', alpha=0.8, edgecolor='black')
    bars2 = ax.bar(x + width/2, df_dia['diff_hidro_r'].values, width, 
                   label='Erro Hidro R', color='steelblue', alpha=0.8, edgecolor='black')
    
    ax.axhline(0, color='green', linestyle=':', linewidth=2)
    ax.set_ylabel('Erro (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Carga Liquida e Hidro R', fontweight='bold', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(horas.astype(int))
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    
    # Térmica separada (escala diferente)
    ax = axes[idx]
    ax.bar(horas, df_dia['diff_termica'].values, width=0.7,
           color='orange', alpha=0.8, edgecolor='black')
    ax.axhline(0, color='green', linestyle=':', linewidth=2)
    ax.set_xlabel('Hora', fontsize=12, fontweight='bold')
    ax.set_ylabel('Erro Termica (MW)', fontsize=12, fontweight='bold')
    ax.set_title('Erro Termica Flexivel por Hora', fontweight='bold', fontsize=13)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(output_dir / f'dia_{data_filename}_erros.png', dpi=150, bbox_inches='tight')
    print(f"[OK] dia_{data_filename}_erros.png")
    plt.close()
    
    # 3. Stacked - Composição da Carga Líquida
    fig, axes = plt.subplots(2, 1, figsize=(16, 10))
    fig.suptitle(f'Composicao da Carga Liquida - {data.strftime("%d/%m/%Y (%A)")}', 
                 fontsize=16, fontweight='bold')
    
    # Real
    ax = axes[0]
    ax.bar(horas, df_dia['hidro_r_real'].values, label='Hidro R', 
          color='steelblue', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax.bar(horas, df_dia['termica_flex_real'].values, 
          bottom=df_dia['hidro_r_real'].values,
          label='Termica Flex', color='orange', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax.plot(horas, df_dia['carga_liq_real'].values, 'ro-', linewidth=2, markersize=6,
           label='CL Total', zorder=10)
    ax.set_ylabel('MW', fontsize=12, fontweight='bold')
    ax.set_title('REAL', fontweight='bold', fontsize=13)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    # Simulado
    ax = axes[1]
    ax.bar(horas, df_dia['hidro_r_sim'].values, label='Hidro R', 
          color='steelblue', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax.bar(horas, df_dia['termica_flex_sim'].values, 
          bottom=df_dia['hidro_r_sim'].values,
          label='Termica Flex', color='orange', alpha=0.8, edgecolor='black', linewidth=0.5)
    ax.plot(horas, df_dia['carga_liq_sim'].values, 'ro-', linewidth=2, markersize=6,
           label='CL Total', zorder=10)
    ax.set_xlabel('Hora', fontsize=12, fontweight='bold')
    ax.set_ylabel('MW', fontsize=12, fontweight='bold')
    ax.set_title('SIMULADO', fontweight='bold', fontsize=13)
    ax.legend(loc='upper left', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    plt.savefig(output_dir / f'dia_{data_filename}_composicao.png', dpi=150, bbox_inches='tight')
    print(f"[OK] dia_{data_filename}_composicao.png")
    plt.close()
    
    print(f"\n{'='*100}")
    print(f"[OK] GRAFICOS SALVOS!")
    print(f"{'='*100}")
    print(f"\nLocal: {output_dir}")
    
    return True

if __name__ == '__main__':
    # Pode passar data como argumento ou usar padrão
    if len(sys.argv) > 1:
        data_str = sys.argv[1]
    else:
        data_str = "2023-09-25"  # Padrão
    
    print("\n" + "="*100)
    print(f"  ANALISANDO DIA: {data_str}")
    print("="*100)
    
    df = carregar_base_completa()
    if df is not None:
        df_dia = analisar_dia(df, data_str)
        if df_dia is not None:
            gerar_graficos_dia(df_dia, data_str)
            
            print("\n" + "="*100)
            print("  ANALISE CONCLUIDA!")
            print("="*100)
            print("\nPara analisar outro dia, execute:")
            print("  python analise_dia_especifico.py YYYY-MM-DD")
            print("\nExemplo:")
            print("  python analise_dia_especifico.py 2023-12-15")

