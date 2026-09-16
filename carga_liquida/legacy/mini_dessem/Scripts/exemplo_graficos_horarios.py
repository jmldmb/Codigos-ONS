"""
Exemplo de uso direto da função de gráficos horários de curtailment.

Este script demonstra como gerar apenas os gráficos horários sem executar
todo o pipeline de atualização.
"""

import sys
from pathlib import Path

# Adicionar diretório src ao path
script_dir = Path(__file__).resolve().parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

from auxiliar.curtailment.analysis import generate_hourly_graphs


def main():
    """Gera gráficos horários de curtailment."""
    print("=" * 80)
    print("GERANDO GRÁFICOS HORÁRIOS DE CURTAILMENT")
    print("=" * 80)
    
    # Você pode personalizar o número de dias
    n_days = 10  # Altere para o número de dias desejado
    
    print(f"\n[*] Gerando gráficos horários dos últimos {n_days} dias...")
    try:
        paths = generate_hourly_graphs(n_days=n_days)
        
        print(f"\n[OK] 6 gráficos gerados com sucesso:")
        print(f"\n  Total:")
        print(f"    - Curtailment: {paths[0]}")
        print(f"    - Potencial:   {paths[1]}")
        print(f"\n  Eólica:")
        print(f"    - Curtailment: {paths[2]}")
        print(f"    - Potencial:   {paths[3]}")
        print(f"\n  Solar:")
        print(f"    - Curtailment: {paths[4]}")
        print(f"    - Potencial:   {paths[5]}")
        
    except Exception as e:
        print(f"\n[ERRO] Falha ao gerar gráficos: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\n" + "=" * 80)
    print("CONCLUÍDO")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

