#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ANÁLISE DE CORRELAÇÃO: CURTAILMENT ENERGÉTICO vs CMO
=====================================================

Este módulo analisa a correlação entre curtailment energético (em termos percentuais)
e o Custo Marginal de Operação (CMO) para cada hora disponível nas amostras.

Objetivos:
- Combinar dados de curtailment do sistema Curtailment
- Combinar dados de CMO do sistema carga_liquida
- Gerar gráficos de correlação por hora
- Usar dados de curtailment a nível Brasil em termos percentuais
- Usar dados de CMO do subsistema Sudeste (conforme usado em carga_liquida)
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Adicionar caminhos para importar módulos dos sistemas existentes (robusto ao local do arquivo)
base_dir = Path(__file__).resolve().parents[2]
sys.path.append(str(base_dir / "Codigos ONS" / "Curtailment" / "Scripts"))
sys.path.append(str(base_dir / "Codigos ONS" / "carga_liquida" / "Scripts"))

class CorrelacaoAnalisador:
    """Analisa correlação entre curtailment energético e CMO."""

    def __init__(self, subsistema='BRASIL', apenas_finais_semana=False):
        """Inicializa o analisador."""
        # Configurar caminhos
        self.project_root = Path(__file__).parent
        self.data_dir = self.project_root / "data"
        self.output_dir = self.project_root / "output"
        # Modo de cálculo do curtailment: 'original' (matching run inicial) ou 'ref_final'
        self.curtailment_mode = 'original'
        # Subsistema a ser analisado ('BRASIL' = todos os subsistemas)
        self.subsistema = subsistema.upper()
        # Filtrar apenas finais de semana (sábado e domingo)
        self.apenas_finais_semana = apenas_finais_semana

        # Criar diretórios necessários
        self.data_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # Configurar logging
        self._configurar_logging()

        # Dados processados
        self.dados_curtailment = None
        self.dados_cmo = None
        self.dados_pld = None
        self.dados_combinados = None

    def _configurar_logging(self):
        """Configura o sistema de logging."""
        log_file = self.project_root / "correlacao_analise.log"

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)

    def carregar_dados_curtailment(self):
        """
        Carrega dados de curtailment energético percentual a nível Brasil.

        Baseado no sistema Curtailment existente.
        """
        self.logger.info("Carregando dados de curtailment...")

        try:
            # Carregar dados brutos diretamente e processar
            dados_brutos = self._carregar_dados_curtailment_brutos()
            dados_processados = self._processar_curtailment_brasil(dados_brutos)

            self.dados_curtailment = dados_processados
            self.logger.info(f"Dados de curtailment carregados: {len(self.dados_curtailment)} registros")

            return True

        except Exception as e:
            self.logger.error(f"Erro ao carregar dados de curtailment: {e}")
            return False

    def _carregar_dados_curtailment_brutos(self):
        """Carrega dados brutos de curtailment."""
        # Caminho para dados brutos
        raw_dir = base_dir / "Codigos ONS" / "Curtailment" / "Dados" / "raw_data"

        if not raw_dir.exists():
            raise FileNotFoundError(f"Diretório de dados brutos não encontrado: {raw_dir}")

        # Lista para armazenar DataFrames
        dfs = []

        # Carregar arquivos de curtailment recentes (últimos 12 meses)
        meses_recentes = []
        hoje = datetime.now()
        for i in range(12):
            ano = hoje.year
            mes = hoje.month - i
            if mes <= 0:
                ano -= 1
                mes += 12
            meses_recentes.append((ano, mes))

        # Carregar arquivos eólicos e solares
        for ano, mes in meses_recentes:
            for tipo in ['EOLICA', 'FOTOVOLTAICA']:
                nome_arquivo = f"RESTRICAO_COFF_{tipo}_{ano}_{mes:02d}.csv"
                arquivo_path = raw_dir / nome_arquivo

                if arquivo_path.exists():
                    try:
                        df = pd.read_csv(arquivo_path, sep=';')
                        df['tipo_usina'] = tipo.lower()
                        dfs.append(df)
                        self.logger.info(f"Arquivo carregado: {nome_arquivo}")
                    except Exception as e:
                        self.logger.warning(f"Erro ao carregar {nome_arquivo}: {e}")

        if not dfs:
            raise ValueError("Nenhum arquivo de curtailment encontrado")

        return pd.concat(dfs, ignore_index=True)

    def _processar_curtailment_brasil(self, dados_brutos):
        """Processa dados de curtailment para obter percentuais por subsistema."""

        # Converter tipos de dados
        dados_brutos['din_instante'] = pd.to_datetime(dados_brutos['din_instante'])
        dados_brutos['val_geracao'] = pd.to_numeric(dados_brutos['val_geracao'], errors='coerce')
        dados_brutos['val_disponibilidade'] = pd.to_numeric(dados_brutos['val_disponibilidade'], errors='coerce')
        dados_brutos['val_geracaoreferencia'] = pd.to_numeric(dados_brutos['val_geracaoreferencia'], errors='coerce')
        if 'val_geracaolimitada' in dados_brutos.columns:
            dados_brutos['val_geracaolimitada'] = pd.to_numeric(dados_brutos['val_geracaolimitada'], errors='coerce')
        else:
            dados_brutos['val_geracaolimitada'] = dados_brutos['val_geracao']
        if 'val_geracaoreferenciafinal' in dados_brutos.columns:
            dados_brutos['val_geracaoreferenciafinal'] = pd.to_numeric(dados_brutos['val_geracaoreferenciafinal'], errors='coerce')
        else:
            dados_brutos['val_geracaoreferenciafinal'] = dados_brutos['val_geracaoreferencia']

        # FILTRAR APENAS CURTAILMENT ENERGÉTICO (ENE)
        if 'cod_razaorestricao' in dados_brutos.columns:
            # Filtrar apenas restrições energéticas
            dados_brutos = dados_brutos[dados_brutos['cod_razaorestricao'].astype(str).str.upper() == 'ENE'].copy()
            self.logger.info(f"Dados filtrados para curtailment energético (ENE): {len(dados_brutos)} registros")
        else:
            self.logger.warning("Coluna 'cod_razaorestricao' não encontrada - processando todos os dados")

        # FILTRAR POR SUBSISTEMA (se não for BRASIL)
        if 'nom_subsistema' in dados_brutos.columns:
            if self.subsistema != 'BRASIL':
                dados_brutos = dados_brutos[dados_brutos['nom_subsistema'].astype(str).str.upper() == self.subsistema].copy()
                self.logger.info(f"Dados filtrados para subsistema: {self.subsistema}")
            else:
                self.logger.info(f"Processando dados de todos os subsistemas (BRASIL)")

        # Calcular curtailment em MWh (30 min para MWh)
        dados_brutos['val_geracao_mwh'] = dados_brutos['val_geracao'] * 0.5
        dados_brutos['val_disponibilidade_mwh'] = dados_brutos['val_disponibilidade'] * 0.5
        dados_brutos['val_geracaoreferencia_mwh'] = dados_brutos['val_geracaoreferencia'] * 0.5
        dados_brutos['val_geracaolimitada_mwh'] = dados_brutos['val_geracaolimitada'] * 0.5
        dados_brutos['val_geracaoreferenciafinal_mwh'] = dados_brutos['val_geracaoreferenciafinal'] * 0.5

        # Calcular curtailment em diferentes variantes
        potencial_final_mwh = np.minimum(dados_brutos['val_disponibilidade_mwh'], dados_brutos['val_geracaoreferenciafinal_mwh'])
        potencial_ref_mwh = np.minimum(dados_brutos['val_disponibilidade_mwh'], dados_brutos['val_geracaoreferencia_mwh'])
        # Variante que casa com a primeira execução (original): min(disponibilidade, referencia) - geração
        dados_brutos['val_curtail_original_mwh'] = np.maximum(potencial_ref_mwh - dados_brutos['val_geracao_mwh'], 0)
        # Variante usando referencia final
        dados_brutos['val_curtail_ref_final_mwh'] = np.maximum(potencial_final_mwh - dados_brutos['val_geracao_mwh'], 0)

        # Filtrar período recente (último ano - 365 dias)
        data_corte = datetime.now() - timedelta(days=365)
        dados_filtrados = dados_brutos[dados_brutos['din_instante'] >= data_corte]

        # Agregar por hora (por subsistema)
        dados_horarios = dados_filtrados.groupby(
            pd.Grouper(key='din_instante', freq='h')
        ).agg({
            'val_geracao_mwh': 'sum',
            'val_geracaoreferencia_mwh': 'sum',
            'val_geracaoreferenciafinal_mwh': 'sum',
            'val_curtail_original_mwh': 'sum',
            'val_curtail_ref_final_mwh': 'sum'
        }).reset_index()

        # Calcular percentual de curtailment
        if self.curtailment_mode == 'original':
            denom = dados_horarios['val_geracaoreferencia_mwh'].replace(0, np.nan)
            dados_horarios['pct_curtailment'] = (dados_horarios['val_curtail_original_mwh'] / denom) * 100
        else:
            denom = dados_horarios['val_geracaoreferenciafinal_mwh'].replace(0, np.nan)
            dados_horarios['pct_curtailment'] = (dados_horarios['val_curtail_ref_final_mwh'] / denom) * 100

        # Remover valores inválidos
        dados_horarios = dados_horarios.dropna(subset=['pct_curtailment'])

        # Filtrar apenas finais de semana se solicitado
        if self.apenas_finais_semana:
            dados_horarios['dia_semana'] = dados_horarios['din_instante'].dt.dayofweek
            # dayofweek: 0=Segunda, 5=Sábado, 6=Domingo
            dados_horarios = dados_horarios[dados_horarios['dia_semana'].isin([5, 6])].copy()
            dados_horarios.drop('dia_semana', axis=1, inplace=True)
            self.logger.info(f"Dados filtrados para finais de semana: {len(dados_horarios)} registros")

        return dados_horarios

    def carregar_dados_cmo(self):
        """
        Carrega dados de CMO do subsistema especificado (ou média Brasil).
        """
        texto_sub = "Brasil (média)" if self.subsistema == 'BRASIL' else f"subsistema {self.subsistema}"
        self.logger.info(f"Carregando dados de CMO do {texto_sub}...")

        try:
            # Caminho preferencial para reproduzir execução inicial: PARQUET
            caminho_parquet = base_dir / "Codigos ONS" / "carga_liquida" / "Data" / "raw" / "CMO"
            dfs_cmo = []
            if caminho_parquet.exists():
                arquivos_parquet = sorted(caminho_parquet.glob("CMO_SEMIHORARIO_*.parquet"))
                for arquivo in arquivos_parquet:
                    try:
                        df = pd.read_parquet(arquivo)
                        dfs_cmo.append(df)
                    except Exception as e:
                        self.logger.warning(f"Erro ao ler parquet {arquivo}: {e}")

            if not dfs_cmo:
                raise FileNotFoundError("Dados de CMO não encontrados (parquet nem csv)")

            dados_cmo = pd.concat(dfs_cmo, ignore_index=True)
            self.logger.info("Dados CMO carregados (parquet/csv combinados)")

            # Processar dados CMO
            # Uniformizar colunas
            dados_cmo.columns = [str(c) for c in dados_cmo.columns]
            if 'din_instante' not in dados_cmo.columns:
                # Tentar variantes
                if 'DIN_INSTANTE' in dados_cmo.columns:
                    dados_cmo.rename(columns={'DIN_INSTANTE': 'din_instante'}, inplace=True)
            if 'val_cmo' not in dados_cmo.columns and 'VAL_CMO' in dados_cmo.columns:
                dados_cmo.rename(columns={'VAL_CMO': 'val_cmo'}, inplace=True)
            if 'nom_subsistema' not in dados_cmo.columns and 'NOM_SUBSISTEMA' in dados_cmo.columns:
                dados_cmo.rename(columns={'NOM_SUBSISTEMA': 'nom_subsistema'}, inplace=True)

            dados_cmo['din_instante'] = pd.to_datetime(dados_cmo['din_instante'])
            dados_cmo['val_cmo'] = pd.to_numeric(dados_cmo['val_cmo'], errors='coerce')

            # Filtrar para o subsistema especificado ou calcular média Brasil
            if self.subsistema != 'BRASIL':
                dados_subsistema = dados_cmo[dados_cmo['nom_subsistema'].astype(str).str.upper() == self.subsistema].copy()
            else:
                # Média de todos os subsistemas (Brasil)
                dados_subsistema = dados_cmo.groupby('din_instante', as_index=False)['val_cmo'].mean()
                self.logger.info(f"Calculando CMO médio do Brasil (média dos subsistemas)")

            # Filtrar período recente (último ano - 365 dias)
            data_corte = datetime.now() - timedelta(days=365)
            dados_subsistema = dados_subsistema[dados_subsistema['din_instante'] >= data_corte]

            # Remover valores inválidos
            dados_subsistema = dados_subsistema.dropna(subset=['val_cmo'])

            # Harmonizar para horário cheio: média por hora
            dados_subsistema['din_instante'] = dados_subsistema['din_instante'].dt.floor('h')
            dados_subsistema = dados_subsistema.groupby('din_instante', as_index=False)['val_cmo'].mean()

            # Filtrar apenas finais de semana se solicitado
            if self.apenas_finais_semana:
                dados_subsistema['dia_semana'] = dados_subsistema['din_instante'].dt.dayofweek
                # dayofweek: 0=Segunda, 5=Sábado, 6=Domingo
                dados_subsistema = dados_subsistema[dados_subsistema['dia_semana'].isin([5, 6])].copy()
                dados_subsistema.drop('dia_semana', axis=1, inplace=True)
                self.logger.info(f"Dados CMO filtrados para finais de semana: {len(dados_subsistema)} registros")

            self.dados_cmo = dados_subsistema
            texto_sub = "Brasil (média)" if self.subsistema == 'BRASIL' else self.subsistema
            self.logger.info(f"Dados CMO {texto_sub} carregados: {len(self.dados_cmo)} registros")

            return True

        except Exception as e:
            self.logger.error(f"Erro ao carregar dados CMO: {e}")
            return False

    def carregar_dados_pld(self):
        """
        Carrega dados de PLD do subsistema especificado.
        """
        texto_sub = "Brasil (média)" if self.subsistema == 'BRASIL' else f"subsistema {self.subsistema}"
        self.logger.info(f"Carregando dados de PLD do {texto_sub}...")

        try:
            # Caminho para o parquet de PLD
            pld_parquet = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\Precos de Energia BR\Data\processed\pld\base_master.parquet")
            
            if not pld_parquet.exists():
                self.logger.warning("Arquivo de PLD não encontrado")
                return False
            
            # Carregar dados de PLD
            dados_pld = pd.read_parquet(pld_parquet)
            
            # Renomear colunas para padrão
            dados_pld = dados_pld.rename(columns={
                'Data': 'din_instante',
                'Hora': 'hora',
                'Submercado': 'nom_subsistema',
                'Preço': 'val_pld'
            })
            
            # Converter data para datetime
            dados_pld['din_instante'] = pd.to_datetime(dados_pld['din_instante'])
            
            # Criar timestamp hora cheia combinando data + hora
            dados_pld['din_instante'] = dados_pld['din_instante'] + pd.to_timedelta(dados_pld['hora'], unit='h')
            
            # Filtrar período recente (último ano - 365 dias)
            data_corte = datetime.now() - timedelta(days=365)
            dados_pld = dados_pld[dados_pld['din_instante'] >= data_corte]
            
            # Filtrar para o subsistema especificado ou calcular média Brasil
            if self.subsistema != 'BRASIL':
                dados_subsistema = dados_pld[dados_pld['nom_subsistema'].astype(str).str.upper() == self.subsistema].copy()
            else:
                # Média de todos os subsistemas (Brasil)
                dados_subsistema = dados_pld.groupby('din_instante', as_index=False)['val_pld'].mean()
                self.logger.info(f"Calculando PLD médio do Brasil (média dos subsistemas)")
            
            # Filtrar apenas finais de semana se solicitado
            if self.apenas_finais_semana:
                dados_subsistema['dia_semana'] = dados_subsistema['din_instante'].dt.dayofweek
                # dayofweek: 0=Segunda, 5=Sábado, 6=Domingo
                dados_subsistema = dados_subsistema[dados_subsistema['dia_semana'].isin([5, 6])].copy()
                dados_subsistema.drop('dia_semana', axis=1, inplace=True)
                self.logger.info(f"Dados PLD filtrados para finais de semana: {len(dados_subsistema)} registros")
            
            # Garantir ordem cronológica
            dados_subsistema = dados_subsistema.sort_values('din_instante')
            
            # Armazenar apenas colunas necessárias
            self.dados_pld = dados_subsistema[['din_instante', 'val_pld']].reset_index(drop=True)
            
            texto_sub = "Brasil (média)" if self.subsistema == 'BRASIL' else self.subsistema
            self.logger.info(f"Dados PLD {texto_sub} carregados: {len(self.dados_pld)} registros")

            return True

        except Exception as e:
            self.logger.error(f"Erro ao carregar dados PLD: {e}")
            import traceback
            traceback.print_exc()
            return False

    def combinar_dados(self):
        """
        Combina dados de curtailment, CMO e PLD por hora.
        """
        self.logger.info("Combinando dados de curtailment, CMO e PLD...")

        if self.dados_curtailment is None or self.dados_cmo is None:
            raise ValueError("Dados de curtailment e/ou CMO não foram carregados")

        # Merge dos dados por hora (usando apenas percentuais, CMO e PLD)
        dados_combinados = pd.merge(
            self.dados_curtailment[['din_instante', 'pct_curtailment']],
            self.dados_cmo[['din_instante', 'val_cmo']],
            on='din_instante',
            how='inner'
        )
        
        # Adicionar PLD se disponível
        if self.dados_pld is not None and not self.dados_pld.empty:
            dados_combinados = pd.merge(
                dados_combinados,
                self.dados_pld[['din_instante', 'val_pld']],
                on='din_instante',
                how='left'  # left join para não perder dados se PLD não tiver todos os timestamps
            )
            self.logger.info(f"PLD integrado aos dados combinados")

        # Remover valores inválidos
        drop_cols = ['pct_curtailment', 'val_cmo']
        dados_combinados = dados_combinados.dropna(subset=drop_cols)

        if dados_combinados.empty:
            self.logger.warning("Merge resultou em 0 registros (sem interseção de horas)")

        self.dados_combinados = dados_combinados
        self.logger.info(f"Dados combinados: {len(self.dados_combinados)} registros")

        return True

    def gerar_graficos_correlacao(self):
        """
        Gera gráficos de correlação entre curtailment percentual e CMO.
        """
        self.logger.info("Gerando gráficos de correlação...")

        if self.dados_combinados is None or self.dados_combinados.empty:
            raise ValueError("Dados combinados não disponíveis")

        # Criar figura com múltiplos subplots
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))

        # 1. Scatter plot principal
        axes[0, 0].scatter(
            self.dados_combinados['pct_curtailment'],
            self.dados_combinados['val_cmo'],
            alpha=0.6, s=50, edgecolors='black', linewidth=0.5
        )
        axes[0, 0].set_xlabel('Curtailment Energético (%)')
        axes[0, 0].set_ylabel('CMO (R$/MWh)')
        periodo_txt = 'Finais de Semana' if self.apenas_finais_semana else 'Todos os Dias'
        axes[0, 0].set_title(f'Correlação: Curtailment vs CMO ({self.subsistema} - {periodo_txt})')
        axes[0, 0].grid(True, alpha=0.3)

        # 2. Distribuição por faixa de CMO
        self.dados_combinados['faixa_cmo'] = pd.cut(
            self.dados_combinados['val_cmo'],
            bins=[0, 100, 500, 1000, float('inf')],
            labels=['Baixo (0-100)', 'Médio (100-500)', 'Alto (500-1000)', 'Muito Alto (>1000)']
        )

        self.dados_combinados['faixa_cmo'].value_counts().plot(kind='bar', ax=axes[0, 1])
        axes[0, 1].set_title('Distribuição de CMO')
        axes[0, 1].set_xlabel('Faixa de CMO')
        axes[0, 1].set_ylabel('Frequência')
        axes[0, 1].tick_params(axis='x', rotation=45)

        # 3. Séries temporais
        axes[1, 0].plot(
            self.dados_combinados['din_instante'],
            self.dados_combinados['pct_curtailment'],
            label='Curtailment (%)', alpha=0.7
        )
        axes[1, 0].set_xlabel('Data/Hora')
        axes[1, 0].set_ylabel('Curtailment (%)', color='blue')
        axes[1, 0].tick_params(axis='y', labelcolor='blue')
        axes[1, 0].legend(loc='upper left')

        ax2 = axes[1, 0].twinx()
        ax2.plot(
            self.dados_combinados['din_instante'],
            self.dados_combinados['val_cmo'],
            label='CMO (R$/MWh)', color='red', alpha=0.7
        )
        ax2.set_ylabel('CMO (R$/MWh)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        ax2.legend(loc='upper right')

        # 4. Correlação por hora do dia
        self.dados_combinados['hora'] = self.dados_combinados['din_instante'].dt.hour
        correlacao_vals = []
        for h in range(24):
            subset = self.dados_combinados[self.dados_combinados['hora'] == h]
            if len(subset) >= 2:
                corr = subset['pct_curtailment'].corr(subset['val_cmo'])
            else:
                corr = np.nan
            correlacao_vals.append(0 if pd.isna(corr) else corr)

        axes[1, 1].bar(range(24), correlacao_vals)
        axes[1, 1].set_xlabel('Hora do Dia')
        axes[1, 1].set_ylabel('Coeficiente de Correlação')
        axes[1, 1].set_title('Correlação por Hora do Dia')
        axes[1, 1].set_xticks(range(0, 24, 2))
        axes[1, 1].grid(True, alpha=0.3)

        plt.tight_layout()

        # Salvar gráfico
        sufixo = '_fds' if self.apenas_finais_semana else ''
        output_path = self.output_dir / f"correlacao_curtailment_cmo_{self.subsistema}{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"Gráfico salvo em: {output_path}")

        return output_path

    def gerar_grafico_perfil_horario(self):
        """
        Gera gráfico de perfil horário: barras (curtailment) + linha (CMO).
        INCLUI ZEROS - considera todas as horas de todos os dias, mesmo sem curtailment ENE.
        """
        self.logger.info("Gerando gráfico de perfil horário...")

        if self.dados_combinados is None or self.dados_combinados.empty:
            raise ValueError("Dados combinados não disponíveis")

        # Adicionar hora do dia
        df = self.dados_combinados.copy()
        df['hora'] = df['din_instante'].dt.hour
        df['data'] = df['din_instante'].dt.date

        # PASSO 1: Criar grid completo de TODAS as datas e TODAS as horas
        data_min = df['din_instante'].min().date()
        data_max = df['din_instante'].max().date()
        
        # Gerar todas as datas no período
        todas_datas = pd.date_range(start=data_min, end=data_max, freq='D').date
        
        # Filtrar apenas dias úteis ou finais de semana conforme configuração
        if self.apenas_finais_semana:
            # Apenas sábados (5) e domingos (6)
            todas_datas = [d for d in todas_datas if pd.Timestamp(d).dayofweek in [5, 6]]
        else:
            # Apenas dias úteis (0-4 = segunda a sexta)
            todas_datas = [d for d in todas_datas if pd.Timestamp(d).dayofweek in [0, 1, 2, 3, 4]]
        
        # Criar grid completo: todas as datas x todas as horas (0-23)
        grid_completo = []
        for data in todas_datas:
            for hora in range(24):
                grid_completo.append({'data': data, 'hora': hora})
        
        df_grid = pd.DataFrame(grid_completo)
        
        # PASSO 2: Agregar curtailment, CMO e PLD por data/hora dos dados REAIS
        agg_dict = {
            'pct_curtailment': 'mean',
            'val_cmo': 'mean'
        }
        
        # Adicionar PLD se disponível
        if 'val_pld' in df.columns:
            agg_dict['val_pld'] = 'mean'
        
        df_agregado = df.groupby(['data', 'hora']).agg(agg_dict).reset_index()
        
        # PASSO 3: Fazer merge com grid completo, preenchendo zeros
        df_completo = df_grid.merge(df_agregado, on=['data', 'hora'], how='left')
        df_completo['pct_curtailment'] = df_completo['pct_curtailment'].fillna(0)
        # CMO: preencher com média geral (não com zero, pois CMO sempre existe)
        cmo_medio_geral = df['val_cmo'].mean()
        df_completo['val_cmo'] = df_completo['val_cmo'].fillna(cmo_medio_geral)
        
        # PLD: preencher com média geral se disponível
        if 'val_pld' in df.columns:
            pld_medio_geral = df['val_pld'].mean()
            df_completo['val_pld'] = df_completo['val_pld'].fillna(pld_medio_geral)
        
        # PASSO 4: Calcular médias por hora (agora com zeros incluídos!)
        perfil_cols = {
            'pct_curtailment': 'mean',
            'val_cmo': 'mean'
        }
        if 'val_pld' in df_completo.columns:
            perfil_cols['val_pld'] = 'mean'
        
        perfil = df_completo.groupby('hora').agg(perfil_cols).reindex(range(24), fill_value=0)
        
        # Log para validação
        total_horas = len(df_completo)
        horas_com_curtailment = (df_completo['pct_curtailment'] > 0).sum()
        horas_sem_curtailment = (df_completo['pct_curtailment'] == 0).sum()
        self.logger.info(f"Perfil horário: {total_horas} horas totais ({horas_com_curtailment} com curtailment, {horas_sem_curtailment} zeros)")

        # Criar figura
        fig, ax1 = plt.subplots(figsize=(14, 7))

        # Gráfico de barras (curtailment)
        x = range(24)
        bars = ax1.bar(x, perfil['pct_curtailment'], alpha=0.7, color='#e74c3c', 
                       label='Curtailment Médio (%)', edgecolor='black', linewidth=0.5)
        ax1.set_xlabel('Hora do Dia', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Curtailment (%)', fontsize=12, fontweight='bold', color='#e74c3c')
        ax1.tick_params(axis='y', labelcolor='#e74c3c')
        ax1.set_xticks(range(24))
        ax1.set_xlim(-0.5, 23.5)
        ax1.grid(True, alpha=0.3, axis='y')

        # Segundo eixo (CMO e PLD)
        ax2 = ax1.twinx()
        line_cmo = ax2.plot(x, perfil['val_cmo'], color='#2c3e50', linewidth=2.5, 
                            marker='o', markersize=6, label='CMO Médio (R$/MWh)')
        
        # Plotar PLD se disponível
        if 'val_pld' in perfil.columns:
            line_pld = ax2.plot(x, perfil['val_pld'], color='#16a085', linewidth=2.5, 
                                marker='s', markersize=6, linestyle='--', label='PLD Médio (R$/MWh)')
        
        ylabel_text = 'CMO e PLD (R$/MWh)' if 'val_pld' in perfil.columns else 'CMO (R$/MWh)'
        ax2.set_ylabel(ylabel_text, fontsize=12, fontweight='bold', color='#2c3e50')
        ax2.tick_params(axis='y', labelcolor='#2c3e50')

        # Título
        periodo_txt = 'Finais de Semana' if self.apenas_finais_semana else 'Dias Úteis'
        titulo_base = 'Curtailment, CMO e PLD' if 'val_pld' in perfil.columns else 'Curtailment e CMO'
        plt.title(f'Perfil Horário: {titulo_base} ({self.subsistema} - {periodo_txt})', 
                  fontsize=14, fontweight='bold', pad=20)

        # Legendas combinadas
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', fontsize=10)
        
        # Adicionar nota sobre inclusão de zeros
        dias_analisados = len(todas_datas)
        nota = f'Nota: Média inclui horas sem curtailment ENE (zeros)\n'
        nota += f'{dias_analisados} dias analisados | {horas_com_curtailment}/{total_horas} horas com curtailment'
        plt.figtext(0.99, 0.01, nota, ha='right', va='bottom', fontsize=8, 
                    style='italic', color='gray', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        plt.tight_layout()

        # Salvar gráfico
        sufixo = '_fds' if self.apenas_finais_semana else '_util'
        output_path = self.output_dir / f"perfil_horario_{self.subsistema}{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()

        self.logger.info(f"Gráfico de perfil horário salvo em: {output_path}")

        return output_path

    def gerar_analise_estatistica(self):
        """
        Gera análise estatística da correlação.
        """
        self.logger.info("Gerando análise estatística...")

        if self.dados_combinados is None:
            raise ValueError("Dados combinados não disponíveis")

        # Calcular estatísticas básicas
        correlacao = self.dados_combinados['pct_curtailment'].corr(self.dados_combinados['val_cmo'])

        # Resumos por dia e hora (Brasil)
        df = self.dados_combinados.copy()
        df['data'] = df['din_instante'].dt.date
        horas_por_dia = df.groupby('data').apply(lambda x: (x['pct_curtailment'] > 0).sum()).rename('horas_com_curtailment').reset_index()
        media_horas_dia = float(horas_por_dia['horas_com_curtailment'].mean()) if not horas_por_dia.empty else 0.0
        mediana_horas_dia = float(horas_por_dia['horas_com_curtailment'].median()) if not horas_por_dia.empty else 0.0
        por_hora = df.groupby(df['din_instante'].dt.hour)['pct_curtailment'].apply(lambda s: (s > 0).mean()).reindex(range(24), fill_value=0)

        analise = {
            'correlacao_pearson': correlacao,
            'tamanho_amostra': len(self.dados_combinados),
            'curtailment_medio': self.dados_combinados['pct_curtailment'].mean(),
            'cmo_medio': self.dados_combinados['val_cmo'].mean(),
            'curtailment_std': self.dados_combinados['pct_curtailment'].std(),
            'cmo_std': self.dados_combinados['val_cmo'].std(),
            'horas_com_curtailment_media_por_dia': media_horas_dia,
            'horas_com_curtailment_mediana_por_dia': mediana_horas_dia,
            'fracao_horas_com_curtailment_por_hora_do_dia': por_hora.to_dict(),
            'periodo_analisado': {
                'inicio': self.dados_combinados['din_instante'].min(),
                'fim': self.dados_combinados['din_instante'].max()
            }
        }

        # Salvar análise em arquivo
        sufixo = '_fds' if self.apenas_finais_semana else ''
        output_path = self.output_dir / f"analise_estatistica_{self.subsistema}{sufixo}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

        with open(output_path, 'w', encoding='utf-8') as f:
            periodo_txt = 'FINAIS DE SEMANA' if self.apenas_finais_semana else 'TODOS OS DIAS'
            f.write(f"ANÁLISE DE CORRELAÇÃO: CURTAILMENT vs CMO ({self.subsistema} - {periodo_txt})\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Subsistema: {self.subsistema}\n")
            f.write(f"Período: {periodo_txt}\n")
            f.write(f"Período analisado: {analise['periodo_analisado']['inicio']} até {analise['periodo_analisado']['fim']}\n")
            f.write(f"Tamanho da amostra: {analise['tamanho_amostra']} observações\n\n")

            f.write("ESTATÍSTICAS DESCRITIVAS:\n")
            f.write("-" * 30 + "\n")
            f.write(f"Curtailment médio: {analise['curtailment_medio']:.2f}%\n")
            f.write(f"CMO médio: R$ {analise['cmo_medio']:.2f}/MWh\n")
            f.write(f"Desvio padrão Curtailment: {analise['curtailment_std']:.2f}%\n")
            f.write(f"Desvio padrão CMO: R$ {analise['cmo_std']:.2f}/MWh\n\n")

            f.write(f"RESUMOS DE CURTAILMENT ({self.subsistema}):\n")
            f.write("-" * 30 + "\n")
            f.write(f"Horas com curtailment (média por dia): {analise['horas_com_curtailment_media_por_dia']:.2f}\n")
            f.write(f"Horas com curtailment (mediana por dia): {analise['horas_com_curtailment_mediana_por_dia']:.2f}\n")
            f.write("Frações de horas com curtailment por hora do dia (0..23):\n")
            for h in range(24):
                fr = analise['fracao_horas_com_curtailment_por_hora_do_dia'].get(h, 0)
                f.write(f"  {h:02d}h: {fr:.2%}\n")

            f.write("CORRELAÇÃO:\n")
            f.write("-" * 15 + "\n")
            f.write(f"Coeficiente de Pearson: {analise['correlacao_pearson']:.4f}\n")

            if abs(correlacao) > 0.7:
                interpretacao = "Forte"
            elif abs(correlacao) > 0.3:
                interpretacao = "Moderada"
            else:
                interpretacao = "Fraca"

            f.write(f"Força da correlação: {interpretacao}\n")

        self.logger.info(f"Análise estatística salva em: {output_path}")

        return analise

    def executar_analise_completa(self):
        """
        Executa análise completa de correlação.
        """
        self.logger.info("Iniciando análise completa de correlação...")

        # Carregar dados
        if not self.carregar_dados_curtailment():
            raise ValueError("Falha ao carregar dados de curtailment")

        if not self.carregar_dados_cmo():
            raise ValueError("Falha ao carregar dados de CMO")
        
        # Carregar dados de PLD (opcional)
        pld_carregado = self.carregar_dados_pld()
        if not pld_carregado:
            self.logger.warning("PLD não carregado - gráficos serão gerados apenas com CMO")

        # Combinar dados
        if not self.combinar_dados():
            raise ValueError("Falha ao combinar dados")

        # Gerar gráficos
        grafico_path = self.gerar_graficos_correlacao()
        
        # Gerar gráfico de perfil horário
        grafico_perfil_path = self.gerar_grafico_perfil_horario()

        # Gerar análise estatística
        analise = self.gerar_analise_estatistica()

        self.logger.info("Análise completa finalizada com sucesso!")

        return {
            'grafico_path': grafico_path,
            'grafico_perfil_path': grafico_perfil_path,
            'analise': analise,
            'dados_combinados': self.dados_combinados
        }


def main():
    """Função principal."""
    print("ANÁLISE DE CORRELAÇÃO: CURTAILMENT ENERGÉTICO vs CMO")
    print("=" * 60)

    try:
        # ANÁLISE 1: DIAS ÚTEIS (Segunda a Sexta) - NORDESTE
        print("\n[1/2] Processando DIAS ÚTEIS (Segunda a Sexta) - NORDESTE...")
        print("-" * 60)
        analisador_util = CorrelacaoAnalisador(subsistema='NORDESTE', apenas_finais_semana=False)
        resultado_util = analisador_util.executar_analise_completa()

        # Filtrar apenas dias úteis (0-4 = segunda a sexta)
        resultado_util['dados_combinados']['dia_semana'] = resultado_util['dados_combinados']['din_instante'].dt.dayofweek
        dados_util = resultado_util['dados_combinados'][resultado_util['dados_combinados']['dia_semana'].isin([0,1,2,3,4])].copy()
        
        export_csv_util = Path(resultado_util['grafico_path']).with_name(f'dados_combinados_{analisador_util.subsistema}_util.csv')
        dados_util.to_csv(export_csv_util, index=False)

        print(f"  Grafico correlacao: {resultado_util['grafico_path']}")
        print(f"  Grafico perfil horario: {resultado_util['grafico_perfil_path']}")
        print(f"  Correlacao: {resultado_util['analise']['correlacao_pearson']:.4f}")

        # ANÁLISE 2: FINAIS DE SEMANA (Sábado e Domingo) - NORDESTE
        print("\n[2/2] Processando FINAIS DE SEMANA (Sábado e Domingo) - NORDESTE...")
        print("-" * 60)
        analisador_fds = CorrelacaoAnalisador(subsistema='NORDESTE', apenas_finais_semana=True)
        resultado_fds = analisador_fds.executar_analise_completa()

        export_csv_fds = Path(resultado_fds['grafico_path']).with_name(f'dados_combinados_{analisador_fds.subsistema}_fds.csv')
        resultado_fds['dados_combinados'].to_csv(export_csv_fds, index=False)

        print(f"  Grafico correlacao: {resultado_fds['grafico_path']}")
        print(f"  Grafico perfil horario: {resultado_fds['grafico_perfil_path']}")
        print(f"  Correlacao: {resultado_fds['analise']['correlacao_pearson']:.4f}")

        # RESUMO FINAL
        print("\n" + "=" * 60)
        print("RESUMO COMPARATIVO (NORDESTE):")
        print("=" * 60)
        print(f"DIAS UTEIS:")
        print(f"  - Curtailment medio: {resultado_util['analise']['curtailment_medio']:.2f}%")
        print(f"  - CMO medio: R$ {resultado_util['analise']['cmo_medio']:.2f}/MWh")
        print(f"  - Correlacao: {resultado_util['analise']['correlacao_pearson']:.4f}")
        print(f"\nFINAIS DE SEMANA:")
        print(f"  - Curtailment medio: {resultado_fds['analise']['curtailment_medio']:.2f}%")
        print(f"  - CMO medio: R$ {resultado_fds['analise']['cmo_medio']:.2f}/MWh")
        print(f"  - Correlacao: {resultado_fds['analise']['correlacao_pearson']:.4f}")
        print("\nArquivos salvos em: output/")

        return True

    except Exception as e:
        print(f"Erro durante a analise: {e}")
        logging.error(f"Erro na análise: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
