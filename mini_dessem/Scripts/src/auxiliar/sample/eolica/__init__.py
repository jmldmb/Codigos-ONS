"""
Módulo de Sample Eólica - Geração Estocástica AR(1) + Perfil
=============================================================

Este módulo fornece ferramentas para gerar perfis horários estocásticos
de geração eólica baseados em modelo AR(1) e dados históricos.

Autor: ONS
Data: Novembro 2024
"""

from .eolica_sampler import EolicaSampler, gerar_perfil_eolico

__all__ = ['EolicaSampler', 'gerar_perfil_eolico']
__version__ = '1.0.0'








