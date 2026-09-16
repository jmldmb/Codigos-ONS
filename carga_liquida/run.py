"""Ponto de entrada do projeto (não requer instalação do pacote).

    python run.py baixar [dataset ...] [--force]
    python run.py processar
    python run.py analisar [hidro|cmo|diarios|curtailment ...]
    python run.py tudo
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from carga_liquida.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
