#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def configurar_e_executar():
    """Configura ambiente e executa o orquestrador do Preços de Energia BR."""
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    sys.path.insert(0, str(script_dir))
    print(f" Ambiente configurado: {script_dir}")
    import orchestrator
    orchestrator.main()

if __name__ == "__main__":
    configurar_e_executar() 