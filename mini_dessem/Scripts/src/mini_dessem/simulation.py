"""
Funções para executar simulações Monte Carlo do sistema energético
"""

import pandas as pd
import numpy as np
import calendar
import time
from datetime import date, timedelta
from .data import (
    capacidade_eolica_total_dic,
    capacidade_solar_total_dic,
    geracao_solar_centralizada_dic,
    geracao_solar_distribuida_dic,
    carga_total_dic,
    ENA_dic,
    val_inflexterm_dic,
    val_inflexterm_ex_pct_dic,
    eh_dado_historico
)
from .sampling import (
    sample_val_geolica_perfil_ar1,
    sample_val_gersolar_perfil_ar1,
    sample_val_gersolar_distribuida_perfil_ar1,
    sample_val_carga_perfil_v6
)
from .dispatch import calcular_despacho_probabilistico
from .pricing import calcular_pld, carregar_pilha_termica
from .temperatura_loader import obter_temperatura_mensal, obter_temperaturas_dia
from .config import (
    MODEL_PARAMS_EOLICA,
    USE_CARGA_SAMPLER_V6,
    MODEL_PARAMS_SOLAR,
    MODEL_PARAMS_CARGA_SEMANA,
    MODEL_PARAMS_CARGA_FDS,
    LIMITE_HIDRO,
    LIMITE_HIDRO_RESERVATORIO,
    MIN_HIDRO_RESERVATORIO,
    VALOR_FIXO_INFLEXTERM,
    MESES_INFLEXTERM_ADICIONAL,
    DEFAULT_NUM_SIMULATIONS,
    SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA
)
from pathlib import Path


# Cache de médias reais por ano para evitar releituras
_CACHE_MEDIA_EOLICA_REAL_ANO = {}
_CACHE_REAL_ANO = {}
_CACHE_ENA_REAL = None


def _formatar_tempo(segundos):
    """Formata tempo em segundos para string legível."""
    if segundos < 60:
        return f"{segundos:.0f}s"
    elif segundos < 3600:
        mins = segundos / 60
        return f"{mins:.1f}min"
    else:
        horas = segundos / 3600
        return f"{horas:.1f}h"


def _barra_progresso(atual, total, largura=50):
    """Cria uma barra de progresso visual."""
    if total == 0:
        return "[" + " " * largura + "]"
    
    pct = atual / total
    preenchido = int(largura * pct)
    vazio = largura - preenchido
    
    if vazio > 0:
        return "[" + "█" * preenchido + ">" + "·" * (vazio - 1) + "]"
    else:
        return "[" + "█" * largura + "]"


def _imprimir_progresso(contador, total_horas, inicio_tempo, mes_atual, ano_atual, sim_atual, num_sims):
    """Imprime linha de progresso formatada."""
    tempo_decorrido = time.time() - inicio_tempo
    pct = (contador / total_horas) * 100
    
    # Calcular tempo estimado restante
    if contador > 0:
        velocidade = contador / tempo_decorrido  # horas processadas por segundo
        horas_restantes = total_horas - contador
        tempo_restante = horas_restantes / velocidade if velocidade > 0 else 0
    else:
        tempo_restante = 0
    
    # Criar barra de progresso
    barra = _barra_progresso(contador, total_horas)
    
    # Nome do mês
    nome_mes = ["", "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
                "Jul", "Ago", "Set", "Out", "Nov", "Dez"][mes_atual]
    
    # Linha de progresso
    print(f"\r{barra} {pct:5.1f}% | {contador:,}/{total_horas:,} horas | "
          f"{nome_mes}/{ano_atual} Sim {sim_atual}/{num_sims} | "
          f"Tempo: {_formatar_tempo(tempo_decorrido)} | "
          f"Restante: ~{_formatar_tempo(tempo_restante)}", end="", flush=True)


def _media_mensal_eolica_real(ano: int, mes: int):
    """Tenta ler a média horária de eólica (SIN) do raw_data do próprio projeto.
    Fallback: retorna None se não conseguir.
    """
    try:
        base_scripts = Path(__file__).resolve().parent.parent.parent.parent
        xlsx = base_scripts / 'Data' / 'raw_data' / f'BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx'
        if not xlsx.exists():
            return None
        if ano not in _CACHE_MEDIA_EOLICA_REAL_ANO:
            df = pd.read_excel(xlsx, sheet_name=0)
            df = df[df['id_subsistema'] == 'SIN'].copy()
            df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
            df = df.dropna(subset=['din_instante'])
            df['ano'] = df['din_instante'].dt.year
            df['mes'] = df['din_instante'].dt.month
            medias = df.groupby(['ano', 'mes'])['val_gereolica'].mean()
            _CACHE_MEDIA_EOLICA_REAL_ANO[ano] = medias
        medias = _CACHE_MEDIA_EOLICA_REAL_ANO.get(ano)
        val = float(medias.get((ano, mes))) if medias is not None else None
        return val
    except Exception:
        return None


def _load_real_year(ano: int) -> pd.DataFrame | None:
    try:
        if ano in _CACHE_REAL_ANO:
            return _CACHE_REAL_ANO[ano]
        base_scripts = Path(__file__).resolve().parent.parent.parent.parent
        xlsx = base_scripts / 'Data' / 'raw_data' / f'BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx'
        if not xlsx.exists():
            return None
        df = pd.read_excel(xlsx, sheet_name=0)
        # Filtrar SIN com robustez para variação de coluna
        id_col = None
        for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
            if cand in df.columns:
                id_col = cand
                break
        if id_col is not None:
            df[id_col] = df[id_col].astype(str).str.upper().str.strip()
            df = df[df[id_col] == 'SIN'].copy()
        df = pd.read_excel(xlsx, sheet_name=0)
        id_col = None
        for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
            if cand in df.columns:
                id_col = cand
                break
        if id_col is not None:
            df[id_col] = df[id_col].astype(str).str.upper().str.strip()
            df = df[df[id_col] == 'SIN'].copy()
        df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
        df = df.dropna(subset=['din_instante'])
        df['ano'] = df['din_instante'].dt.year
        df['mes'] = df['din_instante'].dt.month
        df['hora'] = df['din_instante'].dt.hour
        for c in ['val_gereolica','val_gersolar','val_carga','val_gertermica','val_gerhidraulica']:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors='coerce')
        _CACHE_REAL_ANO[ano] = df
        return df
    except Exception:
        return None


def _media_mensal_solar_real(ano: int, mes: int):
    """Retorna a média 24h mensal da geração solar (SIN)."""
    df = _load_real_year(ano)
    if df is None:
        return None
    dfm = df[df['mes'] == mes]
    if len(dfm) == 0:
        return None
    val = pd.to_numeric(dfm['val_gersolar'], errors='coerce').mean()
    return None if pd.isna(val) else float(val)


def _media_mensal_carga_real(ano: int, mes: int):
    df = _load_real_year(ano)
    if df is None:
        return None
    dfm = df[df['mes'] == mes]
    if len(dfm) == 0:
        return None
    val = pd.to_numeric(dfm['val_carga'], errors='coerce').mean()
    return None if pd.isna(val) else float(val)


def _load_ena_historico():
    """Carrega dados históricos de ENA do arquivo Excel (com cache)."""
    global _CACHE_ENA_REAL
    
    if _CACHE_ENA_REAL is not None:
        return _CACHE_ENA_REAL
    
    try:
        base_scripts = Path(__file__).resolve().parent.parent.parent.parent
        xlsx = base_scripts / 'Data' / 'ENA' / 'ENA_HISTORICO.xlsx'
        
        if not xlsx.exists():
            return None
        
        df = pd.read_excel(xlsx)
        
        # Verificar se as colunas necessárias existem
        if 'ena_armazenavel_regiao_mwmed' not in df.columns:
            print("[AVISO] Coluna 'ena_armazenavel_regiao_mwmed' não encontrada em ENA_HISTORICO.xlsx")
            return None
        
        # Garantir que Data seja datetime
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df = df.dropna(subset=['Data'])
        
        # Extrair ano e mês se não existirem
        if 'Ano' not in df.columns:
            df['Ano'] = df['Data'].dt.year
        if 'Mês' not in df.columns or 'M�s' in df.columns:
            # Tratar possível problema de encoding com Mês
            df['mes'] = df['Data'].dt.month
        else:
            df['mes'] = df['Mês']
        
        df['ano'] = df['Ano']
        
        # Converter coluna de ENA para numérico
        df['ena_armazenavel_regiao_mwmed'] = pd.to_numeric(
            df['ena_armazenavel_regiao_mwmed'], 
            errors='coerce'
        )
        
        # Cachear o DataFrame
        _CACHE_ENA_REAL = df
        
        return df
        
    except Exception as e:
        print(f"[AVISO] Erro ao carregar ENA_HISTORICO.xlsx: {e}")
        return None


def _media_mensal_ena_real(ano: int, mes: int):
    """Retorna a média mensal de ENA armazenável real (MWmed)."""
    df = _load_ena_historico()
    
    if df is None:
        return None
    
    # Filtrar por ano e mês
    dfm = df[(df['ano'] == ano) & (df['mes'] == mes)]
    
    if len(dfm) == 0:
        return None
    
    # Calcular média mensal
    val = dfm['ena_armazenavel_regiao_mwmed'].mean()
    
    return None if pd.isna(val) else float(val)


def aplicar_ajuste_inflexterm(val_inflexterm_dic_original, valor_fixo, meses_especificos):
    """
    Aplica ajuste nos valores de inflexibilidade térmica para meses específicos.
    
    IMPORTANTE: O ajuste só é aplicado em dados PROJETADOS, não em dados históricos reais.
    
    Parâmetros:
    - val_inflexterm_dic_original (dict): Dicionário original
    - valor_fixo (float): Valor a adicionar (MW)
    - meses_especificos (list): Lista de meses para aplicar o ajuste
    
    Retorna:
    - dict: Dicionário ajustado (cópia do original com ajustes aplicados)
    """
    import copy
    val_inflexterm_dic_ajustado = copy.deepcopy(val_inflexterm_dic_original)
    
    for ano in val_inflexterm_dic_ajustado:
        for mes in val_inflexterm_dic_ajustado[ano]:
            # Só aplica o ajuste se:
            # 1. O mês está nos meses específicos E
            # 2. NÃO é um dado histórico (é projeção)
            if mes in meses_especificos and not eh_dado_historico(ano, mes):
                val_inflexterm_dic_ajustado[ano][mes] += valor_fixo
    
    return val_inflexterm_dic_ajustado


def run_simulation(
    num_simulations=DEFAULT_NUM_SIMULATIONS,
    anos=range(2022, 2028),
    meses=range(1, 13),
    is_weekday=True,
    pilha_termica=None,
    verbose=True
):
    """
    Executa simulação Monte Carlo do sistema energético.
    
    NOVA VERSÃO: Cada simulação gera um MÊS COMPLETO com dias úteis e FDS misturados.
    
    Parâmetros:
    - num_simulations (int): Número de cenários (meses completos) por mês/ano
    - anos (range/list): Anos para simular
    - meses (range/list): Meses para simular
    - is_weekday (bool): IGNORADO (mantido para compatibilidade)
    - pilha_termica (list): Pilha térmica (merit order). Se None, usa exemplo.
    - verbose (bool): Se True, imprime progresso
    
    Retorna:
    - pd.DataFrame: DataFrame com resultados da simulação
    """
    # Aplicar ajuste de inflexibilidade térmica
    val_inflexterm_dic_ajustado = aplicar_ajuste_inflexterm(
        val_inflexterm_dic,
        VALOR_FIXO_INFLEXTERM,
        MESES_INFLEXTERM_ADICIONAL
    )
    
    # Criar pilha térmica se não fornecida
    if pilha_termica is None:
        pilha_termica = carregar_pilha_termica()
        if verbose:
            print("[OK] Pilha termica carregada.")
    
    # Arrays para armazenar os resultados
    data = []
    
    # Calcular total de horas (não mais iterações)
    total_horas = 0
    for ano in anos:
        for mes in meses:
            num_dias = calendar.monthrange(ano, mes)[1]
            total_horas += num_simulations * num_dias * 24
    
    contador = 0
    inicio_tempo = time.time()
    
    if verbose:
        print(f"Configuracao da Simulacao:")
        print(f"   Cenarios por mes/ano: {num_simulations}")
        print(f"   Anos: {list(anos)}")
        print(f"   Meses: {list(meses)}")
        print(f"   Cada cenario simula o MES COMPLETO (dias uteis + FDS)")
        print(f"   Total estimado de registros: {total_horas:,}")
        print(f"\nIniciando simulacao...")
        print("-" * 70)
        print()
    
    for ano in anos:
        for mes in meses:
            # Obter parâmetros para o mês/ano
            capacidade_eolica_total = capacidade_eolica_total_dic.get(ano, {}).get(mes)
            capacidade_solar_total = capacidade_solar_total_dic.get(ano, {}).get(mes)
            carga_total = carga_total_dic.get(ano, {}).get(mes)
            val_inflexterm = val_inflexterm_dic_ajustado.get(ano, {}).get(mes)
            # ENA: Usar valor real se disponível, senão usar valor do dicionário
            ena_real = _media_mensal_ena_real(ano, mes)
            ENA_arm = ena_real if ena_real is not None else ENA_dic.get(ano, {}).get(mes)
            val_inflexterm_ex_pct = val_inflexterm_ex_pct_dic.get(ano, {}).get(mes)
            
            # Verificar se todos os parâmetros estão disponíveis
            if any(v is None for v in [capacidade_eolica_total, capacidade_solar_total, 
                                       carga_total, val_inflexterm, ENA_arm]):
                if verbose:
                    print(f"[AVISO] Dados faltando para {ano}-{mes:02d}, pulando...")
                continue
            
            # Calcular médias mensais/diurnas a partir do realizado quando disponível
            # Eólica: média 24h
            # OBS: capacidade_eolica_total_dic já contém MÉDIAS de geração, não capacidades!
            media_eolica_real = _media_mensal_eolica_real(ano, mes)
            media_mensal_eolica = media_eolica_real if media_eolica_real is not None else capacidade_eolica_total
            # Solar: valores são MWmédios (média 24h incluindo períodos noturnos com zero)
            # OBS: capacidade_solar_total_dic já contém MWmédios, não capacidades!
            # O sampler solar já distribui corretamente a energia apenas nas horas de sol
            media_solar_24h_real = _media_mensal_solar_real(ano, mes)
            if media_solar_24h_real is not None:
                # Dados reais: usar média 24h diretamente (sampler aplica perfil diurno)
                media_diurna_solar = media_solar_24h_real
            else:
                # Projeção: usar valores de data.py diretamente (também são médias 24h)
                media_diurna_solar = capacidade_solar_total
            # Carga: média 24h
            media_carga_real = _media_mensal_carga_real(ano, mes)
            media_mensal_carga = media_carga_real if media_carga_real is not None else carga_total
            
            # Obter estrutura do mês
            num_dias_mes = calendar.monthrange(ano, mes)[1]
            
            # Construir lista de dias com tipos
            estrutura_mes = []
            dias_uteis = 0
            dias_fds = 0
            
            for dia in range(1, num_dias_mes + 1):
                data_dia = date(ano, mes, dia)
                is_weekday_dia = data_dia.weekday() < 5  # 0-4 = Seg-Sex
                tipo_dia = 'util' if is_weekday_dia else 'fds'
                estrutura_mes.append((dia, tipo_dia))
                
                if is_weekday_dia:
                    dias_uteis += 1
                else:
                    dias_fds += 1
            
            if verbose:
                nome_mes_completo = ["", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                                     "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][mes]
                print(f"\n>> {nome_mes_completo}/{ano}: {num_dias_mes} dias ({dias_uteis} uteis + {dias_fds} FDS)")
                print(f"   Capacidade Eolica: {capacidade_eolica_total:,.0f} MW")
                print(f"   Capacidade Solar:  {capacidade_solar_total:,.0f} MW")
                print(f"   Carga Total:       {carga_total:,.0f} MW")
                print()
            
            # LOOP DE CENÁRIOS: Cada cenário simula o mês inteiro
            for sim in range(num_simulations):
                
                # Mostrar início do primeiro cenário do mês
                if verbose and sim == 0:
                    print(f"   Processando cenario 1/{num_simulations}...", end="", flush=True)
                    if num_simulations == 1:
                        print()  # Nova linha se for apenas 1 cenário
                    else:
                        print("\r", end="", flush=True)  # Apagar mensagem se houver múltiplos
                
                # LOOP DE DIAS: Percorrer cada dia do mês
                for dia, tipo_dia in estrutura_mes:
                    
                    # Gerar 24 horas para ESTE dia específico
                    seed = None  # Aleatoriedade total
                    
                    val_gereolica_sample = sample_val_geolica_perfil_ar1(
                        media_mensal=media_mensal_eolica,
                        mes=mes,
                        num_horas=24,
                        num_cenarios=1,
                        seed=seed
                    )
                    
                    # Gerar geração solar (separando centralizada e distribuída se configurado)
                    if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA:
                        # Obter médias de centralizada e distribuída
                        solar_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
                        solar_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
                        
                        # Gerar perfis separadamente
                        val_gersolar_cent_sample = sample_val_gersolar_perfil_ar1(
                            media_diurna=solar_cent,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )
                        
                        val_gersolar_dist_sample = sample_val_gersolar_distribuida_perfil_ar1(
                            media_diurna=solar_dist,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )
                        
                        # Somar para obter total
                        val_gersolar_sample = val_gersolar_cent_sample + val_gersolar_dist_sample
                    else:
                        # Modo compatibilidade: usar total diretamente
                        val_gersolar_sample = sample_val_gersolar_perfil_ar1(
                            media_diurna=media_diurna_solar,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )
                    
                    # IMPORTANTE: Usar modelo V6 (determinístico com temperatura)
                    # Obter temperatura REAL se disponível, ou climatologia como fallback
                    temp_media_mensal = obter_temperatura_mensal(ano, mes)
                    
                    # Obter temperaturas horárias reais (se disponíveis para 2023-2025)
                    temp_horaria_real = obter_temperaturas_dia(ano, mes, dia)
                    
                    # V6: Determinístico com temperatura (recomendado!)
                    val_carga_sample = sample_val_carga_perfil_v6(
                        ano=ano,
                        mes=mes,
                        dia=dia,
                        carga_mensal=media_mensal_carga,
                        temp_media_mensal=temp_media_mensal,
                        temp_horaria_real=temp_horaria_real,  # Usa temp real quando disponível!
                        num_horas=24,
                        seed=seed
                    )
                    
                    # Verificar se as amostras são válidas
                    if np.any(np.isnan(val_gereolica_sample)) or \
                       np.any(np.isnan(val_gersolar_sample)) or \
                       np.any(np.isnan(val_carga_sample)):
                        if verbose:
                            print(f"[AVISO] Amostras inválidas para {ano}-{mes:02d} dia {dia}, sim {sim+1}")
                        continue
                    
                    # LOOP DE HORAS: Processar cada hora do dia
                    for hora in range(24):
                        # Extrair valores para a hora atual
                        val_gereolica = val_gereolica_sample[hora]
                        val_gersolar = val_gersolar_sample[hora]
                        val_carga = val_carga_sample[hora]
                        
                        # Preparar valores separados de solar se disponível
                        if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA:
                            val_solar_cent_hora = val_gersolar_cent_sample[hora]
                            val_solar_dist_hora = val_gersolar_dist_sample[hora]
                        else:
                            val_solar_cent_hora = None
                            val_solar_dist_hora = None
                        
                        # Executar o modelo probabilístico
                        resultado = calcular_despacho_probabilistico(
                            LIMITE_HIDRO,
                            LIMITE_HIDRO_RESERVATORIO,
                            val_carga,
                            val_gereolica,
                            val_gersolar,
                            val_inflexterm,
                            ENA_arm,
                            mes,
                            hora,
                            tipo_dia == 'util',
                            MIN_HIDRO_RESERVATORIO,
                            val_gersolar_centralizada=val_solar_cent_hora,
                            val_gersolar_distribuida=val_solar_dist_hora
                        )
                        
                        if resultado is None:
                            continue
                        
                        # Calcular PLD
                        pld = calcular_pld(
                            resultado['val_term_despacho'],
                            VALOR_FIXO_INFLEXTERM,
                            pilha_termica
                        )
                        
                        # Calcular carga líquida
                        # Carga Líquida = Carga - Renováveis - Inflexível - Hidro FD
                        # É o que resta para ser atendido por Hidro Reservatório + Térmica Flexível
                        carga_liquida = (
                            val_carga - 
                            resultado['val_gereolica_depois_corte'] - 
                            resultado['val_gersolar_depois_corte'] - 
                            val_inflexterm - 
                            resultado['val_gerhidro_fd']
                        )
                        
                        # Armazenar os resultados
                        registro = {
                            'simulacao': sim + 1,
                            'dia': dia,
                            'hora': hora,
                            'tipo_dia': tipo_dia,
                            'val_gereolica': val_gereolica,
                            'val_gersolar': val_gersolar,
                            'val_carga': val_carga,
                            'carga_liquida': carga_liquida,
                            'limite_hidro': LIMITE_HIDRO,
                            'limite_hidro_reservatorio': LIMITE_HIDRO_RESERVATORIO,
                            'val_inflexterm': val_inflexterm,
                            'ENA_arm': ENA_arm,
                            'mes': mes,
                            'ano': ano,
                            'is_weekday': tipo_dia == 'util',
                            'min_hidro_reservatorio': MIN_HIDRO_RESERVATORIO,
                            'val_term_despacho': resultado['val_term_despacho'],
                            'val_gerhidro_reservatorio': resultado['val_gerhidro_reservatorio'],
                            'val_gerhidro_fd': resultado['val_gerhidro_fd'],
                            'val_gerhidro_total': resultado['val_gerhidro_reservatorio'] + resultado['val_gerhidro_fd'],
                            'curtailment': resultado['curtailment'],
                            'curtailment_eolica': resultado.get('curtailment_eolica', 0),
                            'curtailment_solar_cent': resultado.get('curtailment_solar_cent', 0),
                            'curtailment_solar_dist': resultado.get('curtailment_solar_dist', 0),
                            'val_gereolica_antes_corte': resultado['val_gereolica_antes_corte'],
                            'val_gereolica_depois_corte': resultado['val_gereolica_depois_corte'],
                            'val_gersolar_antes_corte': resultado['val_gersolar_antes_corte'],
                            'val_gersolar_depois_corte': resultado['val_gersolar_depois_corte'],
                            'val_erro': resultado['val_erro'],
                            'pld': pld
                        }
                        
                        # Adicionar componentes solares se disponível
                        if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA and 'val_gersolar_cent_depois_corte' in resultado:
                            registro['val_gersolar_cent_antes_corte'] = resultado.get('val_gersolar_cent_antes_corte', 0)
                            registro['val_gersolar_cent_depois_corte'] = resultado.get('val_gersolar_cent_depois_corte', 0)
                            registro['val_gersolar_dist_antes_corte'] = resultado.get('val_gersolar_dist_antes_corte', 0)
                            registro['val_gersolar_dist_depois_corte'] = resultado.get('val_gersolar_dist_depois_corte', 0)
                        
                        data.append(registro)
                        
                        contador += 1
                        
                        # Feedback de progresso atualizado - mostrar a cada 50 horas (mais frequente)
                        if verbose and contador % 50 == 0:
                            _imprimir_progresso(contador, total_horas, inicio_tempo, mes, ano, sim + 1, num_simulations)
    
    # Criar DataFrame com os resultados
    df_resultados = pd.DataFrame(data)
    
    if verbose:
        # Finalizar linha de progresso
        if contador > 0:
            _imprimir_progresso(contador, total_horas, inicio_tempo, mes, ano, num_simulations, num_simulations)
        print()  # Nova linha após a barra de progresso
        
        tempo_total = time.time() - inicio_tempo
        print()
        print("=" * 70)
        print(f"  SIMULACAO CONCLUIDA!")
        print("=" * 70)
        print(f"Tempo total: {_formatar_tempo(tempo_total)}")
        print(f"Registros gerados: {len(df_resultados):,}")
        
        if contador > 0:
            velocidade = contador / tempo_total
            print(f"Velocidade media: {velocidade:.1f} horas/segundo")
            print(f"                  {velocidade * 3600:.0f} horas/hora")
        
        if len(df_resultados) > 0:
            # Estatísticas por tipo de dia
            registros_util = (df_resultados['tipo_dia'] == 'util').sum()
            registros_fds = (df_resultados['tipo_dia'] == 'fds').sum()
            pct_util = (registros_util / len(df_resultados)) * 100
            pct_fds = (registros_fds / len(df_resultados)) * 100
            
            print(f"\nDistribuicao:")
            print(f"   Dias uteis: {registros_util:,} registros ({pct_util:.1f}%)")
            print(f"   Finais de semana: {registros_fds:,} registros ({pct_fds:.1f}%)")
            
            if df_resultados['val_erro'].sum() > 0:
                print(f"\n[AVISO] {df_resultados['val_erro'].sum()} erros de balanceamento detectados.")
        elif len(df_resultados) == 0:
            print("[AVISO] Nenhum resultado foi gerado!")
            print("   Verifique se os parametros dos modelos existem.")
    
    return df_resultados


def run_simulation_monthly_aggregated(
    num_simulations=DEFAULT_NUM_SIMULATIONS,
    anos=range(2022, 2028),
    meses=range(1, 13),
    pilha_termica=None,
    verbose=True
):
    """
    Executa simulação Monte Carlo agregando por mês/simulação.

    Saída: uma linha por (ano, mes, simulacao).
    Mantém a lógica de mês completo com mistura de dias úteis/FDS, mas
    acumula valores ao longo das horas para reduzir o volume (ex.: 12x100=1200 linhas).
    """
    # Aplicar ajuste de inflexibilidade térmica
    val_inflexterm_dic_ajustado = aplicar_ajuste_inflexterm(
        val_inflexterm_dic,
        VALOR_FIXO_INFLEXTERM,
        MESES_INFLEXTERM_ADICIONAL
    )

    # Criar pilha térmica se não fornecida
    if pilha_termica is None:
        pilha_termica = carregar_pilha_termica()
        if verbose:
            print("[OK] Pilha termica carregada.")

    resultados = []

    # Total de horas apenas para feedback
    total_horas = 0
    for ano in anos:
        for mes in meses:
            num_dias = calendar.monthrange(ano, mes)[1]
            total_horas += num_simulations * num_dias * 24

    contador = 0

    if verbose:
        print(f"\nSimulando (AGREGADO) {num_simulations} cenarios por mes para {len(anos)} anos e {len(meses)} meses...")
        print(f"Cada cenario simula o MES COMPLETO com dias uteis e finais de semana")
        print(f"Total estimado de horas processadas: {total_horas:,}\n")

    for ano in anos:
        for mes in meses:
            # Parâmetros do mês/ano
            capacidade_eolica_total = capacidade_eolica_total_dic.get(ano, {}).get(mes)
            capacidade_solar_total = capacidade_solar_total_dic.get(ano, {}).get(mes)
            carga_total = carga_total_dic.get(ano, {}).get(mes)
            val_inflexterm = val_inflexterm_dic_ajustado.get(ano, {}).get(mes)
            # ENA: Usar valor real se disponível, senão usar valor do dicionário
            ena_real = _media_mensal_ena_real(ano, mes)
            ENA_arm = ena_real if ena_real is not None else ENA_dic.get(ano, {}).get(mes)
            val_inflexterm_ex_pct = val_inflexterm_ex_pct_dic.get(ano, {}).get(mes)

            if any(v is None for v in [capacidade_eolica_total, capacidade_solar_total, carga_total, val_inflexterm, ENA_arm]):
                if verbose:
                    print(f"[AVISO] Dados faltando para {ano}-{mes:02d}, pulando...")
                continue

            # Médias mensais (mesma regra simples utilizada na simulação detalhada)
            media_mensal_eolica = capacidade_eolica_total * 0.40
            media_diurna_solar = capacidade_solar_total * 0.35
            media_mensal_carga = carga_total

            # Estrutura do mês
            num_dias_mes = calendar.monthrange(ano, mes)[1]
            estrutura_mes = []
            dias_uteis = 0
            dias_fds = 0

            for dia in range(1, num_dias_mes + 1):
                data_dia = date(ano, mes, dia)
                is_weekday_dia = data_dia.weekday() < 5
                tipo_dia = 'util' if is_weekday_dia else 'fds'
                estrutura_mes.append((dia, tipo_dia))
                if is_weekday_dia:
                    dias_uteis += 1
                else:
                    dias_fds += 1

            if verbose:
                print(f"{ano}-{mes:02d}: {num_dias_mes} dias ({dias_uteis} uteis + {dias_fds} FDS)")

            # Loop de cenários (um registro por cenário ao final)
            for sim in range(num_simulations):
                # Acumuladores mensais (MWh ao somar por hora)
                sum_eolica = 0.0
                sum_solar = 0.0
                sum_carga = 0.0
                sum_carga_liquida = 0.0
                sum_termica = 0.0
                sum_hidro_res = 0.0
                sum_hidro_fd = 0.0
                sum_curtail = 0.0
                sum_pld = 0.0  # média no final
                horas = 0
                horas_util = 0
                horas_fds = 0

                for dia, tipo_dia in estrutura_mes:
                    seed = None

                    val_gereolica_sample = sample_val_geolica_perfil_ar1(
                        media_mensal=media_mensal_eolica,
                        mes=mes,
                        num_horas=24,
                        num_cenarios=1,
                        seed=seed
                    )

                    # Gerar geração solar (separando centralizada e distribuída se configurado)
                    if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA:
                        solar_cent = geracao_solar_centralizada_dic.get(ano, {}).get(mes, 0)
                        solar_dist = geracao_solar_distribuida_dic.get(ano, {}).get(mes, 0)
                        
                        val_gersolar_cent_sample = sample_val_gersolar_perfil_ar1(
                            media_diurna=solar_cent,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )
                        
                        val_gersolar_dist_sample = sample_val_gersolar_distribuida_perfil_ar1(
                            media_diurna=solar_dist,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )
                        
                        val_gersolar_sample = val_gersolar_cent_sample + val_gersolar_dist_sample
                    else:
                        val_gersolar_sample = sample_val_gersolar_perfil_ar1(
                            media_diurna=media_diurna_solar,
                            mes=mes,
                            num_horas=24,
                            num_cenarios=1,
                            seed=seed
                        )

                    # Usar modelo V6 (determinístico com temperatura)
                    # Obter temperatura REAL se disponível, ou climatologia como fallback
                    temp_media_mensal = obter_temperatura_mensal(ano, mes)
                    
                    # Obter temperaturas horárias reais (se disponíveis para 2023-2025)
                    temp_horaria_real = obter_temperaturas_dia(ano, mes, dia)
                    
                    # V6: Determinístico com temperatura
                    val_carga_sample = sample_val_carga_perfil_v6(
                        ano=ano,
                        mes=mes,
                        dia=dia,
                        carga_mensal=media_mensal_carga,
                        temp_media_mensal=temp_media_mensal,
                        temp_horaria_real=temp_horaria_real,  # Usa temp real quando disponível!
                        num_horas=24,
                        seed=seed
                    )

                    if np.any(np.isnan(val_gereolica_sample)) or \
                       np.any(np.isnan(val_gersolar_sample)) or \
                       np.any(np.isnan(val_carga_sample)):
                        if verbose:
                            print(f"[AVISO] Amostras invalidas para {ano}-{mes:02d} dia {dia}, sim {sim+1}")
                        continue

                    for hora in range(24):
                        val_gereolica = float(val_gereolica_sample[hora])
                        val_gersolar = float(val_gersolar_sample[hora])
                        val_carga = float(val_carga_sample[hora])
                        
                        # Preparar valores separados de solar se disponível
                        if SOLAR_SEPARAR_CENTRALIZADA_DISTRIBUIDA:
                            val_solar_cent_hora = float(val_gersolar_cent_sample[hora])
                            val_solar_dist_hora = float(val_gersolar_dist_sample[hora])
                        else:
                            val_solar_cent_hora = None
                            val_solar_dist_hora = None

                        resultado = calcular_despacho_probabilistico(
                            LIMITE_HIDRO,
                            LIMITE_HIDRO_RESERVATORIO,
                            val_carga,
                            val_gereolica,
                            val_gersolar,
                            val_inflexterm,
                            ENA_arm,
                            mes,
                            hora,
                            tipo_dia == 'util',
                            MIN_HIDRO_RESERVATORIO,
                            val_gersolar_centralizada=val_solar_cent_hora,
                            val_gersolar_distribuida=val_solar_dist_hora
                        )
                        if resultado is None:
                            continue

                        pld = calcular_pld(
                            resultado['val_term_despacho'],
                            VALOR_FIXO_INFLEXTERM,
                            pilha_termica
                        )

                        # Calcular carga líquida para esta hora
                        carga_liquida_hora = (
                            val_carga - 
                            resultado['val_gereolica_depois_corte'] - 
                            resultado['val_gersolar_depois_corte'] - 
                            val_inflexterm - 
                            resultado['val_gerhidro_fd']
                        )
                        
                        # Acumular (MW hora a hora -> MWh ao somar)
                        sum_eolica += val_gereolica
                        sum_solar += val_gersolar
                        sum_carga += val_carga
                        sum_carga_liquida += carga_liquida_hora
                        sum_termica += resultado['val_term_despacho']
                        sum_hidro_res += resultado['val_gerhidro_reservatorio']
                        sum_hidro_fd += resultado['val_gerhidro_fd']
                        sum_curtail += resultado['curtailment']
                        sum_pld += pld

                        horas += 1
                        if tipo_dia == 'util':
                            horas_util += 1
                        else:
                            horas_fds += 1

                        contador += 1
                        if verbose and contador % 1000 == 0:
                            progresso = (contador / total_horas) * 100
                            print(f"Progresso: {contador:,}/{total_horas:,} ({progresso:.1f}%)")

                if horas == 0:
                    continue

                resultados.append({
                    'ano': ano,
                    'mes': mes,
                    'simulacao': sim + 1,
                    'horas': horas,
                    'horas_util': horas_util,
                    'horas_fds': horas_fds,
                    'pct_util': horas_util / horas * 100.0,
                    'pct_fds': horas_fds / horas * 100.0,
                    # Somas em MWh (pois a unidade das horas é MW)
                    'eolica_mwh': sum_eolica,
                    'solar_mwh': sum_solar,
                    'carga_mwh': sum_carga,
                    'carga_liquida_mwh': sum_carga_liquida,
                    'termica_mwh': sum_termica,
                    'hidro_reservatorio_mwh': sum_hidro_res,
                    'hidro_fd_mwh': sum_hidro_fd,
                    'hidro_total_mwh': sum_hidro_res + sum_hidro_fd,
                    'curtailment_mwh': sum_curtail,
                    # Médias mensais (MW) úteis
                    'pld_medio': sum_pld / horas,
                    'eolica_media_mw': sum_eolica / horas,
                    'solar_media_mw': sum_solar / horas,
                    'carga_media_mw': sum_carga / horas,
                    'carga_liquida_media_mw': sum_carga_liquida / horas,
                    'termica_media_mw': sum_termica / horas,
                    'hidro_total_media_mw': (sum_hidro_res + sum_hidro_fd) / horas,
                })

    df = pd.DataFrame(resultados)

    if verbose:
        print(f"\n[OK] Simulacao AGREGADA concluida! {len(df):,} registros (linhas mensais).")

    return df
