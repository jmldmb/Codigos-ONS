"""Utilidades comuns aos samplers: onde ficam os parâmetros treinados e helpers de perfil."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from ...config import load_config, output_dir


def params_dir() -> Path:
    return output_dir(load_config()["modelo"]["params_dir"])


def salvar_json(nome: str, obj) -> Path:
    p = params_dir() / f"{nome}.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    return p


def carregar_json(nome: str):
    p = params_dir() / f"{nome}.json"
    if not p.exists():
        raise FileNotFoundError(f"Parâmetros '{nome}' não treinados ({p}). Rode: python run.py treinar")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def janela_treino(df: pd.DataFrame, col: str = "din_instante") -> pd.DataFrame:
    ini = load_config()["modelo"]["treino"]["inicio"]
    return df[df[col] >= ini]


def perfil_proporcional_por_mes(df: pd.DataFrame, col: str) -> dict:
    """Para cada mês: {'perfil_absoluto': [24], 'perfil_proporcional': [24], 'n_meses': k}.

    Perfil absoluto = média por hora do dia dentro do mês (sobre todos os anos); proporcional = normalizado a soma 1.
    """
    df = df.dropna(subset=[col]).copy()
    df["mes"], df["hora"] = df["din_instante"].dt.month, df["din_instante"].dt.hour
    out = {}
    for mes, g in df.groupby("mes"):
        abs_ = g.groupby("hora")[col].mean().reindex(range(24)).fillna(0.0).values
        tot = abs_.sum()
        out[int(mes)] = {"perfil_absoluto": abs_.tolist(),
                         "perfil_proporcional": (abs_ / tot if tot > 0 else np.full(24, 1 / 24)).tolist(),
                         "n_meses": int(g["din_instante"].dt.to_period("M").nunique())}
    return out


def interpolar_meses_faltantes(perfis: dict, chave: str = "perfil_proporcional") -> dict:
    """Preenche meses sem dado interpolando linearmente entre os vizinhos disponíveis (circular no ano)."""
    meses = sorted(perfis)
    if len(meses) == 12 or not meses:
        return perfis
    for mes in range(1, 13):
        if mes in perfis:
            continue
        antes = max([m for m in meses if m < mes], default=max(meses))
        depois = min([m for m in meses if m > mes], default=min(meses))
        da = (mes - antes) % 12 or 12
        dd = (depois - mes) % 12 or 12
        wa, wd = dd / (da + dd), da / (da + dd)
        prop = wa * np.array(perfis[antes][chave]) + wd * np.array(perfis[depois][chave])
        perfis[mes] = {chave: (prop / prop.sum()).tolist(), "perfil_absoluto": None, "n_meses": 0, "interpolado": True}
    return perfis
