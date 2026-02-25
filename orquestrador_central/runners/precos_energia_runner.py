#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RUNNER DOS PREÇOS DE ENERGIA BR
===============================

Script para execução do orquestrador de Preços de Energia BR.
"""

import sys
from pathlib import Path

def executar_precos():
    """Executa o orquestrador de Preços de Energia BR."""
    try:
        # Navegar para o diretório do projeto
        projeto_dir = Path(__file__).parent.parent.parent / "Precos de Energia BR" / "Scripts"
        
        # Executar o executar.py
        import subprocess
        result = subprocess.run([
            sys.executable, str(projeto_dir / "executar.py")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Preços de Energia BR executado com sucesso")
            return True
        else:
            print(f"Erro nos Preços de Energia BR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Erro ao executar Preços de Energia BR: {e}")
        return False

if __name__ == "__main__":
    success = executar_precos()
    exit(0 if success else 1) 