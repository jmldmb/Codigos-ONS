"""
Análise de Múltiplos Dias Específicos - Modelo V4
==================================================

Gera análises detalhadas para vários dias de interesse.
"""

import sys
from pathlib import Path
from analise_dia_especifico import carregar_base_completa, analisar_dia, gerar_graficos_dia

# Lista de dias para analisar
DIAS_INTERESSE = [
    "2023-09-25",  # Setembro - mês crítico
    "2023-09-28",  # Setembro - final do mês
    "2023-12-15",  # Dezembro - pior mês
    "2024-07-15",  # Julho - melhor mês
    "2023-06-20",  # Junho - mês que v4 melhorou
    "2023-10-17",  # Outubro
    "2023-11-13",  # Novembro
    "2024-10-24",  # Outubro 2024
]

def main():
    """Processa todos os dias de interesse."""
    
    print("\n" + "="*100)
    print("  ANÁLISE DE MÚLTIPLOS DIAS - MODELO V4")
    print("="*100)
    print(f"\nTotal de dias a analisar: {len(DIAS_INTERESSE)}")
    print("\nDias:")
    for i, dia in enumerate(DIAS_INTERESSE, 1):
        print(f"  {i}. {dia}")
    
    # Carregar base completa uma vez
    print("\n" + "="*100)
    print("  CARREGANDO BASE DE DADOS")
    print("="*100)
    
    df = carregar_base_completa()
    
    if df is None:
        print("\n[ERRO] Não foi possível carregar a base de dados!")
        return
    
    # Processar cada dia
    resultados = []
    
    for i, data_str in enumerate(DIAS_INTERESSE, 1):
        print("\n\n" + "="*100)
        print(f"  [{i}/{len(DIAS_INTERESSE)}] PROCESSANDO: {data_str}")
        print("="*100)
        
        try:
            df_dia = analisar_dia(df, data_str)
            
            if df_dia is not None:
                sucesso = gerar_graficos_dia(df_dia, data_str)
                
                if sucesso:
                    resultados.append({
                        'data': data_str,
                        'status': 'OK',
                        'erro_medio_cl': df_dia['diff_carga_liq'].mean(),
                        'mae_cl': df_dia['diff_carga_liq'].abs().mean(),
                    })
                else:
                    resultados.append({'data': data_str, 'status': 'ERRO - Gráficos'})
            else:
                resultados.append({'data': data_str, 'status': 'ERRO - Sem dados'})
                
        except Exception as e:
            print(f"\n[ERRO] Falha ao processar {data_str}: {e}")
            resultados.append({'data': data_str, 'status': f'ERRO - {str(e)}'})
    
    # Resumo final
    print("\n\n" + "="*100)
    print("  RESUMO FINAL")
    print("="*100)
    
    print(f"\n{'Data':^12} | {'Status':^20} | {'Erro Médio CL':^15} | {'MAE CL':^15}")
    print("-" * 70)
    
    for res in resultados:
        if res['status'] == 'OK':
            print(f"{res['data']:^12} | {res['status']:^20} | {res['erro_medio_cl']:>13,.0f} MW | {res['mae_cl']:>13,.0f} MW")
        else:
            print(f"{res['data']:^12} | {res['status']:^20} | {'N/A':^15} | {'N/A':^15}")
    
    sucesso_count = sum(1 for r in resultados if r['status'] == 'OK')
    
    print("\n" + "="*100)
    print(f"  PROCESSAMENTO CONCLUÍDO: {sucesso_count}/{len(DIAS_INTERESSE)} dias processados com sucesso")
    print("="*100)
    
    print("\nArquivos gerados em:")
    print("  C:\\Users\\joao.barbosa\\Desktop\\Codigos\\Codigos ONS\\carga_liquida\\Output\\analise_dias\\")
    
    print("\nPara cada dia foram gerados 3 gráficos:")
    print("  - dia_YYYYMMDD_comparacao.png")
    print("  - dia_YYYYMMDD_erros.png")
    print("  - dia_YYYYMMDD_composicao.png")

if __name__ == '__main__':
    main()






