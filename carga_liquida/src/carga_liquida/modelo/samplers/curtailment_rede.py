"""Curtailment de REDE (razões CNF/REL do COFF) da eólica e da solar centralizada: premissa mensal exógena.

O despacho reproduz o corte energético (ENE: sobra de energia no SIN com hidro no mínimo e térmica zerada).
O corte de rede é outra coisa: restrições regionais de transmissão/confiabilidade (quase todo no NE) que
ocorrem mesmo quando o SIN precisa da energia — um balanço agregado não o vê. Entra como premissa mensal
(observada no histórico; cenário em config/projecoes.yaml), como a térmica flexível. Aqui só se distribui
essa média nas 24 horas pelo perfil observado por (mês, hora), limitado ao potencial da hora:
o corte de rede não é flat — pica às 7–9h (rampa solar com o NE exportando), ~20 % do potencial eólico
contra ~6 % de madrugada.

Treino: `python run.py treinar curtailment_rede` -> params_dir/curtailment_rede.json
"""
import numpy as np

from ...config import get_logger
from ...dados import ons
from ._base import carregar_json, janela_treino, salvar_json

logger = get_logger("sampler.curtailment_rede")
NOME = "curtailment_rede"
FONTES = ("eolica", "solar")
MIN_MW_PERFIL = 100  # meses com corte de rede médio abaixo disto não entram no perfil (ruído)


def treinar() -> dict:
    out = {}
    for fonte in FONTES:
        df = janela_treino(ons.carregar_coff_horario(fonte))
        df["mes"], df["hora"] = df["din_instante"].dt.month, df["din_instante"].dt.hour
        df["media_mes"] = df.groupby([df["din_instante"].dt.year, "mes"])["corte_rede_mw"].transform("mean")
        d = df[df["media_mes"] >= MIN_MW_PERFIL]
        perfis = {}
        for mes, g in d.groupby("mes"):
            p = g.groupby("hora")["corte_rede_mw"].mean().reindex(range(24)).fillna(0.0).values
            if p.mean() > 0:
                perfis[int(mes)] = {"perfil": (p / p.mean()).tolist(), "n_meses": int(g["din_instante"].dt.to_period("M").nunique())}
        medio = np.mean([v["perfil"] for v in perfis.values()], axis=0) if perfis else np.ones(24)
        faltantes = [m for m in range(1, 13) if m not in perfis]
        for m in faltantes:
            perfis[m] = {"perfil": (medio / medio.mean()).tolist(), "n_meses": 0, "interpolado": True}
        logger.info(f"  {fonte}: {12 - len(faltantes)} meses com perfil próprio; média dos meses em {faltantes}; "
                    f"pico {int(np.argmax(medio))}h ({medio.max():.2f}× a média)")
        out[fonte] = {"meta": {"periodo": f"{df['din_instante'].min()} a {df['din_instante'].max()}", "min_mw_perfil": MIN_MW_PERFIL},
                      "perfis": {str(k): v for k, v in sorted(perfis.items())}}
    salvar_json(NOME, out)
    return out


class CurtailmentRedeSampler:
    def __init__(self, params: dict | None = None):
        p = params or carregar_json(NOME)
        self.perfis = {f: {int(k): np.array(v["perfil"]) for k, v in p[f]["perfis"].items()} for f in FONTES}

    def gerar_dia(self, fonte: str, mes: int, mw_medios: float, potencial: np.ndarray) -> np.ndarray:
        """24 valores (MW) de corte de rede com média = mw_medios, limitados ao potencial da hora.
        Quando o perfil estoura o potencial em alguma hora, o excedente é redistribuído (escala k) nas demais."""
        if not mw_medios or mw_medios <= 0:
            return np.zeros(24)
        perfil = self.perfis[fonte][mes]
        alvo = min(float(mw_medios), float(potencial.mean()))
        k, corte = 1.0, np.zeros(24)
        for _ in range(6):
            corte = np.minimum(mw_medios * perfil * k, potencial)
            if corte.mean() >= 0.995 * alvo:
                break
            k *= alvo / max(corte.mean(), 1e-9)
        return corte
