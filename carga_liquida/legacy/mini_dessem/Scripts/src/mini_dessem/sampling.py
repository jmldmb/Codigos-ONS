"""
Funções de amostragem de séries horárias.

Implementa modelos de geração horária:
- Solar: Perfil determinístico por mês
- Eólica: Modelo estocástico AR(1) com perfil por mês
- Carga: Perfil por tipo de dia (a implementar)
"""

import numpy as np
import sys
from pathlib import Path

# Adicionar path dos módulos auxiliares
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# ===== CACHE GLOBAL PARA MODELOS =====
# Evita carregar os mesmos arquivos repetidamente (GRANDE GANHO DE PERFORMANCE!)

_CACHE_EOLICA_SAMPLER = None
_CACHE_SOLAR_SAMPLER = None
_CACHE_SOLAR_DISTRIBUIDA_SAMPLER = None

# Cache para V6 (modelo atual)
_CACHE_CARGA_V6 = None


def _flat_series(valor_medio: float, num_horas: int) -> np.ndarray:
    """Retorna uma série horária flat com o valor médio informado."""
    return np.full(int(num_horas), float(valor_medio), dtype=float)


# Novas assinaturas usadas em simulation.py
def sample_val_geolica_perfil_ar1(
    media_mensal: float,
    mes: int,
    num_horas: int,
    num_cenarios: int = 1,
    seed: int | None = None,
) -> np.ndarray:
    """
    Gera perfil horário de geração eólica usando modelo AR(1) estocástico
    
    IMPORTANTE: Sempre retorna 24 valores (1 dia), independente de num_horas
    
    Args:
        media_mensal: MWmédios (potência média do mês)
        mes: Mês (1-12)
        num_horas: IGNORADO - sempre retorna 24 horas (1 dia)
        num_cenarios: IGNORADO - Monte Carlo acontece no modelo principal
        seed: IGNORADO - cada chamada gera valores aleatórios
    
    Returns:
        Array com 24 valores (geração eólica estocástica de 1 dia)
    """
    try:
        from auxiliar.sample.eolica import EolicaSampler
        
        # Usar cache para o sampler
        global _CACHE_EOLICA_SAMPLER
        if _CACHE_EOLICA_SAMPLER is None:
            _CACHE_EOLICA_SAMPLER = EolicaSampler()
        
        sampler = _CACHE_EOLICA_SAMPLER
        
        # Sempre gera 1 dia (24 horas) estocástico
        perfil_dia = sampler.gerar_perfil_dia(mes, media_mensal, seed=None)
        
        return perfil_dia
        
    except Exception as e:
        # Fallback para flat se modelo não estiver disponível
        print(f"Aviso: Modelo eolico AR(1) nao disponivel ({e}). Usando flat.")
        return _flat_series(media_mensal, 24)


def sample_val_gersolar_perfil_ar1(
    media_diurna: float,
    mes: int,
    num_horas: int,
    num_cenarios: int = 1,
    seed: int | None = None,
) -> np.ndarray:
    """
    Gera perfil horário de geração solar usando perfil determinístico
    
    IMPORTANTE: Sempre retorna 24 valores (1 dia), independente de num_horas
    
    Args:
        media_diurna: MWmédios (potência média do mês)
        mes: Mês (1-12)
        num_horas: IGNORADO - sempre retorna 24 horas (1 dia)
        num_cenarios: IGNORADO - modelo determinístico
        seed: IGNORADO - modelo determinístico (sempre retorna o mesmo)
    
    Returns:
        Array com 24 valores (geração solar determinística de 1 dia)
    """
    try:
        from auxiliar.sample.solar import SolarSampler
        from mini_dessem.config import SOLAR_CENTRALIZADA_SHAPE_EXPONENT
        
        # Usar cache para o sampler
        global _CACHE_SOLAR_SAMPLER
        if _CACHE_SOLAR_SAMPLER is None:
            _CACHE_SOLAR_SAMPLER = SolarSampler(shape_exponent=SOLAR_CENTRALIZADA_SHAPE_EXPONENT)
        
        sampler = _CACHE_SOLAR_SAMPLER
        
        # Sempre gera 1 dia (24 horas) determinístico
        perfil_dia = sampler.gerar_perfil_dia(mes, media_diurna)
        
        return perfil_dia
        
    except Exception as e:
        # Fallback para flat se modelo não estiver disponível
        print(f"Aviso: Modelo solar nao disponivel ({e}). Usando flat.")
        return _flat_series(media_diurna, 24)


def sample_val_gersolar_distribuida_perfil_ar1(
    media_diurna: float,
    mes: int,
    num_horas: int,
    num_cenarios: int = 1,
    seed: int | None = None,
) -> np.ndarray:
    """
    Gera perfil horário de geração solar DISTRIBUÍDA usando perfil determinístico
    
    IMPORTANTE: Sempre retorna 24 valores (1 dia), independente de num_horas
    
    Diferente da centralizada:
    - Pico mais cedo (11h vs 14h)
    - Mais concentrada no meio do dia
    - Perfil próprio calculado de dados históricos
    
    Args:
        media_diurna: MWmédios (potência média do mês)
        mes: Mês (1-12)
        num_horas: IGNORADO - sempre retorna 24 horas (1 dia)
        num_cenarios: IGNORADO - modelo determinístico
        seed: IGNORADO - modelo determinístico
    
    Returns:
        Array com 24 valores (geração solar distribuída de 1 dia)
    """
    try:
        from auxiliar.sample.solar import SolarDistribuidaSampler
        from mini_dessem.config import SOLAR_DISTRIBUIDA_SHAPE_EXPONENT
        
        # Usar cache para o sampler
        global _CACHE_SOLAR_DISTRIBUIDA_SAMPLER
        if _CACHE_SOLAR_DISTRIBUIDA_SAMPLER is None:
            _CACHE_SOLAR_DISTRIBUIDA_SAMPLER = SolarDistribuidaSampler(shape_exponent=SOLAR_DISTRIBUIDA_SHAPE_EXPONENT)
        
        sampler = _CACHE_SOLAR_DISTRIBUIDA_SAMPLER
        
        # Sempre gera 1 dia (24 horas) determinístico
        perfil_dia = sampler.gerar_perfil_dia(mes, media_diurna)
        
        return perfil_dia
        
    except Exception as e:
        # Fallback para flat se modelo não estiver disponível
        print(f"Aviso: Modelo solar distribuida nao disponivel ({e}). Usando flat.")
        return _flat_series(media_diurna, 24)


def sample_val_carga_perfil_v6(
    ano: int,
    mes: int,
    dia: int,
    carga_mensal: float,
    temp_media_mensal: float,
    temp_horaria_real: dict | None = None,
    num_horas: int = 24,
    seed: int | None = None,
) -> np.ndarray:
    """Amostra carga horária usando modelo V6 (determinístico com temperatura).
    
    MODELO V6 - CARACTERÍSTICAS:
    - Regressão temperatura × carga normalizada por (mês, hora, tipo_dia)
    - Separado DU (dias úteis) vs FDS (fim de semana + feriados)
    - Constraint matemático: sum(carga_normalizada) = 24
    - Ajuste fino de viés aplicado
    - Preserva sensibilidade à temperatura (slopes)
    - Usa temperatura REAL hora-a-hora quando disponível (2023-2025)
    
    DESEMPENHO:
    - MAPE: 3.75%
    - Bias: -0.01% (praticamente zero!)
    - R²: 0.8491
    - Erro P90: -1.70%
    
    Args:
        ano: Ano da simulação
        mes: Mês (1-12)
        dia: Dia do mês
        carga_mensal: Carga média do mês (MW médios)
        temp_media_mensal: Temperatura média do mês (°C)
        temp_horaria_real: Dict {hora: temp_C} com temperaturas reais (opcional)
        num_horas: Número de horas a gerar (padrão: 24)
        seed: Seed aleatória (ignorada - modelo determinístico)
    
    Returns:
        Array com valores horários de carga (MW)
    """
    try:
        from auxiliar.sample.carga.carga_model_v6 import sample_carga_v6
        from datetime import date
        import numpy as np
        
        # Usar cache
        global _CACHE_CARGA_V6
        if _CACHE_CARGA_V6 is None:
            _CACHE_CARGA_V6 = True  # Flag simples - parâmetros são carregados internamente
        
        # Criar objeto date
        data = date(ano, mes, dia)
        
        # Gerar perfil do dia
        perfil_dia = sample_carga_v6(
            data=data,
            carga_mensal=carga_mensal,
            temp_media_mensal=temp_media_mensal,
            temp_horaria_real=temp_horaria_real,
            verificar_distorcao=False
        )
        
        # Truncar para num_horas se necessário
        if num_horas < 24:
            return perfil_dia[:num_horas]
        elif num_horas == 24:
            return perfil_dia
        else:
            # Se precisar de mais de 24h, replicar dias
            n_dias = int(np.ceil(num_horas / 24))
            serie_completa = []
            for d in range(n_dias):
                data_dia = date(ano, mes, min(dia + d, 28))  # Evitar overflow
                perfil = sample_carga_v6(data_dia, carga_mensal, temp_media_mensal)
                serie_completa.extend(perfil)
            
            return np.array(serie_completa[:num_horas])
        
    except Exception as e:
        print(f"AVISO: Modelo V6 não disponível ({e}). Usando flat.")
        return _flat_series(carga_mensal, num_horas)


# ===== FIM DO ARQUIVO =====
# Funções antigas (V3, V4, V5) removidas - agora usando apenas V6


