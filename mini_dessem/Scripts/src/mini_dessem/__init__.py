"""
Mini DESSEM - Sistema de Simulação de Despacho Energético
"""

__version__ = "1.0.0"
__author__ = "João Barbosa"

from .data import (
    capacidade_eolica_total_dic,
    capacidade_solar_total_dic,
    carga_total_dic,
    ENA_dic,
    val_inflexterm_dic,
    val_inflexterm_ex_pct_dic
)

from .sampling import (
    sample_val_geolica_perfil_ar1,
    sample_val_gersolar_perfil_ar1,
    sample_val_carga_perfil_v6
)

from .dispatch import (
    calcular_val_gerhidro_fd,
    calcular_despacho_probabilistico
)

from .simulation import run_simulation
from .pricing import carregar_pilha_termica, encontrar_cvu_proximo, calcular_pld
from .visualization import gerar_todos_graficos

__all__ = [
    'capacidade_eolica_total_dic',
    'capacidade_solar_total_dic',
    'carga_total_dic',
    'ENA_dic',
    'val_inflexterm_dic',
    'val_inflexterm_ex_pct_dic',
    'sample_val_geolica_perfil_ar1',
    'sample_val_gersolar_perfil_ar1',
    'sample_val_carga_perfil_v6',
    'calcular_val_gerhidro_fd',
    'calcular_despacho_probabilistico',
    'run_simulation',
    'carregar_pilha_termica',
    'encontrar_cvu_proximo',
    'calcular_pld',
    'gerar_todos_graficos'
]

