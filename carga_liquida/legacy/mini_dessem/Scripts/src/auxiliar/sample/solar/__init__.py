"""
Módulo de Sample Solar - Geração de Perfis Horários Solares
============================================================

Este módulo fornece ferramentas para gerar perfis horários de geração solar
baseados em dados históricos.

Autor: ONS
Data: Novembro 2024
"""

from .solar_sampler import SolarSampler, gerar_perfil_solar, gerar_dia_tipico
from .solar_distribuida_sampler import (
    SolarDistribuidaSampler, 
    gerar_perfil_solar_distribuida, 
    gerar_dia_tipico_distribuida
)

__all__ = [
    'SolarSampler', 
    'gerar_perfil_solar', 
    'gerar_dia_tipico',
    'SolarDistribuidaSampler',
    'gerar_perfil_solar_distribuida',
    'gerar_dia_tipico_distribuida'
]
__version__ = '1.1.0'  # Incrementado para refletir nova funcionalidade

