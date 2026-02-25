"""
Script atualizado para geração da curva de mérito (Merit Order Curve)
Combina dados de CVU com dados de capacidade de geração
Usa arquivo de equivalência de nomes e filtra apenas térmica/nuclear
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import yaml
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import unicodedata
import re
import os
warnings.filterwarnings('ignore')

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def find_project_root():
    """Encontra o diretório raiz do projeto dinamicamente"""
    current_path = Path.cwd()
    
    # Procurar pelo arquivo config.yaml ou outros marcadores do projeto
    while current_path != current_path.parent:
        if (current_path / "config.yaml").exists() or \
           (current_path / "requirements.txt").exists() or \
           (current_path / "README.md").exists():
            return current_path
        current_path = current_path.parent
    
    # Se não encontrar, procurar pelo diretório CVU termicas em qualquer nível
    current_path = Path.cwd()
    while current_path != current_path.parent:
        # Procurar em subdiretórios
        for subdir in current_path.iterdir():
            if subdir.is_dir():
                cvu_dir = subdir / "CVU termicas"
                if cvu_dir.exists() and (cvu_dir / "config.yaml").exists():
                    return cvu_dir
        current_path = current_path.parent
    
    # Se não encontrar, usar o diretório atual
    return Path.cwd()

class MeritOrderGenerator:
    """Classe para geração da curva de mérito"""
    
    def __init__(self, config_path="config.yaml"):
        """Inicializa com configurações"""
        # Encontrar o diretório raiz do projeto
        self.project_root = find_project_root()
        logger.info(f"Diretório raiz do projeto: {self.project_root}")
        
        # Construir caminho absoluto para o config
        if not Path(config_path).is_absolute():
            config_path = self.project_root / config_path
        
        with open(config_path, 'r') as file:
            self.config = yaml.safe_load(file)
        
        # Construir caminhos absolutos baseados no diretório raiz do projeto
        self.raw_data_path = self.project_root / self.config['paths']['raw_data']
        self.processed_data_path = self.project_root / self.config['paths']['processed_data']
        self.output_charts_path = self.project_root / self.config['paths']['output_charts']
        
        # URL para dados de capacidade de geração
        self.capacity_url = "https://ons-aws-prod-opendata.s3.amazonaws.com/dataset/capacidade-geracao/CAPACIDADE_GERACAO.parquet"
        
        # Criar diretório de saída se não existir
        self.output_charts_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Diretórios configurados:")
        logger.info(f"  Raw data: {self.raw_data_path}")
        logger.info(f"  Processed data: {self.processed_data_path}")
        logger.info(f"  Output charts: {self.output_charts_path}")
    
    def get_all_name_variations(self, name):
        """Retorna todas as variações possíveis de um nome (original, sem acentos, equivalentes)"""
        if pd.isna(name):
            return []
        
        variations = []
        name_str = str(name).strip()
        
        # 1. Nome original
        variations.append(name_str)
        
        # 2. Nome sem acentos
        name_no_accents = unicodedata.normalize('NFD', name_str)
        name_no_accents = ''.join(c for c in name_no_accents if not unicodedata.combining(c))
        if name_no_accents != name_str:
            variations.append(name_no_accents)
        
        # 3. Nome em maiúsculas
        name_upper = name_str.upper()
        if name_upper != name_str:
            variations.append(name_upper)
        
        # 4. Nome sem acentos em maiúsculas
        name_no_accents_upper = name_no_accents.upper()
        if name_no_accents_upper not in variations:
            variations.append(name_no_accents_upper)
        
        # 5. Padronizar números romanos
        for variation in variations[:]:  # Copiar lista para não modificar durante iteração
            # Substituir números romanos
            roman_to_arabic = {
                'I': '1', 'II': '2', 'III': '3', 'IV': '4', 'V': '5',
                'VI': '6', 'VII': '7', 'VIII': '8', 'IX': '9', 'X': '10'
            }
            
            for roman, arabic in roman_to_arabic.items():
                # Procurar por números romanos isolados
                pattern = r'\b' + roman + r'\b'
                if re.search(pattern, variation):
                    new_variation = re.sub(pattern, arabic, variation)
                    if new_variation not in variations:
                        variations.append(new_variation)
                    
                    # Também criar versão com underscore (ex: POTIGUAR_3)
                    new_variation_underscore = re.sub(pattern, '_' + arabic, variation)
                    if new_variation_underscore not in variations:
                        variations.append(new_variation_underscore)
        
        # 6. Remover espaços extras e caracteres especiais
        for variation in variations[:]:
            # Remover espaços extras
            clean_variation = ' '.join(variation.split())
            # Remover caracteres especiais, mantendo apenas letras, números e espaços
            clean_variation = re.sub(r'[^A-Z0-9\s]', '', clean_variation.upper())
            if clean_variation not in variations and clean_variation != '':
                variations.append(clean_variation)
        
        # 7. Extrair palavras-chave (primeira palavra) para casos como "XAVANTES ARUANÃ" -> "XAVANTES"
        for variation in variations[:]:
            words = variation.split()
            if len(words) > 1:
                first_word = words[0]
                if first_word not in variations and len(first_word) > 2:  # Evitar palavras muito curtas
                    variations.append(first_word)
        
        # 8. Lidar com abreviações e pontos (ex: "W.ARJONA O" -> "WILLIAM ARJONA")
        for variation in variations[:]:
            # Expandir abreviações comuns
            abbreviation_map = {
                'W.': 'WILLIAM',
                'J.': 'JOSE',
                'M.': 'MARIA',
                'A.': 'ANGRA',
                'P.': 'POTIGUAR'
            }
            
            for abbrev, full_name in abbreviation_map.items():
                if abbrev in variation:
                    expanded_variation = variation.replace(abbrev, full_name)
                    if expanded_variation not in variations:
                        variations.append(expanded_variation)
        
        return list(set(variations))  # Remover duplicatas
    
    def find_name_match(self, target_name, name_list):
        """Encontra correspondência de nome usando apenas comparação exata"""
        if pd.isna(target_name):
            return None
        
        # Comparação exata apenas
        if target_name in name_list:
            return target_name
        
        return None
    
    def find_name_match_flexible(self, target_name, name_list):
        """Encontra correspondência de nome usando busca flexível para casos específicos"""
        if pd.isna(target_name):
            return None
        
        # Primeiro tentar comparação exata
        if target_name in name_list:
            return target_name
        
        # Busca flexível apenas para casos específicos
        target_variations = self.get_all_name_variations(target_name)
        
        # Criar um conjunto de todas as variações de todos os nomes da lista
        all_name_variations = {}
        for name in name_list:
            if pd.isna(name):
                continue
            name_vars = self.get_all_name_variations(name)
            for var in name_vars:
                all_name_variations[var] = name
        
        # Verificar se alguma variação do target está na lista
        for target_var in target_variations:
            if target_var in all_name_variations:
                matched_name = all_name_variations[target_var]
                # Debug: mostrar correspondência encontrada
                if target_name != matched_name:
                    logger.debug(f"Correspondência flexível encontrada: '{target_name}' -> '{matched_name}' (via '{target_var}')")
                return matched_name
        
        return None
    
    def load_equivalencia_nomes(self):
        """Carrega o arquivo de equivalência de nomes"""
        logger.info("Carregando arquivo de equivalência de nomes...")
        
        equivalencia_path = self.raw_data_path / "equivalencia de nomes.xlsx"
        
        if not equivalencia_path.exists():
            logger.error(f"Arquivo de equivalência não encontrado: {equivalencia_path}")
            return None
        
        try:
            df_equivalencia = pd.read_excel(equivalencia_path)
            logger.info(f"Arquivo de equivalência carregado: {len(df_equivalencia)} mapeamentos")
            return df_equivalencia
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo de equivalência: {e}")
            return None
    
    def download_capacity_data(self):
        """Baixa dados de capacidade de geração"""
        logger.info("Baixando dados de capacidade de geração...")
        
        capacity_file = self.raw_data_path / "CAPACIDADE_GERACAO.parquet"
        
        if not capacity_file.exists():
            try:
                response = requests.get(self.capacity_url, stream=True)
                response.raise_for_status()
                
                with open(capacity_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                logger.info(f"Dados de capacidade baixados: {capacity_file}")
            except Exception as e:
                logger.error(f"Erro ao baixar dados de capacidade: {e}")
                return None
        else:
            logger.info("Dados de capacidade já existem")
        
        return capacity_file
    
    def load_capacity_data(self):
        """Carrega dados de capacidade de geração filtrados por térmica/nuclear e agrega por usina"""
        capacity_file = self.download_capacity_data()
        if capacity_file is None:
            return None
        
        try:
            df_capacity = pd.read_parquet(capacity_file)
            
            # Filtrar apenas térmica e nuclear
            df_filtered = df_capacity[df_capacity['nom_tipousina'].isin(['TÉRMICA', 'NUCLEAR'])].copy()
            
            logger.info(f"Dados de capacidade carregados: {len(df_filtered)} registros térmica/nuclear")
            logger.info(f"Usinas únicas térmica/nuclear: {df_filtered['nom_usina'].nunique()}")
            
            # Agregar por usina (somar potências de múltiplas unidades)
            df_aggregated = df_filtered.groupby(['nom_usina', 'nom_tipousina'])['val_potenciaefetiva'].sum().reset_index()
            
            logger.info(f"Após agregação: {len(df_aggregated)} usinas únicas")
            logger.info(f"Potência total agregada: {df_aggregated['val_potenciaefetiva'].sum():.2f} MW")
            
            return df_aggregated
        except Exception as e:
            logger.error(f"Erro ao carregar dados de capacidade: {e}")
            return None
    
    def load_cvu_data(self, year, month, week):
        """Carrega dados de CVU para um período específico"""
        logger.info(f"Carregando dados CVU para {year}/{month:02d} - semana {week}")
        
        filename = f"CVU_USINA_TERMICA_{year}.parquet"
        filepath = self.raw_data_path / filename
        
        if not filepath.exists():
            logger.error(f"Arquivo CVU não encontrado: {filepath}")
            return None
        
        try:
            df_cvu = pd.read_parquet(filepath)
            
            # Filtrar por mês e semana se especificado
            if month is not None:
                df_cvu = df_cvu[df_cvu['mes_referencia'] == month]
            
            if week is not None:
                # Assumindo que num_revisao corresponde à semana
                df_cvu = df_cvu[df_cvu['num_revisao'] == week]
            
            logger.info(f"Dados CVU carregados: {len(df_cvu)} registros")
            logger.info(f"Usinas únicas CVU: {df_cvu['nom_usina'].nunique()}")
            
            return df_cvu
        except Exception as e:
            logger.error(f"Erro ao carregar dados CVU: {e}")
            return None
    
    def load_indisponibilidade_data(self):
        """Carrega dados de indisponibilidade"""
        logger.info("Carregando dados de indisponibilidade...")
        
        indisponibilidade_file = self.raw_data_path / "indisponibilidade.xlsx"
        
        if not indisponibilidade_file.exists():
            logger.warning(f"Arquivo de indisponibilidade não encontrado: {indisponibilidade_file}")
            return None
        
        try:
            df_indisponibilidade = pd.read_excel(indisponibilidade_file)
            logger.info(f"Dados de indisponibilidade carregados: {len(df_indisponibilidade)} usinas")
            logger.info(f"Colunas: {list(df_indisponibilidade.columns)}")
            return df_indisponibilidade
        except Exception as e:
            logger.error(f"Erro ao carregar dados de indisponibilidade: {e}")
            return None

    def load_exceptions_cvu(self):
        """Carrega dados de exceções CVU"""
        logger.info("Carregando dados de exceções CVU...")
        
        exceptions_file = self.raw_data_path / "exceptions cvu.xlsx"
        
        if not exceptions_file.exists():
            logger.warning(f"Arquivo de exceções CVU não encontrado: {exceptions_file}")
            return None
        
        try:
            df_exceptions = pd.read_excel(exceptions_file)
            logger.info(f"Dados de exceções CVU carregados: {len(df_exceptions)} usinas")
            logger.info(f"Colunas: {list(df_exceptions.columns)}")
            return df_exceptions
        except Exception as e:
            logger.error(f"Erro ao carregar dados de exceções CVU: {e}")
            return None

    def load_inflexibilidade_data(self):
        """Carrega dados de inflexibilidade"""
        logger.info("Carregando dados de inflexibilidade...")
        
        inflexibilidade_file = self.raw_data_path / "inflexibilidade.xlsx"
        
        if not inflexibilidade_file.exists():
            logger.warning(f"Arquivo de inflexibilidade não encontrado: {inflexibilidade_file}")
            return None
        
        try:
            df_inflexibilidade = pd.read_excel(inflexibilidade_file)
            logger.info(f"Dados de inflexibilidade carregados: {len(df_inflexibilidade)} usinas")
            logger.info(f"Colunas: {list(df_inflexibilidade.columns)}")
            
            # Verificar soma da inflexibilidade para janeiro (mês 1)
            if 1 in df_inflexibilidade.columns:
                soma_janeiro = df_inflexibilidade[1].sum()
                logger.info(f"Soma da inflexibilidade para janeiro: {soma_janeiro:.2f} MW")
            
            # Armazenar dados originais para análise posterior
            self.df_inflexibilidade_original = df_inflexibilidade.copy()
            
            return df_inflexibilidade
        except Exception as e:
            logger.error(f"Erro ao carregar dados de inflexibilidade: {e}")
            return None
    
    def apply_equivalencia_mapping(self, df_cvu, df_equivalencia):
        """Aplica o mapeamento de equivalência de nomes usando comparação exata"""
        logger.info("Aplicando mapeamento de equivalência de nomes...")
        
        # Criar dicionário de equivalência (bidirecional)
        equivalencia_dict = {}
        equivalencia_reverse = {}
        for _, row in df_equivalencia.iterrows():
            cvu_name = row['nom_usina_cvu']
            capacity_name = row['nom_usina_capacidade']
            equivalencia_dict[cvu_name] = capacity_name
            equivalencia_reverse[capacity_name] = cvu_name
        
        # Aplicar mapeamento no DataFrame CVU
        df_cvu_mapped = df_cvu.copy()
        df_cvu_mapped['usina_mapeada'] = None
        
        # Debug: mostrar equivalências disponíveis
        logger.info(f"Equivalências disponíveis: {list(equivalencia_dict.keys())}")
        
        mapeamentos_aplicados = 0
        for idx, row in df_cvu_mapped.iterrows():
            cvu_name = row['nom_usina']
            
            # Apenas mapeamento direto da tabela de equivalência
            if cvu_name in equivalencia_dict:
                df_cvu_mapped.at[idx, 'usina_mapeada'] = equivalencia_dict[cvu_name]
                mapeamentos_aplicados += 1
                logger.debug(f"Mapeamento aplicado: {cvu_name} -> {equivalencia_dict[cvu_name]}")
            else:
                # Debug: mostrar usinas que não encontraram equivalência
                logger.debug(f"Usina sem equivalência: {cvu_name}")
        
        # Usar o nome mapeado quando disponível, senão usar o original
        df_cvu_mapped['usina_final'] = df_cvu_mapped['usina_mapeada'].fillna(df_cvu_mapped['nom_usina'])
        
        logger.info(f"Mapeamentos aplicados: {mapeamentos_aplicados} de {len(df_cvu_mapped)}")
        
        # Debug: mostrar alguns mapeamentos aplicados
        if mapeamentos_aplicados > 0:
            logger.info("Exemplos de mapeamentos aplicados:")
            mapped_usinas = df_cvu_mapped[df_cvu_mapped['usina_mapeada'].notna()].head(5)
            for _, row in mapped_usinas.iterrows():
                logger.info(f"  {row['nom_usina']} -> {row['usina_mapeada']}")
        
        return df_cvu_mapped
    
    def audit_matches(self, df_cvu, df_capacity, df_equivalencia, year, month, week):
        """Audita correspondências entre as bases de dados com busca flexível"""
        logger.info("Iniciando auditoria de correspondências...")
        
        # Aplicar mapeamento de equivalência
        df_cvu_mapped = self.apply_equivalencia_mapping(df_cvu, df_equivalencia)
        
        # Obter listas únicas de usinas
        cvu_usinas = df_cvu_mapped['usina_final'].unique()
        capacity_usinas = df_capacity['nom_usina'].unique()
        
        logger.info(f"Usinas únicas na base CVU (após mapeamento): {len(cvu_usinas)}")
        logger.info(f"Usinas únicas na base Capacidade: {len(capacity_usinas)}")
        
        # Criar dicionário de equivalência para verificação
        equivalencia_dict = {}
        for _, row in df_equivalencia.iterrows():
            cvu_name = row['nom_usina_cvu']
            capacity_name = row['nom_usina_capacidade']
            equivalencia_dict[cvu_name] = capacity_name
        
        # Encontrar correspondências usando comparação exata
        matches = []
        cvu_only = []
        capacity_only = []
        
        # Verificar quais usinas CVU encontram correspondência na capacidade
        for cvu_orig in cvu_usinas:
            matched_capacity = None
            
            # Primeiro verificar se está na tabela de equivalência
            if cvu_orig in equivalencia_dict:
                matched_capacity = equivalencia_dict[cvu_orig]
            else:
                # Se não, tentar correspondência exata direta
                matched_capacity = self.find_name_match(cvu_orig, capacity_usinas)
            
            if matched_capacity:
                matches.append({
                    'cvu_original': cvu_orig,
                    'capacity_original': matched_capacity,
                    'mapeamento_aplicado': cvu_orig in df_cvu_mapped[df_cvu_mapped['usina_mapeada'].notna()]['usina_final'].values
                })
            else:
                cvu_only.append(cvu_orig)
        
        # Verificar quais usinas de capacidade não foram encontradas
        matched_capacity_names = [m['capacity_original'] for m in matches]
        for capacity_orig in capacity_usinas:
            if capacity_orig not in matched_capacity_names:
                capacity_only.append(capacity_orig)
        
        # Gerar relatório de auditoria
        audit_report = {
            'matches': matches,
            'cvu_only': cvu_only,
            'capacity_only': capacity_only,
            'total_matches': len(matches),
            'total_cvu_only': len(cvu_only),
            'total_capacity_only': len(capacity_only),
            'mapeamentos_aplicados': len([m for m in matches if m['mapeamento_aplicado']])
        }
        
        # Salvar relatório de auditoria (sem dados de inflexibilidade ainda)
        self.save_audit_report(audit_report, year, month, week)
        
        logger.info(f"Correspondências encontradas: {len(matches)}")
        logger.info(f"Usinas apenas na base CVU: {len(cvu_only)}")
        logger.info(f"Usinas apenas na base Capacidade: {len(capacity_only)}")
        logger.info(f"Mapeamentos aplicados: {audit_report['mapeamentos_aplicados']}")
        
        # Debug: mostrar algumas correspondências encontradas
        if len(matches) > 0:
            logger.info("Exemplos de correspondências encontradas:")
            for i, match in enumerate(matches[:5]):  # Mostrar apenas os primeiros 5
                logger.info(f"  {match['cvu_original']} -> {match['capacity_original']}")
        
        # Debug: mostrar algumas usinas não encontradas
        if len(cvu_only) > 0:
            logger.info("Exemplos de usinas CVU não encontradas:")
            for i, usina in enumerate(cvu_only[:5]):  # Mostrar apenas os primeiros 5
                logger.info(f"  {usina}")
        
        return audit_report, df_cvu_mapped
    
    def save_audit_report(self, audit_report, year, month, week, df_merged=None):
        """Salva relatório de auditoria em formato Excel"""
        logger.info("Salvando relatório de auditoria em Excel...")
        
        # Criar DataFrames para salvar
        matches_df = pd.DataFrame(audit_report['matches'])
        cvu_only_df = pd.DataFrame({'usina': audit_report['cvu_only']})
        capacity_only_df = pd.DataFrame({'usina': audit_report['capacity_only']})
        
        # Criar resumo
        summary = {
            'total_matches': audit_report['total_matches'],
            'total_cvu_only': audit_report['total_cvu_only'],
            'total_capacity_only': audit_report['total_capacity_only'],
            'mapeamentos_aplicados': audit_report['mapeamentos_aplicados'],
            'match_rate': audit_report['total_matches'] / (audit_report['total_matches'] + audit_report['total_cvu_only']) * 100
        }
        
        # Criar DataFrame de resumo
        summary_df = pd.DataFrame([{
            'Período': f'{year}/{month:02d} - Semana {week}',
            'Data/Hora': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Correspondências encontradas': summary['total_matches'],
            'Usinas apenas na base CVU': summary['total_cvu_only'],
            'Usinas apenas na base Capacidade': summary['total_capacity_only'],
            'Mapeamentos aplicados': summary['mapeamentos_aplicados'],
            'Taxa de correspondência (%)': f"{summary['match_rate']:.1f}"
        }])
        
        # Criar DataFrame de inflexibilidade se disponível
        inflexibilidade_df = None
        inflexibilidade_nao_aplicada_df = None
        
        if df_merged is not None and 'inflexibilidade' in df_merged.columns:
            inflexibilidade_df = df_merged[['usina', 'val_potenciaefetiva_original', 'inflexibilidade', 'potencia_flexivel']].copy()
            inflexibilidade_df = inflexibilidade_df.sort_values('inflexibilidade', ascending=False)
            inflexibilidade_df['percentual_inflexibilidade'] = (inflexibilidade_df['inflexibilidade'] / inflexibilidade_df['val_potenciaefetiva_original'] * 100).round(2)
            
            # Adicionar coluna indicando se teve inflexibilidade aplicada
            inflexibilidade_df['teve_inflexibilidade'] = inflexibilidade_df['inflexibilidade'] > 0
            
            # Reorganizar colunas
            inflexibilidade_df = inflexibilidade_df[['usina', 'teve_inflexibilidade', 'val_potenciaefetiva_original', 'inflexibilidade', 'potencia_flexivel', 'percentual_inflexibilidade']]
            
            # Criar análise de inflexibilidade não aplicada
            if hasattr(self, 'df_inflexibilidade_original') and self.df_inflexibilidade_original is not None:
                 # Obter todas as usinas da planilha de inflexibilidade
                 todas_usinas_inflex = self.df_inflexibilidade_original['nom_usina_cvu'].unique()
                 
                 # Usinas que estão na planilha mas não foram aplicadas
                 usinas_nao_aplicadas = []
                 for usina_inflex in todas_usinas_inflex:
                     # Obter valor de inflexibilidade da planilha
                     inflex_planilha = self.df_inflexibilidade_original[self.df_inflexibilidade_original['nom_usina_cvu'] == usina_inflex][month].iloc[0] if month in self.df_inflexibilidade_original.columns else 0
                     
                     # Tentar encontrar pelo mapeamento de equivalência
                     usina_mapeada = None
                     if hasattr(self, 'df_equivalencia'):
                         equivalencia_dict = dict(zip(self.df_equivalencia['nom_usina_cvu'], self.df_equivalencia['nom_usina_capacidade']))
                         usina_mapeada = equivalencia_dict.get(usina_inflex)
                     
                     # Verificar se a usina mapeada está no df_merged
                     if usina_mapeada and usina_mapeada in df_merged['usina'].values:
                         # Verificar se a inflexibilidade foi aplicada corretamente
                         usina_no_merged = df_merged[df_merged['usina'] == usina_mapeada]
                         if len(usina_no_merged) > 0:
                             inflex_aplicada = usina_no_merged['inflexibilidade'].iloc[0]
                             if inflex_aplicada != inflex_planilha:
                                 # Inflexibilidade foi aplicada mas com valor diferente
                                 usinas_nao_aplicadas.append({
                                     'usina_original': usina_inflex,
                                     'usina_mapeada': usina_mapeada,
                                     'motivo': f'Inflexibilidade aplicada incorretamente (planilha: {inflex_planilha:.2f}, aplicada: {inflex_aplicada:.2f})',
                                     'inflexibilidade_planilha': inflex_planilha,
                                     'inflexibilidade_aplicada': inflex_aplicada
                                 })
                         else:
                             # Usina foi mapeada mas não está no merge final
                             usinas_nao_aplicadas.append({
                                 'usina_original': usina_inflex,
                                 'usina_mapeada': usina_mapeada,
                                 'motivo': 'Mapeada mas não encontrada no merge final',
                                 'inflexibilidade_planilha': inflex_planilha,
                                 'inflexibilidade_aplicada': 0
                             })
                     else:
                         # Usina não foi mapeada ou não encontrada no df_merged
                         motivo = 'Não mapeada na planilha de equivalência'
                         if usina_mapeada:
                             motivo = 'Mapeada mas não encontrada no merge final'
                         
                         usinas_nao_aplicadas.append({
                             'usina_original': usina_inflex,
                             'usina_mapeada': usina_mapeada,
                             'motivo': motivo,
                             'inflexibilidade_planilha': inflex_planilha,
                             'inflexibilidade_aplicada': 0
                         })
                 
                 if usinas_nao_aplicadas:
                     inflexibilidade_nao_aplicada_df = pd.DataFrame(usinas_nao_aplicadas)
                     inflexibilidade_nao_aplicada_df = inflexibilidade_nao_aplicada_df.sort_values('inflexibilidade_planilha', ascending=False)
        
        # Salvar arquivo Excel com múltiplas abas
        base_filename = f"audit_report_{year}_{month:02d}_week{week}"
        excel_file = self.output_charts_path / f"{base_filename}.xlsx"
        
        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
            # Aba de resumo
            summary_df.to_excel(writer, sheet_name='Resumo', index=False)
            
            # Aba de correspondências
            if len(matches_df) > 0:
                matches_df.to_excel(writer, sheet_name='Correspondências', index=False)
            
            # Aba de usinas apenas CVU
            if len(cvu_only_df) > 0:
                cvu_only_df.to_excel(writer, sheet_name='Usinas Apenas CVU', index=False)
            
            # Aba de usinas apenas Capacidade
            if len(capacity_only_df) > 0:
                capacity_only_df.to_excel(writer, sheet_name='Usinas Apenas Capacidade', index=False)
            
            # Aba de inflexibilidade
            if inflexibilidade_df is not None and len(inflexibilidade_df) > 0:
                inflexibilidade_df.to_excel(writer, sheet_name='Inflexibilidade', index=False)
            
            # Aba de inflexibilidade não aplicada
            if inflexibilidade_nao_aplicada_df is not None and len(inflexibilidade_nao_aplicada_df) > 0:
                inflexibilidade_nao_aplicada_df.to_excel(writer, sheet_name='Inflexibilidade Não Aplicada', index=False)
        
        logger.info(f"Relatório de auditoria salvo em Excel: {excel_file}")
        
        # Manter também o arquivo de texto para compatibilidade
        summary_file = self.output_charts_path / f"{base_filename}_summary.txt"
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE AUDITORIA DE CORRESPONDÊNCIAS MELHORADO\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Período: {year}/{month:02d} - Semana {week}\n")
            f.write(f"Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"Correspondências encontradas: {summary['total_matches']}\n")
            f.write(f"Usinas apenas na base CVU: {summary['total_cvu_only']}\n")
            f.write(f"Usinas apenas na base Capacidade: {summary['total_capacity_only']}\n")
            f.write(f"Mapeamentos aplicados: {summary['mapeamentos_aplicados']}\n")
            f.write(f"Taxa de correspondência: {summary['match_rate']:.1f}%\n\n")
            
            # Adicionar informações de inflexibilidade no texto
            if inflexibilidade_df is not None and len(inflexibilidade_df) > 0:
                f.write("INFORMAÇÕES DE INFLEXIBILIDADE:\n")
                f.write("-" * 35 + "\n")
                total_inflex = inflexibilidade_df['inflexibilidade'].sum()
                usinas_com_inflex = inflexibilidade_df['teve_inflexibilidade'].sum()
                total_potencia = inflexibilidade_df['val_potenciaefetiva_original'].sum()
                potencia_flexivel = inflexibilidade_df['potencia_flexivel'].sum()
                
                f.write(f"Total de usinas analisadas: {len(inflexibilidade_df)}\n")
                f.write(f"Usinas com inflexibilidade aplicada: {usinas_com_inflex}\n")
                f.write(f"Usinas sem inflexibilidade: {len(inflexibilidade_df) - usinas_com_inflex}\n")
                f.write(f"Potência total original: {total_potencia:.2f} MW\n")
                f.write(f"Inflexibilidade total: {total_inflex:.2f} MW\n")
                f.write(f"Potência flexível: {potencia_flexivel:.2f} MW\n")
                f.write(f"Redução total: {total_potencia - potencia_flexivel:.2f} MW\n")
                f.write(f"Percentual de inflexibilidade: {(total_inflex/total_potencia*100):.1f}%\n\n")
                
                f.write("USINAS COM INFLEXIBILIDADE APLICADA:\n")
                f.write("-" * 40 + "\n")
                usinas_com_inflex_df = inflexibilidade_df[inflexibilidade_df['teve_inflexibilidade'] == True]
                for _, row in usinas_com_inflex_df.iterrows():
                    f.write(f"- {row['usina']}: {row['inflexibilidade']:.2f} MW ({row['percentual_inflexibilidade']:.1f}%)\n")
                f.write("\n")
                
                # Adicionar informações sobre inflexibilidade não aplicada
                if inflexibilidade_nao_aplicada_df is not None and len(inflexibilidade_nao_aplicada_df) > 0:
                    f.write("USINAS COM INFLEXIBILIDADE NÃO APLICADA:\n")
                    f.write("-" * 45 + "\n")
                    total_inflex_nao_aplicada = inflexibilidade_nao_aplicada_df['inflexibilidade_planilha'].sum()
                    f.write(f"Total de inflexibilidade não aplicada: {total_inflex_nao_aplicada:.2f} MW\n")
                    f.write(f"Usinas com inflexibilidade não aplicada: {len(inflexibilidade_nao_aplicada_df)}\n\n")
                    
                    for _, row in inflexibilidade_nao_aplicada_df.iterrows():
                        f.write(f"- {row['usina_original']}: {row['inflexibilidade_planilha']:.2f} MW\n")
                        f.write(f"  Motivo: {row['motivo']}\n")
                        if pd.notna(row['usina_mapeada']):
                            f.write(f"  Usina mapeada: {row['usina_mapeada']}\n")
                        f.write("\n")
            
            if audit_report['cvu_only']:
                f.write("USINAS APENAS NA BASE CVU:\n")
                f.write("-" * 30 + "\n")
                for usina in audit_report['cvu_only']:
                    f.write(f"- {usina}\n")
                f.write("\n")
            
            if audit_report['capacity_only']:
                f.write("USINAS APENAS NA BASE CAPACIDADE:\n")
                f.write("-" * 35 + "\n")
                for usina in audit_report['capacity_only']:
                    f.write(f"- {usina}\n")
        
        logger.info(f"Resumo em texto salvo: {summary_file}")
    
    def merge_cvu_capacity(self, df_cvu_mapped, df_capacity, df_indisponibilidade=None, df_exceptions=None, df_inflexibilidade=None, month=None, df_cvu_original=None):
        """Combina dados de CVU com dados de capacidade usando mapeamento e aplica funcionalidades completas"""
        logger.info("Combinando dados de CVU com capacidade usando mapeamento...")
        
        # Preparar dados de CVU
        df_cvu_clean = df_cvu_mapped[['usina_final', 'val_cvu', 'ano_referencia', 'mes_referencia', 'num_revisao']].copy()
        df_cvu_clean = df_cvu_clean.rename(columns={'usina_final': 'usina'})
        
        # Criar dicionário de equivalência bidirecional para uso na inflexibilidade
        equivalencia_dict = {}
        equivalencia_reverse = {}
        if hasattr(self, 'df_equivalencia'):
            for _, row in self.df_equivalencia.iterrows():
                cvu_name = row['nom_usina_cvu']
                capacity_name = row['nom_usina_capacidade']
                equivalencia_dict[cvu_name] = capacity_name
                equivalencia_reverse[capacity_name] = cvu_name
        
        # Preparar dados de capacidade
        df_capacity_clean = df_capacity[['nom_usina', 'val_potenciaefetiva', 'nom_tipousina']].copy()
        
        # 1. EXCEÇÕES JÁ FORAM APLICADAS ANTES DA EQUIVALÊNCIA
        # (Removido daqui para evitar duplicação)
        
        # 2. APLICAR INDISPONIBILIDADE COM COMPARAÇÃO EXATA
        if df_indisponibilidade is not None:
            logger.info("Aplicando filtro de indisponibilidade com comparação exata...")
            
            # Criar lista de nomes de indisponibilidade
            indisponibilidade_names = df_indisponibilidade['nom_usina_cvu'].unique().tolist()
            
            # Filtrar usinas indisponíveis usando comparação exata
            usinas_para_remover = []
            for capacity_name in df_capacity_clean['nom_usina'].unique():
                if capacity_name in indisponibilidade_names:
                    usinas_para_remover.append(capacity_name)
            
            df_capacity_clean = df_capacity_clean[~df_capacity_clean['nom_usina'].isin(usinas_para_remover)]
            logger.info(f"Usinas indisponíveis removidas: {len(usinas_para_remover)} usinas")
        
        # Debug: mostrar algumas usinas antes do merge
        logger.info("Exemplos de usinas CVU antes do merge:")
        for usina in df_cvu_clean['usina'].head(10):
            logger.info(f"  {usina}")
        
        logger.info("Exemplos de usinas Capacidade antes do merge:")
        for usina in df_capacity_clean['nom_usina'].head(10):
            logger.info(f"  {usina}")
        
        # Fazer merge
        df_merged = df_cvu_clean.merge(
            df_capacity_clean, 
            left_on='usina',
            right_on='nom_usina', 
            how='inner'
        )
        
        # Remover registros sem capacidade
        df_merged = df_merged.dropna(subset=['val_potenciaefetiva'])
        
        # Para usinas de capacidade que não encontraram CVU, tentar usar equivalência reversa
        # Primeiro, identificar usinas de capacidade que não estão no merge
        usinas_capacidade_sem_cvu = df_capacity_clean[~df_capacity_clean['nom_usina'].isin(df_merged['nom_usina'])]
        
        if len(usinas_capacidade_sem_cvu) > 0:
            logger.info(f"Usinas de capacidade sem CVU encontradas: {len(usinas_capacidade_sem_cvu)}")
            
            # Para cada usina de capacidade sem CVU, verificar se existe equivalência reversa
            for _, row in usinas_capacidade_sem_cvu.iterrows():
                capacity_name = row['nom_usina']
                
                # Verificar se existe equivalência reversa
                if capacity_name in equivalencia_reverse:
                    cvu_name_original = equivalencia_reverse[capacity_name]
                    
                    # Buscar CVU da usina original
                    cvu_original = df_cvu_clean[df_cvu_clean['usina'] == cvu_name_original]
                    if len(cvu_original) > 0:
                        # Adicionar esta usina ao merge com o CVU encontrado
                        new_row = row.copy()
                        new_row['usina'] = cvu_name_original
                        new_row['val_cvu'] = cvu_original['val_cvu'].iloc[0]
                        new_row['nom_usina'] = capacity_name  # Manter o nome da capacidade
                        
                        # Adicionar ao DataFrame merged
                        df_merged = pd.concat([df_merged, pd.DataFrame([new_row])], ignore_index=True)
                        logger.info(f"CVU aplicado via equivalência reversa: {capacity_name} -> {cvu_name_original} -> CVU = {cvu_original['val_cvu'].iloc[0]}")
                    else:
                        logger.debug(f"Equivalência reversa encontrada mas CVU não disponível: {capacity_name} -> {cvu_name_original}")
                else:
                    logger.debug(f"Sem equivalência reversa: {capacity_name}")
        
        # Debug: mostrar resultado do merge
        logger.info(f"Usinas após merge: {len(df_merged)}")
        logger.info("Exemplos de usinas após merge:")
        for usina in df_merged['usina'].head(10):
            logger.info(f"  {usina}")
        
        # 3. APLICAR INFLEXIBILIDADE COM COMPARAÇÃO EXATA E EQUIVALÊNCIA
        if df_inflexibilidade is not None and month is not None:
            logger.info(f"Aplicando inflexibilidade para o mês {month} com comparação exata e equivalência...")
            
            # Preparar dados de inflexibilidade para o mês específico
            df_inflex_mes = df_inflexibilidade[['nom_usina_cvu', month]].copy()
            df_inflex_mes = df_inflex_mes.rename(columns={month: 'inflexibilidade'})
            
            # Criar dicionário de inflexibilidade para busca rápida
            inflexibilidade_dict = {}
            for _, row in df_inflex_mes.iterrows():
                inflexibilidade_dict[row['nom_usina_cvu']] = row['inflexibilidade']
            
            # Aplicar inflexibilidade usando comparação exata com equivalência
            df_merged['inflexibilidade'] = 0.0  # Inicializar com 0
            
            inflexibilidade_aplicada = 0
            for idx, row in df_merged.iterrows():
                merged_name = row['usina']
                
                # Primeiro tentar correspondência exata direta
                if merged_name in inflexibilidade_dict:
                    df_merged.at[idx, 'inflexibilidade'] = inflexibilidade_dict[merged_name]
                    inflexibilidade_aplicada += 1
                else:
                    # Se não encontrar, verificar se está na tabela de equivalência
                    # Buscar o nome original CVU que corresponde ao nome final
                    for cvu_name, capacity_name in equivalencia_dict.items():
                        if capacity_name == merged_name:
                            # Encontrar inflexibilidade usando o nome CVU original
                            if cvu_name in inflexibilidade_dict:
                                df_merged.at[idx, 'inflexibilidade'] = inflexibilidade_dict[cvu_name]
                                inflexibilidade_aplicada += 1
                                logger.debug(f"Inflexibilidade aplicada via equivalência: {merged_name} -> {cvu_name} -> {inflexibilidade_dict[cvu_name]}")
                            break
            
            logger.info(f"Inflexibilidade aplicada: {inflexibilidade_aplicada} usinas")
            
            # Preencher inflexibilidade com 0 para usinas não encontradas
            df_merged['inflexibilidade'] = df_merged['inflexibilidade'].fillna(0)
            
            # Verificar consistência: inflexibilidade deve ser menor que potência total
            inconsistencias = df_merged[df_merged['inflexibilidade'] > df_merged['val_potenciaefetiva']]
            if len(inconsistencias) > 0:
                logger.warning(f"Encontradas {len(inconsistencias)} inconsistências onde inflexibilidade > potência total:")
                for _, row in inconsistencias.iterrows():
                    logger.warning(f"  {row['usina']}: Potência={row['val_potenciaefetiva']:.2f}, Inflexibilidade={row['inflexibilidade']:.2f}")
            
            # Calcular potência flexível (potência total - inflexibilidade)
            df_merged['potencia_flexivel'] = df_merged['val_potenciaefetiva'] - df_merged['inflexibilidade']
            
            # Garantir que potência flexível não seja negativa
            df_merged['potencia_flexivel'] = df_merged['potencia_flexivel'].clip(lower=0)
            
            # Usar potência flexível como potência efetiva para a curva de mérito
            df_merged['val_potenciaefetiva_original'] = df_merged['val_potenciaefetiva'].copy()
            df_merged['val_potenciaefetiva'] = df_merged['potencia_flexivel']
            
            logger.info(f"Inflexibilidade aplicada:")
            logger.info(f"  Total de usinas: {len(df_merged)}")
            logger.info(f"  Usinas com inflexibilidade > 0: {(df_merged['inflexibilidade'] > 0).sum()}")
            logger.info(f"  Potência total original: {df_merged['val_potenciaefetiva_original'].sum():.2f} MW")
            logger.info(f"  Potência flexível: {df_merged['potencia_flexivel'].sum():.2f} MW")
            logger.info(f"  Redução total: {df_merged['val_potenciaefetiva_original'].sum() - df_merged['potencia_flexivel'].sum():.2f} MW")
        
        # Verificar CVUs zerados após aplicação de exceções
        cvus_zerados = df_merged[df_merged['val_cvu'] == 0]
        if len(cvus_zerados) > 0:
            logger.warning(f"Encontradas {len(cvus_zerados)} usinas com CVU = 0 após aplicação de exceções:")
            for _, row in cvus_zerados.iterrows():
                logger.warning(f"  {row['usina']}: CVU = {row['val_cvu']}")
                
                # Debug: verificar se a usina estava na base CVU original
                if df_cvu_original is not None:
                    original_cvu = df_cvu_original[df_cvu_original['nom_usina'] == row['usina']]
                    if len(original_cvu) > 0:
                        logger.warning(f"    -> CVU original: {original_cvu['val_cvu'].iloc[0]}")
                    else:
                        logger.warning(f"    -> Não encontrada na base CVU original")
                else:
                    logger.warning(f"    -> Base CVU original não disponível para debug")
        
        logger.info(f"Dados combinados: {len(df_merged)} registros")
        logger.info(f"Usinas únicas: {df_merged['nom_usina'].nunique()}")
        logger.info(f"CVUs únicos: {df_merged['val_cvu'].nunique()}")
        logger.info(f"CVU médio: {df_merged['val_cvu'].mean():.2f}")
        logger.info(f"CVU mínimo: {df_merged['val_cvu'].min():.2f}")
        logger.info(f"CVU máximo: {df_merged['val_cvu'].max():.2f}")
        
        return df_merged
    
    def preprocess_cvu_data(self, df_cvu, df_equivalencia, df_indisponibilidade, df_exceptions):
        """
        Pré-processa dados CVU aplicando indisponibilidade e exceções com equivalência de nomes
        """
        logger.info("Iniciando pré-processamento de dados CVU...")
        
        # Fazer uma cópia dos dados CVU originais
        df_cvu_processed = df_cvu.copy()
        
        # Criar dicionários de equivalência para busca rápida
        equivalencia_dict = {}
        equivalencia_reverse = {}
        if df_equivalencia is not None:
            for _, row in df_equivalencia.iterrows():
                cvu_name = row['nom_usina_cvu']
                capacity_name = row['nom_usina_capacidade']
                equivalencia_dict[cvu_name] = capacity_name
                equivalencia_reverse[capacity_name] = cvu_name
        
        # 1. REMOÇÃO DE INDISPONIBILIDADE (PRIMEIRA ETAPA)
        if df_indisponibilidade is not None:
            logger.info("=== ETAPA 1: Remoção de indisponibilidade ===")
            
            # Lista de usinas indisponíveis (nomes originais)
            indisponibilidade_names = df_indisponibilidade['nom_usina_cvu'].unique().tolist()
            logger.info(f"Usinas indisponíveis (originais): {len(indisponibilidade_names)}")
            
            # Remover usinas indisponíveis com nomes originais
            usinas_removidas_originais = []
            for idx, row in df_cvu_processed.iterrows():
                if row['nom_usina'] in indisponibilidade_names:
                    usinas_removidas_originais.append(row['nom_usina'])
                    df_cvu_processed = df_cvu_processed.drop(idx)
            
            logger.info(f"Usinas removidas (nomes originais): {len(usinas_removidas_originais)}")
            for usina in usinas_removidas_originais:
                logger.info(f"  Removida: {usina}")
            
            # Converter nomes de indisponibilidade segundo equivalência e remover
            usinas_removidas_convertidas = []
            for indisponivel in indisponibilidade_names:
                if indisponivel in equivalencia_dict:
                    nome_convertido = equivalencia_dict[indisponivel]
                    # Buscar e remover usinas com nome convertido
                    for idx, row in df_cvu_processed.iterrows():
                        if row['nom_usina'] == nome_convertido:
                            usinas_removidas_convertidas.append(f"{indisponivel} -> {nome_convertido}")
                            df_cvu_processed = df_cvu_processed.drop(idx)
                            break
            
            logger.info(f"Usinas removidas (nomes convertidos): {len(usinas_removidas_convertidas)}")
            for usina in usinas_removidas_convertidas:
                logger.info(f"  Removida: {usina}")
            
            logger.info(f"Total de usinas removidas por indisponibilidade: {len(usinas_removidas_originais) + len(usinas_removidas_convertidas)}")
        
        # 2. APLICAÇÃO DE EXCEÇÕES CVU (SEGUNDA ETAPA)
        if df_exceptions is not None:
            logger.info("=== ETAPA 2: Aplicação de exceções CVU ===")
            
            # Criar dicionário de exceções para busca rápida
            exceptions_dict = {}
            for _, row in df_exceptions.iterrows():
                exception_name = row['nom_usina_cvu']
                exceptions_dict[exception_name] = row['val_cvu']
            
            logger.info(f"Exceções disponíveis (originais): {len(exceptions_dict)}")
            
            # Aplicar exceções com nomes originais
            excecoes_aplicadas_originais = 0
            for idx, row in df_cvu_processed.iterrows():
                cvu_name = row['nom_usina']
                if cvu_name in exceptions_dict:
                    df_cvu_processed.at[idx, 'val_cvu'] = exceptions_dict[cvu_name]
                    excecoes_aplicadas_originais += 1
                    logger.info(f"Exceção aplicada (original): {cvu_name} -> CVU = {exceptions_dict[cvu_name]}")
            
            logger.info(f"Exceções aplicadas (nomes originais): {excecoes_aplicadas_originais}")
            
            # Aplicar exceções com nomes convertidos
            excecoes_aplicadas_convertidas = 0
            for exception_name, exception_cvu in exceptions_dict.items():
                if exception_name in equivalencia_dict:
                    nome_convertido = equivalencia_dict[exception_name]
                    # Buscar usinas com nome convertido e aplicar exceção
                    for idx, row in df_cvu_processed.iterrows():
                        if row['nom_usina'] == nome_convertido:
                            df_cvu_processed.at[idx, 'val_cvu'] = exception_cvu
                            excecoes_aplicadas_convertidas += 1
                            logger.info(f"Exceção aplicada (convertida): {exception_name} -> {nome_convertido} -> CVU = {exception_cvu}")
                            break
            
            logger.info(f"Exceções aplicadas (nomes convertidos): {excecoes_aplicadas_convertidas}")
            logger.info(f"Total de exceções aplicadas: {excecoes_aplicadas_originais + excecoes_aplicadas_convertidas}")
        
        # 3. VALIDAÇÃO PÓS-PROCESSAMENTO
        logger.info("=== ETAPA 3: Validação pós-processamento ===")
        
        # Verificar CVUs zerados
        cvus_zerados = df_cvu_processed[df_cvu_processed['val_cvu'] == 0]
        if len(cvus_zerados) > 0:
            logger.warning(f"Encontradas {len(cvus_zerados)} usinas com CVU = 0 após processamento:")
            
            for _, row in cvus_zerados.iterrows():
                usina_name = row['nom_usina']
                logger.warning(f"  {usina_name}: CVU = {row['val_cvu']}")
                
                # Verificar se está em exceções
                if df_exceptions is not None:
                    em_excecoes = df_exceptions[df_exceptions['nom_usina_cvu'] == usina_name]
                    if len(em_excecoes) > 0:
                        logger.warning(f"    -> ENCONTRADA em exceções com CVU = {em_excecoes['val_cvu'].iloc[0]}")
                    else:
                        logger.warning(f"    -> NÃO encontrada em exceções")
                
                # Verificar se está em indisponibilidade
                if df_indisponibilidade is not None:
                    em_indisponibilidade = df_indisponibilidade[df_indisponibilidade['nom_usina_cvu'] == usina_name]
                    if len(em_indisponibilidade) > 0:
                        logger.warning(f"    -> ENCONTRADA em indisponibilidade")
                    else:
                        logger.warning(f"    -> NÃO encontrada em indisponibilidade")
                
                # Verificar equivalência
                if usina_name in equivalencia_reverse:
                    nome_original = equivalencia_reverse[usina_name]
                    logger.warning(f"    -> Equivalência: {usina_name} <-> {nome_original}")
                    
                    # Verificar se o nome original está em exceções
                    if df_exceptions is not None:
                        em_excecoes_original = df_exceptions[df_exceptions['nom_usina_cvu'] == nome_original]
                        if len(em_excecoes_original) > 0:
                            logger.warning(f"    -> Nome original ENCONTRADO em exceções com CVU = {em_excecoes_original['val_cvu'].iloc[0]}")
                    
                    # Verificar se o nome original está em indisponibilidade
                    if df_indisponibilidade is not None:
                        em_indisponibilidade_original = df_indisponibilidade[df_indisponibilidade['nom_usina_cvu'] == nome_original]
                        if len(em_indisponibilidade_original) > 0:
                            logger.warning(f"    -> Nome original ENCONTRADO em indisponibilidade")
        else:
            logger.info("Nenhuma usina com CVU = 0 encontrada após processamento")
        
        logger.info(f"Pré-processamento concluído. Usinas restantes: {len(df_cvu_processed)}")
        return df_cvu_processed

    def generate_merit_order_curve(self, df_merged, year, month, week):
        """Gera a curva de mérito"""
        logger.info("Gerando curva de mérito...")
        
        # Ordenar por CVU
        df_sorted = df_merged.sort_values('val_cvu').copy()
        
        # Calcular capacidade acumulada
        df_sorted['capacidade_acumulada'] = df_sorted['val_potenciaefetiva'].cumsum()
        
        # Configurar estilo do gráfico
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Criar figura com apenas um gráfico
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        
        # Curva de mérito
        ax.plot(df_sorted['capacidade_acumulada'], df_sorted['val_cvu'], 
                linewidth=2, color='blue', alpha=0.7)
        ax.scatter(df_sorted['capacidade_acumulada'], df_sorted['val_cvu'], 
                   s=30, color='red', alpha=0.6)
        
        ax.set_xlabel('Capacidade Acumulada (MW)', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        
        # Título dinâmico baseado nas funcionalidades aplicadas
        title = f'Curva de Mérito - {year}/{month:02d} - Semana {week}'
        if 'inflexibilidade' in df_sorted.columns:
            title += ' (Ajustada por Inflexibilidade)'
        if 'val_cvu_exception' in df_sorted.columns:
            title += ' (Com Exceções CVU)'
        
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Adicionar estatísticas
        total_capacity = df_sorted['val_potenciaefetiva'].sum()
        avg_cvu = df_sorted['val_cvu'].mean()
        min_cvu = df_sorted['val_cvu'].min()
        max_cvu = df_sorted['val_cvu'].max()
        
        stats_text = f'Total: {total_capacity:.0f} MW\nMédia CVU: {avg_cvu:.1f} R$/MWh\nMin: {min_cvu:.1f} R$/MWh\nMax: {max_cvu:.1f} R$/MWh'
        
        # Adicionar informações de inflexibilidade se disponível
        if 'inflexibilidade' in df_sorted.columns:
            total_inflex = df_sorted['inflexibilidade'].sum()
            usinas_com_inflex = (df_sorted['inflexibilidade'] > 0).sum()
            stats_text += f'\nInflexibilidade Total: {total_inflex:.0f} MW\nUsinas com Inflexibilidade: {usinas_com_inflex}'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
        
        plt.tight_layout()
        
        # Salvar gráfico
        filename = f"merit_order_curve_{year}_{month:02d}_week{week}.png"
        filepath = self.output_charts_path / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Curva de mérito salva: {filepath}")
        
        return df_sorted
    
    def generate_merit_order_table(self, df_sorted, year, month, week):
        """Gera tabela de mérito"""
        logger.info("Gerando tabela de mérito...")
        
        # Selecionar colunas para a tabela
        columns_to_include = ['usina', 'val_cvu', 'val_potenciaefetiva', 'capacidade_acumulada', 'nom_tipousina']
        
        # Adicionar colunas de inflexibilidade se disponíveis
        if 'inflexibilidade' in df_sorted.columns:
            columns_to_include.extend(['inflexibilidade', 'potencia_flexivel'])
        if 'val_potenciaefetiva_original' in df_sorted.columns:
            columns_to_include.append('val_potenciaefetiva_original')
        
        # Criar tabela de mérito
        merit_table = df_sorted[columns_to_include].copy()
        merit_table = merit_table.reset_index(drop=True)
        merit_table.index = merit_table.index + 1  # Ranking começa em 1
        
        # Salvar tabela
        filename = f"merit_order_table_{year}_{month:02d}_week{week}.xlsx"
        filepath = self.output_charts_path / filename
        merit_table.to_excel(filepath, index=True, index_label='Ranking')
        
        logger.info(f"Tabela de mérito salva: {filepath}")
        
        return merit_table

    def compare_merit_orders(self, date1, date2):
        """
        Compara curvas de mérito de duas datas diferentes
        date1, date2: tuplas (year, month, week)
        """
        logger.info(f"Comparando pilhas térmicas: {date1[0]}/{date1[1]:02d} semana {date1[2]} vs {date2[0]}/{date2[1]:02d} semana {date2[2]}")
        
        # Gerar dados para as duas datas
        result1 = self.generate_merit_order(date1[0], date1[1], date1[2])
        result2 = self.generate_merit_order(date2[0], date2[1], date2[2])
        
        if result1 is None or result2 is None:
            logger.error("Não foi possível gerar dados para uma ou ambas as datas")
            return None
        
        df_sorted1 = result1['sorted_data']
        df_sorted2 = result2['sorted_data']
        
        # Configurar estilo do gráfico
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Criar figura com apenas um gráfico
        fig, ax = plt.subplots(1, 1, figsize=(14, 8))
        
        # Curvas de mérito sobrepostas
        ax.plot(df_sorted1['capacidade_acumulada'], df_sorted1['val_cvu'], 
                linewidth=2, color='blue', alpha=0.7, label=f'{date1[0]}/{date1[1]:02d} semana {date1[2]}')
        ax.scatter(df_sorted1['capacidade_acumulada'], df_sorted1['val_cvu'], 
                   s=30, color='blue', alpha=0.6)
        
        ax.plot(df_sorted2['capacidade_acumulada'], df_sorted2['val_cvu'], 
                linewidth=2, color='red', alpha=0.7, label=f'{date2[0]}/{date2[1]:02d} semana {date2[2]}')
        ax.scatter(df_sorted2['capacidade_acumulada'], df_sorted2['val_cvu'], 
                   s=30, color='red', alpha=0.6)
        
        ax.set_xlabel('Capacidade Acumulada (MW)', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        ax.set_title('Comparação de Curvas de Mérito', fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Adicionar estatísticas
        stats_text1 = f'Data 1: {date1[0]}/{date1[1]:02d} semana {date1[2]}\n'
        stats_text1 += f'Total: {df_sorted1["val_potenciaefetiva"].sum():.0f} MW\n'
        stats_text1 += f'Média CVU: {df_sorted1["val_cvu"].mean():.1f} R$/MWh\n'
        stats_text1 += f'Min: {df_sorted1["val_cvu"].min():.1f} R$/MWh\n'
        stats_text1 += f'Max: {df_sorted1["val_cvu"].max():.1f} R$/MWh'
        
        stats_text2 = f'Data 2: {date2[0]}/{date2[1]:02d} semana {date2[2]}\n'
        stats_text2 += f'Total: {df_sorted2["val_potenciaefetiva"].sum():.0f} MW\n'
        stats_text2 += f'Média CVU: {df_sorted2["val_cvu"].mean():.1f} R$/MWh\n'
        stats_text2 += f'Min: {df_sorted2["val_cvu"].min():.1f} R$/MWh\n'
        stats_text2 += f'Max: {df_sorted2["val_cvu"].max():.1f} R$/MWh'
        
        # Adicionar estatísticas de comparação
        diff_capacity = df_sorted2['val_potenciaefetiva'].sum() - df_sorted1['val_potenciaefetiva'].sum()
        diff_avg_cvu = df_sorted2['val_cvu'].mean() - df_sorted1['val_cvu'].mean()
        
        comparison_text = f'Diferenças:\n'
        comparison_text += f'Capacidade: {diff_capacity:+.0f} MW\n'
        comparison_text += f'CVU Médio: {diff_avg_cvu:+.1f} R$/MWh\n'
        comparison_text += f'Usinas Data 1: {len(df_sorted1)}\n'
        comparison_text += f'Usinas Data 2: {len(df_sorted2)}'
        
        ax.text(0.02, 0.98, stats_text1, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        ax.text(0.02, 0.70, stats_text2, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightcoral', alpha=0.8))
        ax.text(0.02, 0.42, comparison_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.8))
        
        plt.tight_layout()
        
        # Salvar gráfico
        filename = f"merit_order_comparison_{date1[0]}_{date1[1]:02d}_week{date1[2]}_vs_{date2[0]}_{date2[1]:02d}_week{date2[2]}.png"
        filepath = self.output_charts_path / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Comparação salva: {filepath}")
        
        # Gerar tabela de comparação
        comparison_table = self.generate_comparison_table(df_sorted1, df_sorted2, date1, date2)
        
        return {
            'data1': result1,
            'data2': result2,
            'comparison_chart': filepath,
            'comparison_table': comparison_table
        }
    
    def generate_comparison_table(self, df_sorted1, df_sorted2, date1, date2):
        """Gera tabela de comparação entre duas datas"""
        logger.info("Gerando tabela de comparação...")
        
        # Criar DataFrame de comparação
        comparison_data = []
        
        # Usinas que estão em ambas as datas
        usinas_comuns = set(df_sorted1['usina']) & set(df_sorted2['usina'])
        
        for usina in usinas_comuns:
            row1 = df_sorted1[df_sorted1['usina'] == usina].iloc[0]
            row2 = df_sorted2[df_sorted2['usina'] == usina].iloc[0]
            
            comparison_data.append({
                'usina': usina,
                'cvu_data1': row1['val_cvu'],
                'potencia_data1': row1['val_potenciaefetiva'],
                'cvu_data2': row2['val_cvu'],
                'potencia_data2': row2['val_potenciaefetiva'],
                'diff_cvu': row2['val_cvu'] - row1['val_cvu'],
                'diff_potencia': row2['val_potenciaefetiva'] - row1['val_potenciaefetiva']
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        df_comparison = df_comparison.sort_values('diff_cvu', ascending=False)
        
        # Adicionar estatísticas
        stats_row = {
            'usina': 'ESTATÍSTICAS',
            'cvu_data1': df_sorted1['val_cvu'].mean(),
            'potencia_data1': df_sorted1['val_potenciaefetiva'].sum(),
            'cvu_data2': df_sorted2['val_cvu'].mean(),
            'potencia_data2': df_sorted2['val_potenciaefetiva'].sum(),
            'diff_cvu': df_sorted2['val_cvu'].mean() - df_sorted1['val_cvu'].mean(),
            'diff_potencia': df_sorted2['val_potenciaefetiva'].sum() - df_sorted1['val_potenciaefetiva'].sum()
        }
        
        df_comparison = pd.concat([df_comparison, pd.DataFrame([stats_row])], ignore_index=True)
        
        # Salvar tabela
        filename = f"merit_order_comparison_{date1[0]}_{date1[1]:02d}_week{date1[2]}_vs_{date2[0]}_{date2[1]:02d}_week{date2[2]}.xlsx"
        filepath = self.output_charts_path / filename
        df_comparison.to_excel(filepath, index=False)
        
        logger.info(f"Tabela de comparação salva: {filepath}")
        
        return df_comparison

    def generate_merit_order(self, year, month, week):
        """Gera curva de mérito completa para uma semana específica"""
        logger.info(f"Gerando curva de mérito para {year}/{month:02d} - semana {week}")
        
        # Carregar dados
        df_equivalencia = self.load_equivalencia_nomes()
        if df_equivalencia is None:
            logger.error("Não foi possível carregar arquivo de equivalência")
            return None
        
        # Armazenar equivalência como atributo da classe para uso na inflexibilidade
        self.df_equivalencia = df_equivalencia
        
        df_capacity = self.load_capacity_data()
        if df_capacity is None:
            logger.error("Não foi possível carregar dados de capacidade")
            return None
        
        df_cvu = self.load_cvu_data(year, month, week)
        if df_cvu is None:
            logger.error("Não foi possível carregar dados CVU")
            return None
        
        # Carregar dados de inflexibilidade
        df_inflexibilidade = self.load_inflexibilidade_data()
        if df_inflexibilidade is None:
            logger.warning("Dados de inflexibilidade não disponíveis - usando potência total")
        
        # Carregar dados de exceções CVU
        df_exceptions = self.load_exceptions_cvu()
        if df_exceptions is None:
            logger.warning("Dados de exceções CVU não disponíveis - usando CVU original")
        
        # Carregar dados de indisponibilidade
        df_indisponibilidade = self.load_indisponibilidade_data()
        if df_indisponibilidade is None:
            logger.warning("Dados de indisponibilidade não disponíveis - incluindo todas as usinas")
        
        # NOVA LÓGICA: PRÉ-PROCESSAMENTO DE CVU
        df_cvu_processed = self.preprocess_cvu_data(df_cvu, df_equivalencia, df_indisponibilidade, df_exceptions)
        
        # Auditar correspondências com dados pré-processados
        audit_report, df_cvu_mapped = self.audit_matches(df_cvu_processed, df_capacity, df_equivalencia, year, month, week)
        
        # Combinar dados (sem indisponibilidade, já aplicada no pré-processamento)
        df_merged = self.merge_cvu_capacity(df_cvu_mapped, df_capacity, None, None, df_inflexibilidade, month, df_cvu_processed)
        
        if len(df_merged) == 0:
            logger.warning("Nenhum dado combinado encontrado")
            return None
        
        # Salvar relatório de auditoria atualizado com dados de inflexibilidade
        self.save_audit_report(audit_report, year, month, week, df_merged)
        
        # Gerar curva de mérito
        df_sorted = self.generate_merit_order_curve(df_merged, year, month, week)
        
        # Gerar tabela de mérito
        merit_table = self.generate_merit_order_table(df_sorted, year, month, week)
        
        logger.info("Processamento concluído com sucesso")
        
        return {
            'audit_report': audit_report,
            'merged_data': df_merged,
            'sorted_data': df_sorted,
            'merit_table': merit_table
        }

    def compare_with_historical_data(self, current_date=None):
        """
        Compara a pilha atual com dados históricos (2 meses atrás e 1 ano atrás)
        current_date: tupla (year, month, week) - se None, usa a data atual
        """
        from datetime import datetime, timedelta
        
        # Se não fornecer data atual, usar a data atual do sistema
        if current_date is None:
            now = datetime.now()
            current_date = (now.year, now.month, now.day)
            # Converter para semana (simplificado - assumir semana 1)
            current_date = (current_date[0], current_date[1], 1)
        
        logger.info(f"Comparando pilha atual ({current_date[0]}/{current_date[1]:02d} semana {current_date[2]}) com dados históricos")
        
        # Calcular datas históricas
        year, month, week = current_date
        
        # Data de 2 meses atrás
        month_2_ago = month - 2
        year_2_ago = year
        if month_2_ago <= 0:
            month_2_ago += 12
            year_2_ago -= 1
        
        # Data de 1 ano atrás
        year_1_ago = year - 1
        
        date_current = (year, month, week)
        date_2_months_ago = (year_2_ago, month_2_ago, week)
        date_1_year_ago = (year_1_ago, month, week)
        
        logger.info(f"Datas para comparação:")
        logger.info(f"  Atual: {date_current[0]}/{date_current[1]:02d} semana {date_current[2]}")
        logger.info(f"  2 meses atrás: {date_2_months_ago[0]}/{date_2_months_ago[1]:02d} semana {date_2_months_ago[2]}")
        logger.info(f"  1 ano atrás: {date_1_year_ago[0]}/{date_1_year_ago[1]:02d} semana {date_1_year_ago[2]}")
        
        # Gerar dados para as três datas
        result_current = self.generate_merit_order(date_current[0], date_current[1], date_current[2])
        result_2_months = self.generate_merit_order(date_2_months_ago[0], date_2_months_ago[1], date_2_months_ago[2])
        result_1_year = self.generate_merit_order(date_1_year_ago[0], date_1_year_ago[1], date_1_year_ago[2])
        
        if result_current is None or result_2_months is None or result_1_year is None:
            logger.error("Não foi possível gerar dados para uma ou mais datas")
            return None
        
        df_current = result_current['sorted_data']
        df_2_months = result_2_months['sorted_data']
        df_1_year = result_1_year['sorted_data']
        
        # Configurar estilo do gráfico
        plt.style.use('default')
        sns.set_palette("husl")
        
        # Criar figura com três curvas
        fig, ax = plt.subplots(1, 1, figsize=(16, 10))
        
        # Curvas de mérito sobrepostas
        ax.plot(df_current['capacidade_acumulada'], df_current['val_cvu'], 
                linewidth=3, color='blue', alpha=0.8, label=f'Atual: {date_current[0]}/{date_current[1]:02d} semana {date_current[2]}')
        ax.scatter(df_current['capacidade_acumulada'], df_current['val_cvu'], 
                   s=40, color='blue', alpha=0.7)
        
        ax.plot(df_2_months['capacidade_acumulada'], df_2_months['val_cvu'], 
                linewidth=2, color='red', alpha=0.7, label=f'2 meses atrás: {date_2_months_ago[0]}/{date_2_months_ago[1]:02d} semana {date_2_months_ago[2]}')
        ax.scatter(df_2_months['capacidade_acumulada'], df_2_months['val_cvu'], 
                   s=30, color='red', alpha=0.6)
        
        ax.plot(df_1_year['capacidade_acumulada'], df_1_year['val_cvu'], 
                linewidth=2, color='green', alpha=0.7, label=f'1 ano atrás: {date_1_year_ago[0]}/{date_1_year_ago[1]:02d} semana {date_1_year_ago[2]}')
        ax.scatter(df_1_year['capacidade_acumulada'], df_1_year['val_cvu'], 
                   s=30, color='green', alpha=0.6)
        
        ax.set_xlabel('Capacidade Acumulada (MW)', fontsize=12)
        ax.set_ylabel('CVU (R$/MWh)', fontsize=12)
        ax.set_title('Evolução Temporal da Curva de Mérito', fontsize=16, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        
        # Adicionar estatísticas
        stats_text = f'ESTATÍSTICAS:\n\n'
        stats_text += f'ATUAL ({date_current[0]}/{date_current[1]:02d}):\n'
        stats_text += f'  Total: {df_current["val_potenciaefetiva"].sum():.0f} MW\n'
        stats_text += f'  CVU Médio: {df_current["val_cvu"].mean():.1f} R$/MWh\n'
        stats_text += f'  CVU Min: {df_current["val_cvu"].min():.1f} R$/MWh\n'
        stats_text += f'  CVU Max: {df_current["val_cvu"].max():.1f} R$/MWh\n\n'
        
        stats_text += f'2 MESES ATRÁS ({date_2_months_ago[0]}/{date_2_months_ago[1]:02d}):\n'
        stats_text += f'  Total: {df_2_months["val_potenciaefetiva"].sum():.0f} MW\n'
        stats_text += f'  CVU Médio: {df_2_months["val_cvu"].mean():.1f} R$/MWh\n'
        stats_text += f'  Diferença CVU: {df_current["val_cvu"].mean() - df_2_months["val_cvu"].mean():+.1f} R$/MWh\n\n'
        
        stats_text += f'1 ANO ATRÁS ({date_1_year_ago[0]}/{date_1_year_ago[1]:02d}):\n'
        stats_text += f'  Total: {df_1_year["val_potenciaefetiva"].sum():.0f} MW\n'
        stats_text += f'  CVU Médio: {df_1_year["val_cvu"].mean():.1f} R$/MWh\n'
        stats_text += f'  Diferença CVU: {df_current["val_cvu"].mean() - df_1_year["val_cvu"].mean():+.1f} R$/MWh'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, 
                verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.9),
                fontsize=9)
        
        plt.tight_layout()
        
        # Salvar gráfico
        filename = f"merit_order_historical_comparison_{date_current[0]}_{date_current[1]:02d}_week{date_current[2]}.png"
        filepath = self.output_charts_path / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"Comparação histórica salva: {filepath}")
        
        # Gerar tabela de comparação histórica
        historical_table = self.generate_historical_comparison_table(df_current, df_2_months, df_1_year, 
                                                                   date_current, date_2_months_ago, date_1_year_ago)
        
        return {
            'current_data': result_current,
            'data_2_months': result_2_months,
            'data_1_year': result_1_year,
            'historical_chart': filepath,
            'historical_table': historical_table
        }
    
    def generate_historical_comparison_table(self, df_current, df_2_months, df_1_year, 
                                           date_current, date_2_months, date_1_year):
        """Gera tabela de comparação histórica"""
        logger.info("Gerando tabela de comparação histórica...")
        
        # Criar DataFrame de comparação
        comparison_data = []
        
        # Usinas que estão em todas as três datas
        usinas_comuns = set(df_current['usina']) & set(df_2_months['usina']) & set(df_1_year['usina'])
        
        for usina in usinas_comuns:
            row_current = df_current[df_current['usina'] == usina].iloc[0]
            row_2_months = df_2_months[df_2_months['usina'] == usina].iloc[0]
            row_1_year = df_1_year[df_1_year['usina'] == usina].iloc[0]
            
            comparison_data.append({
                'usina': usina,
                'cvu_atual': row_current['val_cvu'],
                'potencia_atual': row_current['val_potenciaefetiva'],
                'cvu_2_meses': row_2_months['val_cvu'],
                'potencia_2_meses': row_2_months['val_potenciaefetiva'],
                'cvu_1_ano': row_1_year['val_cvu'],
                'potencia_1_ano': row_1_year['val_potenciaefetiva'],
                'diff_cvu_2m': row_current['val_cvu'] - row_2_months['val_cvu'],
                'diff_cvu_1a': row_current['val_cvu'] - row_1_year['val_cvu'],
                'diff_potencia_2m': row_current['val_potenciaefetiva'] - row_2_months['val_potenciaefetiva'],
                'diff_potencia_1a': row_current['val_potenciaefetiva'] - row_1_year['val_potenciaefetiva']
            })
        
        df_comparison = pd.DataFrame(comparison_data)
        df_comparison = df_comparison.sort_values('diff_cvu_1a', ascending=False)
        
        # Adicionar estatísticas
        stats_row = {
            'usina': 'ESTATÍSTICAS',
            'cvu_atual': df_current['val_cvu'].mean(),
            'potencia_atual': df_current['val_potenciaefetiva'].sum(),
            'cvu_2_meses': df_2_months['val_cvu'].mean(),
            'potencia_2_meses': df_2_months['val_potenciaefetiva'].sum(),
            'cvu_1_ano': df_1_year['val_cvu'].mean(),
            'potencia_1_ano': df_1_year['val_potenciaefetiva'].sum(),
            'diff_cvu_2m': df_current['val_cvu'].mean() - df_2_months['val_cvu'].mean(),
            'diff_cvu_1a': df_current['val_cvu'].mean() - df_1_year['val_cvu'].mean(),
            'diff_potencia_2m': df_current['val_potenciaefetiva'].sum() - df_2_months['val_potenciaefetiva'].sum(),
            'diff_potencia_1a': df_current['val_potenciaefetiva'].sum() - df_1_year['val_potenciaefetiva'].sum()
        }
        
        df_comparison = pd.concat([df_comparison, pd.DataFrame([stats_row])], ignore_index=True)
        
        # Salvar tabela
        filename = f"merit_order_historical_comparison_{date_current[0]}_{date_current[1]:02d}_week{date_current[2]}.xlsx"
        filepath = self.output_charts_path / filename
        df_comparison.to_excel(filepath, index=False)
        
        logger.info(f"Tabela de comparação histórica salva: {filepath}")
        
        return df_comparison

def main():
    """Função principal"""
    generator = MeritOrderGenerator()
    
    # Exemplo de uso para uma data específica
    year = 2025
    month = 8
    week = 1
    
    result = generator.generate_merit_order(year, month, week)
    
    if result:
        print("Processamento concluído com sucesso!")
        print(f"Correspondências encontradas: {result['audit_report']['total_matches']}")
        print(f"Taxa de correspondência: {result['audit_report']['total_matches'] / (result['audit_report']['total_matches'] + result['audit_report']['total_cvu_only']) * 100:.1f}%")
    else:
        print("Erro no processamento")
    
    # COMPARAÇÃO DE DUAS DATAS
    print("\n" + "="*50)
    print("COMPARAÇÃO DE PILHAS TÉRMICAS")
    print("="*50)
    
    # Definir as duas datas para comparação
    date1 = (2025, 8, 1)  # Agosto 2025, semana 1
    date2 = (2025, 6, 1)  # Junho 2025, semana 1
    
    print(f"Comparando: {date1[0]}/{date1[1]:02d} semana {date1[2]} vs {date2[0]}/{date2[1]:02d} semana {date2[2]}")
    
    comparison_result = generator.compare_merit_orders(date1, date2)
    
    if comparison_result:
        print("Comparação concluída com sucesso!")
        print(f"Gráfico salvo: {comparison_result['comparison_chart']}")
        print(f"Tabela salva: {comparison_result['comparison_table'].name if hasattr(comparison_result['comparison_table'], 'name') else 'Tabela de comparação'}")
    else:
        print("Erro na comparação")
    
    # COMPARAÇÃO HISTÓRICA AUTOMÁTICA
    print("\n" + "="*50)
    print("COMPARAÇÃO HISTÓRICA AUTOMÁTICA")
    print("="*50)
    
    # Usar a data atual (ou uma data específica para teste)
    current_date = (2025, 8, 1)  # Para teste, usar agosto 2025
    
    print(f"Comparando pilha atual com dados históricos (2 meses e 1 ano atrás)")
    print(f"Data atual: {current_date[0]}/{current_date[1]:02d} semana {current_date[2]}")
    
    historical_result = generator.compare_with_historical_data(current_date)
    
    if historical_result:
        print("Comparação histórica concluída com sucesso!")
        print(f"Gráfico histórico salvo: {historical_result['historical_chart']}")
        print(f"Tabela histórica salva: {historical_result['historical_table'].name if hasattr(historical_result['historical_table'], 'name') else 'Tabela histórica'}")
    else:
        print("Erro na comparação histórica")

    print("Finalizando...")

if __name__ == "__main__":
    main() 