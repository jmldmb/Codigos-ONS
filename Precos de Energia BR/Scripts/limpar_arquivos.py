import os
from pathlib import Path
import shutil

ARQUIVOS = [
    "fix_imports.py", "teste_imports.py", "teste_caminhos.py", "precos_BR_corrigido.py",
    "GUIA_CORRECAO_IMPORTS.md", "GUIA_SOLUCAO_RAPIDA.md", "GUIA_CORRECAO_NOTEBOOK.md",
    "GUIA_CORRECAO_PANDAS.md", "GUIA_CORRECAO_ORQUESTRADOR.md",
    "orchestrator.ipynb", "precos_BR.ipynb", "data_ingest.ipynb", "plot_utils.ipynb", "terminal.ipynb"
]
DIRETORIOS = ["__pycache__", ".ipynb_checkpoints"]

base = Path(__file__).parent

for nome in ARQUIVOS:
    caminho = base / nome
    if caminho.exists():
        caminho.unlink()
        print(f" Arquivo deletado: {nome}")

for nome in DIRETORIOS:
    caminho = base / nome
    if caminho.exists():
        shutil.rmtree(caminho)
        print(f" Diretório deletado: {nome}")

print("\nLimpeza concluída!")