"""Feriados nacionais (calculados, sem tabela manual) e tipo de dia DU/FDS do sampler de carga.

O legado tratava sábado, domingo e feriado nacional como 'FDS' (treino); na simulação usava só o
dia da semana. Aqui o feriado entra nos dois lados.
"""
from datetime import date, timedelta
from functools import lru_cache


def pascoa(ano: int) -> date:
    """Domingo de Páscoa (algoritmo de Meeus/Jones/Butcher)."""
    a, b, c = ano % 19, ano // 100, ano % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = (h + l - 7 * m + 114) % 31 + 1
    return date(ano, mes, dia)


@lru_cache(maxsize=None)
def feriados_nacionais(ano: int) -> frozenset[date]:
    p = pascoa(ano)
    fixos = [(1, 1), (4, 21), (5, 1), (9, 7), (10, 12), (11, 2), (11, 15), (12, 25)]
    if ano >= 2024:
        fixos.append((11, 20))  # Consciência Negra, nacional desde 2024
    moveis = [p - timedelta(days=48), p - timedelta(days=47), p - timedelta(days=46),  # carnaval seg/ter/quarta de cinzas
              p - timedelta(days=2),                                                    # sexta-feira santa
              p + timedelta(days=60)]                                                   # Corpus Christi
    return frozenset([date(ano, m, d) for m, d in fixos] + moveis)


def eh_feriado(d: date) -> bool:
    return d in feriados_nacionais(d.year)


def tipo_dia(d: date) -> str:
    """'DU' (segunda a sexta não feriado) ou 'FDS' (sábado, domingo, feriado nacional)."""
    return "FDS" if d.weekday() >= 5 or eh_feriado(d) else "DU"
