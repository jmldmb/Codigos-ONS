"""
Script para atualizar dados e gráficos de curtailment.

Gera:
- curtailment_raw.parquet (dados brutos processados)
- Gráficos mensais (9): pct, mwh e potencial para total, eólica e solar
- Gráficos diários dos últimos 15 dias (6): mwh e pct para total, eólica e solar
- Gráficos horários dos últimos 10 dias (6): curtailment e potencial horário para total, eólica e solar
- Parquets mensais por fonte (2): brasil_mensal_eolica.parquet e brasil_mensal_solar.parquet

Uso:
    python atualizar_curtailment.py
    python atualizar_curtailment.py --dias 30  # Últimos 30 dias ao invés de 15
    python atualizar_curtailment.py --dias 30 --dias-horario 7  # Personalizar gráficos diários e horários
"""

import sys
import argparse
from pathlib import Path

# Adicionar diretório src ao path
script_dir = Path(__file__).resolve().parent
src_dir = script_dir / "src"
sys.path.insert(0, str(src_dir))

from auxiliar.curtailment.processor import process_and_save
from auxiliar.curtailment.analysis import (
    generate_source_graphs,
    save_source_monthly_parquets,
    generate_daily_high_frequency_graphs,
    generate_hourly_graphs,
)


def main():
    parser = argparse.ArgumentParser(description="Atualiza dados e gráficos de curtailment")
    parser.add_argument(
        "--dias",
        type=int,
        default=30,
        help="Número de dias para gráficos diários (padrão: 30)",
    )
    parser.add_argument(
        "--dias-horario",
        type=int,
        default=10,
        help="Número de dias para gráficos horários (padrão: 10)",
    )
    args = parser.parse_args()

    print("=" * 80)
    print("ATUALIZAÇÃO DE CURTAILMENT")
    print("=" * 80)
    
    # Etapa 1: Processar dados brutos
    print("\n[1/5] Processando dados brutos...")
    try:
        path_raw, path_brasil = process_and_save(inicio="2021-01-01", fim="auto")
        print(f"  [OK] {path_raw.name}")
        print(f"  [OK] {path_brasil.name}")
    except Exception as e:
        print(f"  [ERRO] {e}")
        return 1
    
    # Etapa 2: Gráficos mensais
    print("\n[2/5] Gerando gráficos mensais...")
    try:
        paths = generate_source_graphs()
        print(f"  [OK] 9 gráficos gerados")
    except Exception as e:
        print(f"  [ERRO] {e}")
        return 1
    
    # Etapa 3: Gráficos diários
    print(f"\n[3/5] Gerando gráficos diários (últimos {args.dias} dias)...")
    try:
        paths_daily = generate_daily_high_frequency_graphs(n_days=args.dias)
        print(f"  [OK] 6 gráficos gerados")
    except Exception as e:
        print(f"  [ERRO] {e}")
        return 1
    
    # Etapa 4: Gráficos horários
    print(f"\n[4/5] Gerando gráficos horários (últimos {args.dias_horario} dias)...")
    try:
        paths_hourly = generate_hourly_graphs(n_days=args.dias_horario)
        print(f"  [OK] 6 gráficos gerados")
    except Exception as e:
        print(f"  [ERRO] {e}")
        return 1
    
    # Etapa 5: Parquets por fonte
    print("\n[5/5] Salvando parquets por fonte...")
    try:
        path_eolica, path_solar = save_source_monthly_parquets()
        print(f"  [OK] {path_eolica.name}")
        print(f"  [OK] {path_solar.name}")
    except Exception as e:
        print(f"  [ERRO] {e}")
        return 1
    
    print("\n" + "=" * 80)
    print("ATUALIZAÇÃO CONCLUÍDA")
    print("=" * 80)
    print(f"\nSaída: {path_raw.parent}")
    print(f"Total: 21 gráficos + 4 parquets")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())



