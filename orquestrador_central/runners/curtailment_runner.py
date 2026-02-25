#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RUNNER DO CURTAILMENT
=====================

Script para execução do orquestrador do Curtailment.
"""

import sys
from pathlib import Path

def executar_curtailment():
    """Executa o orquestrador do Curtailment."""
    try:
        # Navegar para o diretório do projeto
        projeto_dir = Path(__file__).parent.parent.parent / "Curtailment" / "Scripts"
        
        # Executar o executar.py
        import subprocess
        result = subprocess.run([
            sys.executable, str(projeto_dir / "executar.py")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Curtailment executado com sucesso")
            return True
        else:
            print(f"Erro no Curtailment: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Erro ao executar Curtailment: {e}")
        return False

if __name__ == "__main__":
    success = executar_curtailment()
    exit(0 if success else 1) 