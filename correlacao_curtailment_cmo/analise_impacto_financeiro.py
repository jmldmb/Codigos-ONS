#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para calcular o impacto financeiro do curtailment por tipo e por mês.

Impacto Financeiro = PLD (R$/MWh) × Curtailment (MWh)

Hipótese: Curtailment energético (ENE) deve ter menor impacto financeiro relativo
porque ocorre em horas de menor preço.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from datetime import datetime, timedelta
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurações
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class AnalisadorImpactoFinanceiro:
    """Analisa o impacto financeiro do curtailment por tipo e período."""
    
    def __init__(self, subsistema='BRASIL'):
        """Inicializa o analisador."""
        self.subsistema = subsistema.upper()
        self.project_root = Path(__file__).parent
        self.output_dir = self.project_root / "output"
        self.output_dir.mkdir(exist_ok=True)
        
        # Dados
        self.dados_curtailment_raw = None
        self.dados_pld = None
        self.impacto_mensal = None
        
        logger.info(f"Analisador iniciado para subsistema: {self.subsistema}")
    
    def carregar_dados_curtailment_raw(self):
        """Carrega dados brutos de curtailment (TODOS os tipos, não apenas ENE)."""
        logger.info("Carregando dados brutos de curtailment (todos os tipos)...")
        
        try:
            raw_dir = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\Curtailment\Dados\raw_data")
            
            # Carregar últimos 12 meses
            dfs = []
            hoje = datetime.now()
            for i in range(12):
                ano = hoje.year
                mes = hoje.month - i
                if mes <= 0:
                    ano -= 1
                    mes += 12
                
                for tipo in ['EOLICA', 'FOTOVOLTAICA']:
                    arquivo = raw_dir / f"RESTRICAO_COFF_{tipo}_{ano}_{mes:02d}.csv"
                    if arquivo.exists():
                        df = pd.read_csv(arquivo, sep=';')
                        df['tipo_fonte'] = tipo
                        dfs.append(df)
                        logger.info(f"Arquivo carregado: {arquivo.name}")
            
            if not dfs:
                raise FileNotFoundError("Nenhum arquivo de curtailment encontrado")
            
            # Combinar todos os dados
            dados_brutos = pd.concat(dfs, ignore_index=True)
            
            # Converter colunas
            dados_brutos['din_instante'] = pd.to_datetime(dados_brutos['din_instante'])
            
            for col in ['val_geracao', 'val_disponibilidade', 'val_geracaoreferencia']:
                dados_brutos[col] = pd.to_numeric(dados_brutos[col], errors='coerce')
            
            # Filtrar período (último ano)
            data_corte = datetime.now() - timedelta(days=365)
            dados_brutos = dados_brutos[dados_brutos['din_instante'] >= data_corte].copy()
            
            # FILTRAR POR SUBSISTEMA (se não for BRASIL)
            if 'nom_subsistema' in dados_brutos.columns:
                if self.subsistema != 'BRASIL':
                    dados_brutos = dados_brutos[dados_brutos['nom_subsistema'].astype(str).str.upper() == self.subsistema].copy()
                    logger.info(f"Dados filtrados para subsistema: {self.subsistema}")
                else:
                    logger.info(f"Processando dados de todos os subsistemas (BRASIL)")
            
            # Calcular curtailment em MWh (não percentual!)
            dados_brutos['potencial_mw'] = dados_brutos[['val_disponibilidade', 'val_geracaoreferencia']].min(axis=1)
            dados_brutos['curtailment_mw'] = (dados_brutos['potencial_mw'] - dados_brutos['val_geracao']).clip(lower=0)
            dados_brutos['curtailment_mwh'] = dados_brutos['curtailment_mw'] * 0.5  # Semi-horário
            
            # Adicionar coluna de tipo de curtailment
            if 'cod_razaorestricao' in dados_brutos.columns:
                dados_brutos['tipo_curtailment'] = dados_brutos['cod_razaorestricao'].astype(str).str.upper()
                
                # FILTRAR APENAS REGISTROS COM RESTRIÇÃO VÁLIDA (excluir nulos/vazios)
                # SR = "Sem Restrição" = não é curtailment válido
                registros_antes = len(dados_brutos)
                dados_brutos = dados_brutos[
                    (dados_brutos['tipo_curtailment'] != 'NAN') &  # Excluir nulos
                    (dados_brutos['tipo_curtailment'] != '') &      # Excluir vazios
                    (dados_brutos['tipo_curtailment'] != 'SR')      # Excluir "Sem Restrição"
                ].copy()
                registros_depois = len(dados_brutos)
                logger.info(f"Registros sem restrição válida excluídos: {registros_antes - registros_depois}")
                logger.info(f"Apenas curtailment com restrição válida: {registros_depois} registros")
            else:
                dados_brutos['tipo_curtailment'] = 'DESCONHECIDO'
            
            # Arredondar para hora cheia
            dados_brutos['hora_cheia'] = dados_brutos['din_instante'].dt.floor('h')
            
            # Agregar por hora (soma dos semi-horários)
            self.dados_curtailment_raw = dados_brutos.groupby(
                ['hora_cheia', 'tipo_curtailment', 'tipo_fonte'], as_index=False
            ).agg({
                'curtailment_mwh': 'sum',
                'nom_subsistema': 'first' if 'nom_subsistema' in dados_brutos.columns else lambda x: self.subsistema
            })
            
            # Renomear coluna
            self.dados_curtailment_raw = self.dados_curtailment_raw.rename(columns={'hora_cheia': 'din_instante'})
            
            logger.info(f"Dados de curtailment carregados: {len(self.dados_curtailment_raw)} registros horários")
            logger.info(f"Tipos de curtailment encontrados: {self.dados_curtailment_raw['tipo_curtailment'].unique()}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados de curtailment: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def carregar_dados_pld(self):
        """Carrega dados de PLD."""
        logger.info(f"Carregando dados de PLD do subsistema: {self.subsistema}...")
        
        try:
            pld_parquet = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\Precos de Energia BR\Data\processed\pld\base_master.parquet")
            
            if not pld_parquet.exists():
                raise FileNotFoundError("Arquivo de PLD não encontrado")
            
            # Carregar dados de PLD
            dados_pld = pd.read_parquet(pld_parquet)
            
            # Renomear colunas
            dados_pld = dados_pld.rename(columns={
                'Data': 'din_instante',
                'Hora': 'hora',
                'Submercado': 'nom_subsistema',
                'Preço': 'val_pld'
            })
            
            # Converter data para datetime
            dados_pld['din_instante'] = pd.to_datetime(dados_pld['din_instante'])
            
            # Criar timestamp hora cheia
            dados_pld['din_instante'] = dados_pld['din_instante'] + pd.to_timedelta(dados_pld['hora'], unit='h')
            
            # Filtrar período (último ano)
            data_corte = datetime.now() - timedelta(days=365)
            dados_pld = dados_pld[dados_pld['din_instante'] >= data_corte]
            
            # Filtrar por subsistema ou calcular média Brasil
            if self.subsistema != 'BRASIL':
                self.dados_pld = dados_pld[dados_pld['nom_subsistema'].astype(str).str.upper() == self.subsistema].copy()
            else:
                # Média de todos os subsistemas
                self.dados_pld = dados_pld.groupby('din_instante', as_index=False)['val_pld'].mean()
                logger.info(f"Calculando PLD médio do Brasil (média dos subsistemas)")
            
            # Manter apenas colunas necessárias
            self.dados_pld = self.dados_pld[['din_instante', 'val_pld']].copy()
            
            logger.info(f"Dados PLD carregados: {len(self.dados_pld)} registros")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados PLD: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def calcular_impacto_financeiro(self):
        """Calcula impacto financeiro: PLD × Curtailment."""
        logger.info("Calculando impacto financeiro do curtailment...")
        
        if self.dados_curtailment_raw is None or self.dados_pld is None:
            raise ValueError("Dados não carregados")
        
        # Merge dos dados
        df_combinado = pd.merge(
            self.dados_curtailment_raw,
            self.dados_pld,
            on='din_instante',
            how='inner'
        )
        
        logger.info(f"Registros após merge: {len(df_combinado)}")
        
        # Calcular impacto financeiro (R$)
        df_combinado['impacto_financeiro_reais'] = df_combinado['curtailment_mwh'] * df_combinado['val_pld']
        
        # Adicionar coluna de ano-mês
        df_combinado['ano_mes'] = df_combinado['din_instante'].dt.to_period('M')
        
        # Agregar por mês e tipo de curtailment
        impacto_mensal = df_combinado.groupby(['ano_mes', 'tipo_curtailment'], as_index=False).agg({
            'impacto_financeiro_reais': 'sum',
            'curtailment_mwh': 'sum',
            'val_pld': 'mean'
        })
        
        # Converter período para datetime para facilitar plotagem
        impacto_mensal['data'] = impacto_mensal['ano_mes'].dt.to_timestamp()
        
        # Calcular PLD médio ponderado por curtailment (para cada tipo)
        pld_ponderado = df_combinado.groupby(['ano_mes', 'tipo_curtailment']).apply(
            lambda x: (x['val_pld'] * x['curtailment_mwh']).sum() / x['curtailment_mwh'].sum() if x['curtailment_mwh'].sum() > 0 else 0
        ).reset_index(name='pld_medio_ponderado')
        
        impacto_mensal = impacto_mensal.merge(pld_ponderado, on=['ano_mes', 'tipo_curtailment'], how='left')
        
        self.impacto_mensal = impacto_mensal
        
        logger.info(f"Impacto financeiro calculado: {len(self.impacto_mensal)} registros")
        
        # Log resumo
        total_impacto = self.impacto_mensal['impacto_financeiro_reais'].sum()
        logger.info(f"Impacto financeiro total (12 meses): R$ {total_impacto:,.2f}")
        
        for tipo in self.impacto_mensal['tipo_curtailment'].unique():
            df_tipo = self.impacto_mensal[self.impacto_mensal['tipo_curtailment'] == tipo]
            impacto_tipo = df_tipo['impacto_financeiro_reais'].sum()
            pct_tipo = (impacto_tipo / total_impacto * 100) if total_impacto > 0 else 0
            pld_medio_tipo = df_tipo['pld_medio_ponderado'].mean()
            logger.info(f"  {tipo}: R$ {impacto_tipo:,.2f} ({pct_tipo:.1f}%) | PLD médio: R$ {pld_medio_tipo:.2f}/MWh")
        
        return True
    
    def gerar_grafico_impacto_mensal(self):
        """Gera gráfico de barras com impacto financeiro por mês e tipo."""
        logger.info("Gerando gráfico de impacto financeiro mensal...")
        
        if self.impacto_mensal is None:
            raise ValueError("Impacto financeiro não calculado")
        
        # Preparar dados para plotagem
        df_plot = self.impacto_mensal.copy()
        
        # Converter impacto para milhões de reais
        df_plot['impacto_milhoes'] = df_plot['impacto_financeiro_reais'] / 1_000_000
        
        # Criar figura
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12))
        
        # GRÁFICO 1: Impacto financeiro por mês e tipo (barras empilhadas)
        pivot_impacto = df_plot.pivot(index='data', columns='tipo_curtailment', values='impacto_milhoes').fillna(0)
        
        pivot_impacto.plot(kind='bar', stacked=True, ax=ax1, width=0.8, edgecolor='black', linewidth=0.5)
        
        ax1.set_title(f'Impacto Financeiro do Curtailment por Mês e Tipo ({self.subsistema})', 
                      fontsize=14, fontweight='bold', pad=20)
        ax1.set_xlabel('Mês', fontsize=12, fontweight='bold')
        ax1.set_ylabel('Impacto Financeiro (Milhões R$)', fontsize=12, fontweight='bold')
        ax1.legend(title='Tipo de Curtailment', loc='upper left', fontsize=10)
        ax1.grid(True, alpha=0.3, axis='y')
        
        # Formatar rótulos do eixo x
        ax1.set_xticklabels([d.strftime('%b/%Y') for d in pivot_impacto.index], rotation=45, ha='right')
        
        # Adicionar valores totais no topo das barras
        for i, data in enumerate(pivot_impacto.index):
            total = pivot_impacto.loc[data].sum()
            ax1.text(i, total, f'R$ {total:.1f}M', ha='center', va='bottom', fontsize=9, fontweight='bold')
        
        # GRÁFICO 2: PLD médio ponderado por tipo de curtailment
        pivot_pld = df_plot.pivot(index='data', columns='tipo_curtailment', values='pld_medio_ponderado').fillna(0)
        
        for col in pivot_pld.columns:
            ax2.plot(pivot_pld.index, pivot_pld[col], marker='o', linewidth=2, label=col, markersize=6)
        
        ax2.set_title(f'PLD Médio Ponderado por Tipo de Curtailment ({self.subsistema})', 
                      fontsize=14, fontweight='bold', pad=20)
        ax2.set_xlabel('Mês', fontsize=12, fontweight='bold')
        ax2.set_ylabel('PLD Médio Ponderado (R$/MWh)', fontsize=12, fontweight='bold')
        ax2.legend(title='Tipo de Curtailment', loc='upper left', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        # Formatar rótulos do eixo x
        ax2.set_xticklabels([d.strftime('%b/%Y') for d in pivot_pld.index], rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Salvar gráfico
        output_path = self.output_dir / f"impacto_financeiro_mensal_{self.subsistema}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Gráfico salvo em: {output_path}")
        
        return output_path
    
    def gerar_relatorio_resumido(self):
        """Gera relatório resumido do impacto financeiro."""
        logger.info("Gerando relatório resumido...")
        
        if self.impacto_mensal is None:
            raise ValueError("Impacto financeiro não calculado")
        
        output_path = self.output_dir / f"relatorio_impacto_financeiro_{self.subsistema}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 100 + "\n")
            f.write(f"RELATÓRIO: IMPACTO FINANCEIRO DO CURTAILMENT ({self.subsistema})\n")
            f.write("=" * 100 + "\n\n")
            
            # Resumo geral
            total_impacto = self.impacto_mensal['impacto_financeiro_reais'].sum()
            total_curtailment = self.impacto_mensal['curtailment_mwh'].sum()
            pld_medio_geral = (total_impacto / total_curtailment) if total_curtailment > 0 else 0
            
            f.write(f"RESUMO GERAL (ÚLTIMOS 12 MESES):\n")
            f.write("-" * 100 + "\n")
            f.write(f"Impacto Financeiro Total: R$ {total_impacto:,.2f}\n")
            f.write(f"Curtailment Total: {total_curtailment:,.2f} MWh\n")
            f.write(f"PLD Médio Ponderado: R$ {pld_medio_geral:.2f}/MWh\n\n")
            
            # Resumo por tipo
            f.write(f"RESUMO POR TIPO DE CURTAILMENT:\n")
            f.write("-" * 100 + "\n")
            f.write(f"{'Tipo':<20} {'Impacto (R$)':<20} {'% Total':<10} {'Curtailment (MWh)':<20} {'PLD Médio (R$/MWh)':<20}\n")
            f.write("-" * 100 + "\n")
            
            for tipo in sorted(self.impacto_mensal['tipo_curtailment'].unique()):
                df_tipo = self.impacto_mensal[self.impacto_mensal['tipo_curtailment'] == tipo]
                impacto_tipo = df_tipo['impacto_financeiro_reais'].sum()
                pct_tipo = (impacto_tipo / total_impacto * 100) if total_impacto > 0 else 0
                curtailment_tipo = df_tipo['curtailment_mwh'].sum()
                pld_medio_tipo = df_tipo['pld_medio_ponderado'].mean()
                
                f.write(f"{tipo:<20} {impacto_tipo:>18,.2f} {pct_tipo:>8.1f}% {curtailment_tipo:>18,.2f} {pld_medio_tipo:>18,.2f}\n")
            
            f.write("\n")
            
            # Detalhamento mensal
            f.write(f"DETALHAMENTO MENSAL:\n")
            f.write("=" * 100 + "\n\n")
            
            for mes in sorted(self.impacto_mensal['ano_mes'].unique()):
                df_mes = self.impacto_mensal[self.impacto_mensal['ano_mes'] == mes]
                impacto_mes = df_mes['impacto_financeiro_reais'].sum()
                
                f.write(f"{mes} - Impacto Total: R$ {impacto_mes:,.2f}\n")
                f.write("-" * 100 + "\n")
                
                for _, row in df_mes.iterrows():
                    f.write(f"  {row['tipo_curtailment']:<15} Impacto: R$ {row['impacto_financeiro_reais']:>15,.2f} | ")
                    f.write(f"Curtailment: {row['curtailment_mwh']:>10,.2f} MWh | ")
                    f.write(f"PLD Médio: R$ {row['pld_medio_ponderado']:>8,.2f}/MWh\n")
                
                f.write("\n")
        
        logger.info(f"Relatório salvo em: {output_path}")
        
        return output_path
    
    def executar_analise_completa(self):
        """Executa análise completa."""
        logger.info("=" * 100)
        logger.info(f"ANÁLISE DE IMPACTO FINANCEIRO DO CURTAILMENT - {self.subsistema}")
        logger.info("=" * 100)
        
        # Carregar dados
        if not self.carregar_dados_curtailment_raw():
            raise ValueError("Falha ao carregar dados de curtailment")
        
        if not self.carregar_dados_pld():
            raise ValueError("Falha ao carregar dados de PLD")
        
        # Calcular impacto
        if not self.calcular_impacto_financeiro():
            raise ValueError("Falha ao calcular impacto financeiro")
        
        # Gerar visualizações
        grafico_path = self.gerar_grafico_impacto_mensal()
        relatorio_path = self.gerar_relatorio_resumido()
        
        logger.info("=" * 100)
        logger.info("ANÁLISE CONCLUÍDA COM SUCESSO!")
        logger.info(f"Gráfico: {grafico_path}")
        logger.info(f"Relatório: {relatorio_path}")
        logger.info("=" * 100)
        
        return {
            'grafico_path': grafico_path,
            'relatorio_path': relatorio_path,
            'dados': self.impacto_mensal
        }


def main():
    """Função principal."""
    # Analisar BRASIL
    analisador = AnalisadorImpactoFinanceiro(subsistema='BRASIL')
    resultado = analisador.executar_analise_completa()
    
    # Exportar dados para CSV
    csv_path = Path(resultado['grafico_path']).with_name(f'impacto_financeiro_BRASIL.csv')
    resultado['dados'].to_csv(csv_path, index=False)
    logger.info(f"Dados exportados para: {csv_path}")


if __name__ == "__main__":
    main()

