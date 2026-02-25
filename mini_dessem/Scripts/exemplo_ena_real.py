"""
Exemplo simples: Verificar que ENA real está sendo usado nas simulações
"""

import sys
from pathlib import Path

# Adicionar diretório src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mini_dessem.simulation import _media_mensal_ena_real
from mini_dessem.data import ENA_dic

def main():
    print("\n" + "="*70)
    print("EXEMPLO: Verificando uso de ENA Real")
    print("="*70 + "\n")
    
    # Exemplo: Janeiro de 2025
    ano = 2025
    mes = 1
    
    print(f"Mes de analise: {ano}-{mes:02d}\n")
    
    # 1. Buscar valor real
    ena_real = _media_mensal_ena_real(ano, mes)
    
    # 2. Buscar valor do dicionário
    ena_dict = ENA_dic.get(ano, {}).get(mes)
    
    # 3. Mostrar qual será usado
    ena_usado = ena_real if ena_real is not None else ena_dict
    
    print(f"ENA Real disponivel:       {'Sim' if ena_real is not None else 'Nao'}")
    print(f"Valor Real:                {ena_real:,.0f} MW" if ena_real else "Valor Real:                N/A")
    print(f"Valor Dicionario:          {ena_dict:,.0f} MW" if ena_dict else "Valor Dicionario:          N/A")
    print(f"\nValor usado na simulacao:  {ena_usado:,.0f} MW")
    
    if ena_real is not None and ena_dict is not None:
        dif = ena_real - ena_dict
        dif_pct = (dif / ena_dict) * 100
        print(f"Diferenca:                 {dif:+,.0f} MW ({dif_pct:+.1f}%)")
    
    print("\n" + "="*70)
    print("\nComo funciona:")
    print("  1. Sistema tenta carregar valor real de ENA_HISTORICO.xlsx")
    print("  2. Se encontrado, usa o valor real")
    print("  3. Se nao encontrado, usa valor do dicionario (data.py)")
    print("\nArquivo de dados: Data/ENA/ENA_HISTORICO.xlsx")
    print("Coluna usada:     ena_armazenavel_regiao_mwmed")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()

