"""PLD pela pilha térmica (merit order), porte de mini_dessem/pricing.py.

    PLD = CVU da primeira usina da pilha cuja potência acumulada >= térmica_flex + inflexterm_adicional
          (se térmica_flex > 200 MW); senão CVU no ponto do adicional, com piso pld_minimo.

A pilha real (xlsx com aba 'pilha_term': potencia acumulada MW, cvu R$/MWh) vem do módulo CVU
térmicas; sem ela usa-se a pilha de exemplo abaixo (config.modelo.pilha_termica = null).
"""
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import ROOT, get_logger, load_config

logger = get_logger("preco")

PILHA_EXEMPLO = pd.DataFrame({
    "potencia": [0, 500, 1000, 1500, 2000, 3000, 4000, 5000, 7000, 10000, 15000, 20000, 30000],
    "cvu": [61, 150, 250, 350, 450, 550, 650, 750, 900, 1200, 1500, 2000, 3000],
})


def carregar_pilha(path: str | Path | None = None) -> pd.DataFrame:
    cfg = load_config()["modelo"]
    path = path or cfg.get("pilha_termica")
    if path:
        p = Path(path)
        p = p if p.is_absolute() else ROOT / p
        if p.exists():
            df = pd.read_excel(p, sheet_name="pilha_term")
            if {"potencia", "cvu"} <= set(df.columns):
                return df[["potencia", "cvu"]].sort_values("potencia").reset_index(drop=True)
            logger.warning(f"Pilha térmica sem colunas potencia/cvu: {p}")
        else:
            logger.warning(f"Pilha térmica não encontrada: {p}")
    logger.warning("Usando pilha térmica de EXEMPLO (PLD ilustrativo)")
    return PILHA_EXEMPLO.copy()


class Precificador:
    def __init__(self, pilha: pd.DataFrame | None = None):
        cfg = load_config()["modelo"]
        self.pld_min = cfg["pld_minimo"]
        self.adicional = cfg["inflexterm_adicional_mw"]
        p = pilha if pilha is not None else carregar_pilha()
        self.pot, self.cvu = p["potencia"].values.astype(float), p["cvu"].values.astype(float)

    def cvu_no_ponto(self, potencia: float) -> float:
        if potencia <= 0:
            return self.pld_min
        i = np.searchsorted(self.pot, potencia, side="left")  # primeira potência acumulada >= input
        return float(self.cvu[i]) if i < len(self.cvu) else float(self.cvu.max())

    def pld(self, termica_flex: float) -> float:
        if termica_flex > 200:
            return self.cvu_no_ponto(termica_flex + self.adicional)
        return max(self.cvu_no_ponto(self.adicional), self.pld_min)
