"""
Configurações e parâmetros do sistema
"""

import os
from pathlib import Path

# Diretórios base
# __file__ está em: Scripts/src/mini_dessem/config.py
# Precisamos subir 3 níveis para chegar na raiz do projeto (mini_dessem/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "Data" / "processed_data"

# Diretórios de parâmetros dos modelos
MODEL_PARAMS_EOLICA = DATA_DIR / "model_parametros_eolica"
MODEL_PARAMS_SOLAR = DATA_DIR / "model_parametros_solar"
MODEL_PARAMS_CARGA_SEMANA = DATA_DIR / "model_parametros_carga_semana"
MODEL_PARAMS_CARGA_FDS = DATA_DIR / "model_parametros_carga_fds"

# Diretório de output
OUTPUT_DIR = BASE_DIR / "output" / "resultados"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Parâmetros de simulação
DEFAULT_NUM_SIMULATIONS = 6
DEFAULT_RANDOM_STATE = None

# Anos e meses para simular (EDITE AQUI)
ANOS_SIMULAR = [2022,2023,2024,2025,2026,2027,2028]  # Quais anos simular
MESES_SIMULAR = list(range(1, 13))  # Quais meses simular (1 a 12)

# Limites operacionais
LIMITE_HIDRO = 80000  # MW
LIMITE_HIDRO_RESERVATORIO = 42000  # MW
MIN_HIDRO_RESERVATORIO = 14500  # MW

# Parâmetros de preço
PLD_MINIMO = 61  # R$/MWh
VALOR_FIXO_INFLEXTERM = 3500 # MW adicional nos meses específicos
MESES_INFLEXTERM_ADICIONAL = [11, 12, 1, 2, 3]  # Junho a Outubro

# Parâmetros de regressão para hidro FD
# CALIBRADOS V2 (Otimização) - MAE: 1,857 MW | MAPE: 8.08% | R²: 0.8887
# Melhoria: -327 MW (-15.0%) vs parâmetros originais
REGRESSION_PARAMS = {
    'intercept': 3563,
    'ghr': 0.33,
    'ena': 0.15,
    'peso_mes': {
        1: 1944, 2: 2737, 3: 4870, 4: 6687, 5: 5241, 6: 2677,
        7: 1062, 8: -467, 9: -1353, 10: -2544, 11: -1036, 12: 0
    },
    'peso_hora': {
        0: 937, 1: 447, 2: 69, 3: -148, 4: -216, 5: -154,
        6: -257, 7: -552, 8: -753, 9: -809, 10: -818, 11: -797,
        12: -876, 13: -428, 14: 105, 15: 732, 16: 1489, 17: 2520,
        18: 3564, 19: 3602, 20: 3125, 21: 2621, 22: 2215, 23: 1708
    },
    'peso_weekday': 1352,
    'peso_fds': 1523
}

# Tolerância para balanceamento
BALANCE_TOLERANCE = 1e-3

# Solver settings
SOLVER_XTOL = 1e-6

# Ajuste de perfil solar (shape)
# Geração solar é separada em CENTRALIZADA e DISTRIBUÍDA
# Cada uma tem perfil horário e configuração próprios

# Geração Solar CENTRALIZADA (usinas de grande porte, ~36% do total)
# Perfil: Pico às 14h, mais espalhado ao longo do dia
SOLAR_CENTRALIZADA_SHAPE_EXPONENT = 1.5  # Acentua pico, suaviza rampas

# Geração Solar DISTRIBUÍDA (telhados, pequenos sistemas, ~64% do total)
# Perfil: Pico às 11h (3h mais cedo!), mais concentrado
SOLAR_DISTRIBUIDA_SHAPE_EXPONENT = 1.0  # Perfil já é naturalmente mais concentrado

# Flag para habilitar separação centralizada/distribuída
# True = Modela separadamente (mais preciso)
# False = Usa apenas total (compatibilidade com versão anterior)
SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA = True

# ===== VERSÃO DO SAMPLER DE CARGA =====
# v6: Modelo com regressão temperatura × carga normalizada por (mês, hora, tipo_dia)
#     Separado DU vs FDS, com constraint matemático, ajuste fino de viés
#     DESEMPENHO: MAPE 3.75%, Bias -0.01%, R² 0.8491, Erro P90 -1.70%
USE_CARGA_SAMPLER_V6 = True   # Usar v6 (recomendado!)

