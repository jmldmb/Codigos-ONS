"""PLD pela pilha térmica (merit order), porte de mini_dessem/pricing.py.

    PLD = CVU da primeira usina da pilha cuja potência acumulada >= térmica_flex + inflexterm_adicional
          (se térmica_flex > 200 MW); senão CVU no ponto do adicional, com piso pld_minimo.

A pilha de cada mês vem de modelo/pilha_termica.py (CVU semanal x capacidade, dados ONS). Um xlsx com
aba 'pilha_term' (config.modelo.pilha_termica_xlsx) substitui todas; sem nenhum dos dois, pilha de exemplo.
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


def carregar_pilha_xlsx(path: str | Path | None = None) -> pd.DataFrame | None:
    cfg = load_config()["modelo"]
    path = path or cfg.get("pilha_termica_xlsx")
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
    return None


class Precificador:
    """pld(termica_flex, ano, mes): usa a pilha fixa (xlsx/DataFrame) se houver, senão a pilha mensal dos dados."""

    def __init__(self, pilha: pd.DataFrame | None = None):
        cfg = load_config()["modelo"]
        self.pld_min = cfg["pld_minimo"]
        self.adicional = cfg["inflexterm_adicional_mw"]
        self.fixa = pilha if pilha is not None else carregar_pilha_xlsx()
        if self.fixa is None:
            try:
                from .pilha_termica import montar_todas
                montar_todas()
            except FileNotFoundError as e:
                logger.warning(f"{e}; usando pilha térmica de EXEMPLO (PLD ilustrativo)")
                self.fixa = PILHA_EXEMPLO.copy()
        self._cache = {}

    def _pilha(self, ano: int, mes: int) -> tuple[np.ndarray, np.ndarray]:
        key = None if self.fixa is not None else (ano, mes)
        if key not in self._cache:
            if self.fixa is not None:
                p = self.fixa
            else:
                from .pilha_termica import pilha
                p = pilha(ano, mes)
            self._cache[key] = (p["potencia"].values.astype(float), p["cvu"].values.astype(float))
        return self._cache[key]

    def cvu_no_ponto(self, potencia: float, ano: int = 0, mes: int = 0) -> float:
        if potencia <= 0:
            return self.pld_min
        pot, cvu = self._pilha(ano, mes)
        i = np.searchsorted(pot, potencia, side="left")  # primeira potência acumulada >= input
        return float(cvu[i]) if i < len(cvu) else float(cvu.max())

    def pld(self, termica_flex: float, ano: int = 0, mes: int = 0) -> float:
        if termica_flex > 200:
            return self.cvu_no_ponto(termica_flex + self.adicional, ano, mes)
        return max(self.cvu_no_ponto(self.adicional, ano, mes), self.pld_min)
