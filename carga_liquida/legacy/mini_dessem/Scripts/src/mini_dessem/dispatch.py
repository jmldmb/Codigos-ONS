"""
Funções para cálculo de despacho energético
"""

import numpy as np
from scipy.optimize import brentq
from .config import REGRESSION_PARAMS, BALANCE_TOLERANCE, SOLVER_XTOL


def calcular_val_gerhidro_fd(mes, hora, is_weekday, val_gerhidro_reservatorio, ENA_arm):
    """
    Calcula geração hidráulica fio d'água baseada em regressão múltipla.
    
    Parâmetros:
    - mes (int): Mês (1-12)
    - hora (int): Hora do dia (0-23)
    - is_weekday (bool): True se dia útil, False se fim de semana
    - val_gerhidro_reservatorio (float): Geração hidro de reservatório (MW)
    - ENA_arm (float): Energia Natural Afluente armazenada (MWmed)
    
    Retorna:
    - float: Geração hidro fio d'água (MW)
    """
    # Parâmetros da regressão
    intercept = REGRESSION_PARAMS['intercept']
    ghr = REGRESSION_PARAMS['ghr']
    ena = REGRESSION_PARAMS['ena']
    peso_mes = REGRESSION_PARAMS['peso_mes']
    peso_hora = REGRESSION_PARAMS['peso_hora']
    
    # Peso para dia da semana
    if is_weekday:
        peso_weekday = REGRESSION_PARAMS['peso_weekday']
    else:
        peso_weekday = REGRESSION_PARAMS['peso_fds']
    
    # Regressão linear
    val_gerhidro_fd = (
        intercept +
        ghr * val_gerhidro_reservatorio +
        ena * ENA_arm +
        peso_mes[mes] +
        peso_hora[hora] +
        peso_weekday
    )
    
    return val_gerhidro_fd


def _funcao_erro(val_gerhidro_reservatorio, *args):
    """
    Função de erro para o solver numérico (uso interno).
    
    Calcula a diferença entre geração total e carga.
    """
    (limite_hidro_reservatorio, val_carga, val_gereolica_pos_corte,
     val_gersolar_pos_corte, val_inflexterm, ENA_arm, mes, hora,
     is_weekday, min_hidro_reservatorio) = args
    
    # Garantir que val_gerhidro_reservatorio esteja dentro dos limites
    val_gerhidro_reservatorio = max(
        min(val_gerhidro_reservatorio, limite_hidro_reservatorio), 
        min_hidro_reservatorio
    )
    
    # Recalcular val_gerhidro_fd
    val_gerhidro_fd = calcular_val_gerhidro_fd(
        mes, hora, is_weekday, val_gerhidro_reservatorio, ENA_arm
    )
    
    # Calcular soma da geração
    soma_geracao = (
        val_gereolica_pos_corte +
        val_gersolar_pos_corte +
        val_inflexterm +
        val_gerhidro_fd +
        val_gerhidro_reservatorio
    )
    
    # Calcular diferença em relação à carga
    return soma_geracao - val_carga


def calcular_despacho_probabilistico(
    limite_hidro,
    limite_hidro_reservatorio,
    val_carga,
    val_gereolica,
    val_gersolar,
    val_inflexterm,
    ENA_arm,
    mes,
    hora,
    is_weekday,
    min_hidro_reservatorio,
    val_gersolar_centralizada=None,
    val_gersolar_distribuida=None
):
    """
    Calcula o despacho probabilístico do sistema energético.
    
    Esta função implementa a lógica de despacho com os seguintes passos:
    1. Maximiza geração hidro de reservatório
    2. Calcula geração hidro fio d'água
    3. Verifica excesso de geração
    4. Aplica curtailment se necessário (em cascata se solar separada)
    5. Calcula despacho térmico para cobrir déficit
    
    Curtailment em Cascata (quando solar separada disponível):
    - Prioridade 1: Rateio proporcional entre Eólica e Solar Centralizada
    - Prioridade 2: Solar Distribuída (só se eólica e centralizada zeradas)
    
    Parâmetros:
    - limite_hidro (float): Limite total de geração hidráulica (MW)
    - limite_hidro_reservatorio (float): Limite de geração hidro reservatório (MW)
    - val_carga (float): Carga do sistema (MW)
    - val_gereolica (float): Geração eólica disponível (MW)
    - val_gersolar (float): Geração solar TOTAL disponível (MW)
    - val_inflexterm (float): Geração térmica inflexível (MW)
    - ENA_arm (float): Energia Natural Afluente (MWmed)
    - mes (int): Mês (1-12)
    - hora (int): Hora (0-23)
    - is_weekday (bool): True se dia útil
    - min_hidro_reservatorio (float): Mínimo de geração hidro reservatório (MW)
    - val_gersolar_centralizada (float, opcional): Solar centralizada separada (MW)
    - val_gersolar_distribuida (float, opcional): Solar distribuída separada (MW)
    
    Retorna:
    - dict: Dicionário com os resultados do despacho:
        - val_term_despacho: Despacho térmico (MW)
        - val_gerhidro_reservatorio: Geração hidro reservatório (MW)
        - val_gerhidro_fd: Geração hidro fio d'água (MW)
        - curtailment: Curtailment total aplicado (MW)
        - curtailment_eolica: Curtailment só em eólica (MW)
        - curtailment_solar_cent: Curtailment só em solar centralizada (MW)
        - curtailment_solar_dist: Curtailment só em solar distribuída (MW)
        - val_gereolica_antes_corte: Geração eólica antes do corte (MW)
        - val_gereolica_depois_corte: Geração eólica depois do corte (MW)
        - val_gersolar_antes_corte: Geração solar antes do corte (MW)
        - val_gersolar_depois_corte: Geração solar depois do corte (MW)
        - val_gersolar_cent_depois_corte: Solar centralizada depois do corte (MW)
        - val_gersolar_dist_depois_corte: Solar distribuída depois do corte (MW)
        - val_erro: Flag de erro (0=OK, 1=Erro de balanceamento)
    """
    # Passo 1: Maximizar val_gerhidro_reservatorio
    val_gerhidro_reservatorio = limite_hidro_reservatorio
    
    # Passo 2: Calcular val_gerhidro_fd
    val_gerhidro_fd = calcular_val_gerhidro_fd(
        mes, hora, is_weekday, val_gerhidro_reservatorio, ENA_arm
    )
    
    # Passo 3: Calcular soma da geração total
    soma_geracao = (
        val_gereolica +
        val_gersolar +
        val_inflexterm +
        val_gerhidro_fd +
        val_gerhidro_reservatorio
    )
    
    # Passo 4: Verificar excesso de geração
    excesso_geracao = soma_geracao - val_carga
    
    # Passo 5: Ajustar val_gerhidro_reservatorio e aplicar curtailment se necessário
    curtailment = 0
    curtailment_eolica = 0
    curtailment_solar_cent = 0
    curtailment_solar_dist = 0
    
    val_gereolica_pos_corte = val_gereolica
    val_gersolar_pos_corte = val_gersolar
    
    # Separar solar se disponível
    usar_separacao_solar = (val_gersolar_centralizada is not None and 
                           val_gersolar_distribuida is not None)
    
    if usar_separacao_solar:
        val_gersolar_cent_pos_corte = val_gersolar_centralizada
        val_gersolar_dist_pos_corte = val_gersolar_distribuida
    else:
        val_gersolar_cent_pos_corte = val_gersolar
        val_gersolar_dist_pos_corte = 0
    
    if excesso_geracao > 0:
        # Reduzir val_gerhidro_reservatorio até min_hidro_reservatorio
        args_solver = (
            limite_hidro_reservatorio, val_carga, val_gereolica_pos_corte,
            val_gersolar_pos_corte, val_inflexterm, ENA_arm, mes, hora,
            is_weekday, min_hidro_reservatorio
        )
        
        try:
            val_gerhidro_reservatorio = brentq(
                _funcao_erro,
                min_hidro_reservatorio,
                limite_hidro_reservatorio,
                args=args_solver,
                xtol=SOLVER_XTOL
            )
        except ValueError:
            # Não foi possível encontrar uma solução dentro dos limites
            val_gerhidro_reservatorio = min_hidro_reservatorio
        
        # Recalcular val_gerhidro_fd com o novo val_gerhidro_reservatorio
        val_gerhidro_fd = calcular_val_gerhidro_fd(
            mes, hora, is_weekday, val_gerhidro_reservatorio, ENA_arm
        )
        
        # Recalcular soma_geracao e excesso_geracao
        soma_geracao = (
            val_gereolica_pos_corte +
            val_gersolar_pos_corte +
            val_inflexterm +
            val_gerhidro_fd +
            val_gerhidro_reservatorio
        )
        excesso_geracao = soma_geracao - val_carga
        
        # Aplicar curtailment EM CASCATA se ainda houver excesso
        if excesso_geracao > 0:
            if usar_separacao_solar:
                # NOVA LÓGICA EM CASCATA
                # Prioridade 1: Rateio proporcional entre Eólica e Solar Centralizada
                total_prioridade1 = val_gereolica_pos_corte + val_gersolar_cent_pos_corte
                
                if total_prioridade1 > 0:
                    if excesso_geracao <= total_prioridade1:
                        # Excesso pode ser absorvido só pela prioridade 1
                        proporcao_eolica = val_gereolica_pos_corte / total_prioridade1
                        proporcao_solar_cent = val_gersolar_cent_pos_corte / total_prioridade1
                        
                        reducao_eolica = proporcao_eolica * excesso_geracao
                        reducao_solar_cent = proporcao_solar_cent * excesso_geracao
                        
                        val_gereolica_pos_corte -= reducao_eolica
                        val_gersolar_cent_pos_corte -= reducao_solar_cent
                        
                        curtailment_eolica = reducao_eolica
                        curtailment_solar_cent = reducao_solar_cent
                        curtailment = excesso_geracao
                    else:
                        # Excesso maior que prioridade 1 - zerar e cortar distribuída
                        curtailment_eolica = val_gereolica_pos_corte
                        curtailment_solar_cent = val_gersolar_cent_pos_corte
                        
                        val_gereolica_pos_corte = 0
                        val_gersolar_cent_pos_corte = 0
                        
                        # Restante vem da distribuída
                        excesso_restante = excesso_geracao - total_prioridade1
                        reducao_solar_dist = min(excesso_restante, val_gersolar_dist_pos_corte)
                        
                        val_gersolar_dist_pos_corte -= reducao_solar_dist
                        curtailment_solar_dist = reducao_solar_dist
                        
                        curtailment = curtailment_eolica + curtailment_solar_cent + curtailment_solar_dist
                
                # Atualizar total solar
                val_gersolar_pos_corte = val_gersolar_cent_pos_corte + val_gersolar_dist_pos_corte
                
            else:
                # LÓGICA ANTIGA (compatibilidade): Rateio proporcional total
                total_renovavel = val_gereolica_pos_corte + val_gersolar_pos_corte
                if total_renovavel > 0:
                    proporcao_eolica = val_gereolica_pos_corte / total_renovavel
                    proporcao_solar = val_gersolar_pos_corte / total_renovavel
                    
                    reducao_eolica = proporcao_eolica * excesso_geracao
                    reducao_solar = proporcao_solar * excesso_geracao
                    
                    val_gereolica_pos_corte -= reducao_eolica
                    val_gersolar_pos_corte -= reducao_solar
                    
                    curtailment_eolica = reducao_eolica
                    curtailment_solar_cent = reducao_solar  # Todo solar tratado como centralizada
                    curtailment = excesso_geracao
            
            # Garantir que as gerações não sejam negativas
            val_gereolica_pos_corte = max(val_gereolica_pos_corte, 0)
            val_gersolar_pos_corte = max(val_gersolar_pos_corte, 0)
            
            if usar_separacao_solar:
                val_gersolar_cent_pos_corte = max(val_gersolar_cent_pos_corte, 0)
                val_gersolar_dist_pos_corte = max(val_gersolar_dist_pos_corte, 0)
    
    # Passo 6: Recalcular soma da geração após ajustes
    soma_geracao = (
        val_gereolica_pos_corte +
        val_gersolar_pos_corte +
        val_inflexterm +
        val_gerhidro_fd +
        val_gerhidro_reservatorio
    )
    
    # Passo 7: Verificar déficit de geração
    deficit_geracao = val_carga - soma_geracao
    
    if deficit_geracao > 0:
        # Tentar aumentar val_gerhidro_reservatorio até o limite
        incremento_possivel = limite_hidro_reservatorio - val_gerhidro_reservatorio
        incremento_necessario = min(deficit_geracao, incremento_possivel)
        val_gerhidro_reservatorio += incremento_necessario
        deficit_geracao -= incremento_necessario
        
        # Recalcular val_gerhidro_fd após ajustar val_gerhidro_reservatorio
        val_gerhidro_fd = calcular_val_gerhidro_fd(
            mes, hora, is_weekday, val_gerhidro_reservatorio, ENA_arm
        )
        
        # Recalcular soma_geracao e deficit_geracao
        soma_geracao = (
            val_gereolica_pos_corte +
            val_gersolar_pos_corte +
            val_inflexterm +
            val_gerhidro_fd +
            val_gerhidro_reservatorio
        )
        deficit_geracao = val_carga - soma_geracao
    
    # Passo 8: Utilizar val_term_despacho se ainda houver déficit
    if deficit_geracao > 0:
        val_term_despacho = deficit_geracao
    else:
        val_term_despacho = 0
    
    # Passo 9: Garantir que nenhuma variável é negativa
    variaveis = [
        val_term_despacho,
        val_gerhidro_reservatorio,
        val_gerhidro_fd,
        val_gereolica_pos_corte,
        val_gersolar_pos_corte
    ]
    if any(v < 0 for v in variaveis):
        return None  # Se houver valores negativos
    
    # Passo 10: Verificar a equação de balanceamento
    balanceamento = (
        val_gereolica_pos_corte +
        val_gersolar_pos_corte +
        val_inflexterm +
        val_gerhidro_fd +
        val_gerhidro_reservatorio +
        val_term_despacho
    )
    
    # Flag de erro se balanceamento não for satisfeito
    val_erro = 0
    if abs(balanceamento - val_carga) > BALANCE_TOLERANCE:
        val_erro = 1
    
    # Outputs
    resultado = {
        'val_term_despacho': val_term_despacho,
        'val_gerhidro_reservatorio': val_gerhidro_reservatorio,
        'val_gerhidro_fd': val_gerhidro_fd,
        'curtailment': curtailment,
        'curtailment_eolica': curtailment_eolica,
        'curtailment_solar_cent': curtailment_solar_cent,
        'curtailment_solar_dist': curtailment_solar_dist,
        'val_gereolica_antes_corte': val_gereolica,
        'val_gereolica_depois_corte': val_gereolica_pos_corte,
        'val_gersolar_antes_corte': val_gersolar,
        'val_gersolar_depois_corte': val_gersolar_pos_corte,
        'val_erro': val_erro
    }
    
    # Adicionar componentes solares separadas se disponível
    if usar_separacao_solar:
        resultado['val_gersolar_cent_antes_corte'] = val_gersolar_centralizada
        resultado['val_gersolar_cent_depois_corte'] = val_gersolar_cent_pos_corte
        resultado['val_gersolar_dist_antes_corte'] = val_gersolar_distribuida
        resultado['val_gersolar_dist_depois_corte'] = val_gersolar_dist_pos_corte
    
    return resultado



