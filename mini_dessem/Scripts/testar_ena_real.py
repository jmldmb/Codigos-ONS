"""
Script para testar a integração dos dados reais de ENA
"""

import sys
from pathlib import Path

# Adicionar diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mini_dessem.simulation import _load_ena_historico, _media_mensal_ena_real
from mini_dessem.data import ENA_dic

def main():
    print("="*70)
    print("TESTE DE INTEGRAÇÃO - DADOS REAIS DE ENA")
    print("="*70)
    print()
    
    # 1. Testar carregamento do arquivo
    print("[1] Testando carregamento do arquivo ENA_HISTORICO.xlsx...")
    df = _load_ena_historico()
    
    if df is None:
        print("   [ERRO] Nao foi possivel carregar o arquivo!")
        return
    else:
        print(f"   [OK] Arquivo carregado com sucesso!")
        print(f"   - Total de registros: {len(df):,}")
        print(f"   - Anos disponiveis: {sorted(df['ano'].unique())}")
        print(f"   - Colunas: {list(df.columns)}")
        print()
    
    # 2. Testar médias mensais para alguns anos
    print("[2] Comparando valores reais vs. valores do dicionário...")
    print()
    
    anos_teste = [2022, 2023, 2024, 2025]
    meses_teste = range(1, 13)
    
    # Tabela comparativa
    print(f"{'Ano-Mês':<10} | {'ENA Real (MW)':<15} | {'ENA Dict (MW)':<15} | {'Diferença (%)':<15} | {'Status':<10}")
    print("-" * 85)
    
    total_com_dados_reais = 0
    total_sem_dados_reais = 0
    
    for ano in anos_teste:
        for mes in meses_teste:
            ena_real = _media_mensal_ena_real(ano, mes)
            ena_dict = ENA_dic.get(ano, {}).get(mes)
            
            ano_mes_str = f"{ano}-{mes:02d}"
            
            if ena_real is not None and ena_dict is not None:
                dif_pct = ((ena_real - ena_dict) / ena_dict) * 100
                status = "REAL"
                total_com_dados_reais += 1
                print(f"{ano_mes_str:<10} | {ena_real:>13,.0f} | {ena_dict:>13,.0f} | {dif_pct:>13,.1f}% | {status:<10}")
            elif ena_real is None and ena_dict is not None:
                status = "DICT"
                total_sem_dados_reais += 1
                print(f"{ano_mes_str:<10} | {'N/A':>13} | {ena_dict:>13,.0f} | {'N/A':>13} | {status:<10}")
            else:
                status = "MISSING"
                print(f"{ano_mes_str:<10} | {'N/A':>13} | {'N/A':>13} | {'N/A':>13} | {status:<10}")
    
    print()
    print("="*70)
    print("RESUMO:")
    print(f"  - Periodos com dados reais disponiveis: {total_com_dados_reais}")
    print(f"  - Periodos usando valores do dicionario: {total_sem_dados_reais}")
    print()
    
    if total_com_dados_reais > 0:
        print("[SUCESSO] A integracao dos dados reais de ENA esta funcionando.")
        print("  Os valores reais serao usados automaticamente quando disponiveis.")
    else:
        print("[AVISO] Nenhum dado real encontrado para os anos testados.")
        print("  Verifique se o arquivo ENA_HISTORICO.xlsx contem dados para 2022-2025.")
    
    print()
    print("="*70)


if __name__ == "__main__":
    main()

