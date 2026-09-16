"""
Runner para a análise histórica dos dados em Data/raw_data.

Uso:
    python run_historical_analysis.py
"""

from pathlib import Path
import sys

# Garantir que src esteja no path (subir dois níveis: analise_historico -> src -> Scripts -> src)
from pathlib import Path as _P
SCRIPT_DIR = _P(__file__).parent.parent.parent
sys.path.insert(0, str(SCRIPT_DIR / 'src'))

from mini_dessem.historical_analysis import gerar_analise_historica
from mini_dessem.config import OUTPUT_DIR


def main() -> int:
    out_dir = OUTPUT_DIR.parent / 'analise_historica'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Gerando análise histórica em: {out_dir}")
    
    gerar_analise_historica(output_dir=out_dir)
    
    print(f"\nAnálise concluída! Resultados em: {out_dir}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

