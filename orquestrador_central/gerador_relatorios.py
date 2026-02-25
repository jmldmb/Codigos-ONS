#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
GERADOR DE RELATÓRIOS PERSONALIZADOS
====================================

Sistema para coletar gráficos de diferentes rotinas e organizá-los em relatórios.
"""

import os
import sys
import glob
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd
from datetime import datetime
import logging

class GeradorRelatorios:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent.parent
        self.output_path = self.base_path / "relatorios"
        self.output_path.mkdir(exist_ok=True)
        
        # Configurar logging
        self._configurar_logging()
        
        # Configurações dos projetos na ordem especificada
        self.projetos = {
            'carga': {
                'nome': 'Análise de Carga Energética',
                'path': self.base_path / 'Codigos ONS' / 'Carga',
                'graficos': {
                    'crescimento_yoy': {
                        'padrao': '**/crescimento_yoy*.png',
                        'descricao': 'Crescimento YoY - Carga'
                    },
                    'comparacao_horaria': {
                        'padrao': '**/comparacao_horaria*.png',
                        'descricao': 'Comparação Horária - Carga'
                    }
                }
            },
            'carga_liquida': {
                'nome': 'Análise de Carga Líquida',
                'path': self.base_path / 'Codigos ONS' / 'carga_liquida',
                'graficos': {
                    'grafico_soma_valores': {
                        'padrao': '**/grafico_soma_valores*.png',
                        'descricao': 'Soma de Valores e Média Móvel 24h'
                    },
                    'componentes_geracao': {
                        'padrao': '**/componentes_geracao*.png',
                        'descricao': 'Componentes de Geração'
                    },
                    'grafico_diario': {
                        'padrao': '**/grafico_2025-*.png',
                        'descricao': 'Gráfico Diário'
                    }
                }
            },
            'curtailment_brasil': {
                'nome': 'Curtailment - Nível Brasil',
                'path': self.base_path / 'Codigos ONS' / 'Curtailment',
                'graficos': {
                    'h_abs_brasil': {
                        'padrao': '**/H_abs_Brasil*.png',
                        'descricao': 'Curtailment Absoluto - Brasil'
                    },
                    'h_pct_brasil': {
                        'padrao': '**/H_pct_Brasil*.png',
                        'descricao': 'Curtailment Percentual - Brasil'
                    },
                    'abs_brasil': {
                        'padrao': '**/abs_Brasil*.png',
                        'descricao': 'Curtailment Absoluto - Brasil'
                    },
                    'pct_brasil': {
                        'padrao': '**/pct_Brasil*.png',
                        'descricao': 'Curtailment Percentual - Brasil'
                    }
                }
            },
            'precos_energia': {
                'nome': 'Sistema de Preços de Energia BR',
                'path': self.base_path / 'Codigos ONS' / 'Precos de Energia BR',
                'graficos': {
                    'pld_se': {
                        'padrao': '**/pld_se*.png',
                        'descricao': 'PLD SE'
                    },
                    'price_se': {
                        'padrao': '**/price_se*.png',
                        'descricao': 'Preço SE'
                    },
                    'spread_nordeste_se': {
                        'padrao': '**/spread_nordeste_se*.png',
                        'descricao': 'Spread Nordeste-SE'
                    },
                    'spread_norte_se': {
                        'padrao': '**/spread_norte_se*.png',
                        'descricao': 'Spread Norte-SE'
                    },
                    'spread_ne': {
                        'padrao': '**/spread_ne*.png',
                        'descricao': 'Spread Nordeste'
                    }
                }
            },
            'captura_ena': {
                'nome': 'Captura ENA',
                'path': self.base_path / 'Codigos ONS' / 'Captura ENA',
                'graficos': {
                    'comparison_chart': {
                        'padrao': '**/comparison_chart*.png',
                        'descricao': 'Comparação ENA'
                    },
                    'monthly_ranking': {
                        'padrao': '**/monthly_ranking*.png',
                        'descricao': 'Monthly Ranking ENA'
                    }
                }
            },
            'curtailment_empresas': {
                'nome': 'Curtailment - Nível Empresa',
                'path': self.base_path / 'Codigos ONS' / 'Curtailment',
                'graficos': {
                    'h_abs_auren': {
                        'padrao': '**/H_abs_Auren*.png',
                        'descricao': 'Curtailment Absoluto - Auren-AES'
                    },
                    'h_pct_auren': {
                        'padrao': '**/H_pct_Auren*.png',
                        'descricao': 'Curtailment Percentual - Auren-AES'
                    },
                    'abs_auren': {
                        'padrao': '**/abs_Auren*.png',
                        'descricao': 'Curtailment Absoluto - Auren-AES'
                    },
                    'pct_auren': {
                        'padrao': '**/pct_Auren*.png',
                        'descricao': 'Curtailment Percentual - Auren-AES'
                    },
                    'h_abs_comerc': {
                        'padrao': '**/H_abs_Comerc*.png',
                        'descricao': 'Curtailment Absoluto - Comerc'
                    },
                    'h_pct_comerc': {
                        'padrao': '**/H_pct_Comerc*.png',
                        'descricao': 'Curtailment Percentual - Comerc'
                    },
                    'abs_comerc': {
                        'padrao': '**/abs_Comerc*.png',
                        'descricao': 'Curtailment Absoluto - Comerc'
                    },
                    'pct_comerc': {
                        'padrao': '**/pct_Comerc*.png',
                        'descricao': 'Curtailment Percentual - Comerc'
                    },
                    'h_abs_alupar': {
                        'padrao': '**/H_abs_Alupar*.png',
                        'descricao': 'Curtailment Absoluto - Alupar'
                    },
                    'h_pct_alupar': {
                        'padrao': '**/H_pct_Alupar*.png',
                        'descricao': 'Curtailment Percentual - Alupar'
                    },
                    'abs_alupar': {
                        'padrao': '**/abs_Alupar*.png',
                        'descricao': 'Curtailment Absoluto - Alupar'
                    },
                    'pct_alupar': {
                        'padrao': '**/pct_Alupar*.png',
                        'descricao': 'Curtailment Percentual - Alupar'
                    },
                    'h_abs_engie': {
                        'padrao': '**/H_abs_Engie*.png',
                        'descricao': 'Curtailment Absoluto - Engie'
                    },
                    'h_pct_engie': {
                        'padrao': '**/H_pct_Engie*.png',
                        'descricao': 'Curtailment Percentual - Engie'
                    },
                    'abs_engie': {
                        'padrao': '**/abs_Engie*.png',
                        'descricao': 'Curtailment Absoluto - Engie'
                    },
                    'pct_engie': {
                        'padrao': '**/pct_Engie*.png',
                        'descricao': 'Curtailment Percentual - Engie'
                    },
                    'h_abs_neoenergia': {
                        'padrao': '**/H_abs_Neoenergia*.png',
                        'descricao': 'Curtailment Absoluto - Neoenergia'
                    },
                    'h_pct_neoenergia': {
                        'padrao': '**/H_pct_Neoenergia*.png',
                        'descricao': 'Curtailment Percentual - Neoenergia'
                    },
                    'abs_neoenergia': {
                        'padrao': '**/abs_Neoenergia*.png',
                        'descricao': 'Curtailment Absoluto - Neoenergia'
                    },
                    'pct_neoenergia': {
                        'padrao': '**/pct_Neoenergia*.png',
                        'descricao': 'Curtailment Percentual - Neoenergia'
                    },
                    'h_abs_cpfl': {
                        'padrao': '**/H_abs_CPFL*.png',
                        'descricao': 'Curtailment Absoluto - CPFL'
                    },
                    'h_pct_cpfl': {
                        'padrao': '**/H_pct_CPFL*.png',
                        'descricao': 'Curtailment Percentual - CPFL'
                    },
                    'abs_cpfl': {
                        'padrao': '**/abs_CPFL*.png',
                        'descricao': 'Curtailment Absoluto - CPFL'
                    },
                    'pct_cpfl': {
                        'padrao': '**/pct_CPFL*.png',
                        'descricao': 'Curtailment Percentual - CPFL'
                    },
                    'h_abs_eqtl': {
                        'padrao': '**/H_abs_EQTL*.png',
                        'descricao': 'Curtailment Absoluto - EQTL'
                    },
                    'h_pct_eqtl': {
                        'padrao': '**/H_pct_EQTL*.png',
                        'descricao': 'Curtailment Percentual - EQTL'
                    },
                    'abs_eqtl': {
                        'padrao': '**/abs_EQTL*.png',
                        'descricao': 'Curtailment Absoluto - EQTL'
                    },
                    'pct_eqtl': {
                        'padrao': '**/pct_EQTL*.png',
                        'descricao': 'Curtailment Percentual - EQTL'
                    },
                    'h_abs_copel': {
                        'padrao': '**/H_abs_Copel*.png',
                        'descricao': 'Curtailment Absoluto - Copel'
                    },
                    'h_pct_copel': {
                        'padrao': '**/H_pct_Copel*.png',
                        'descricao': 'Curtailment Percentual - Copel'
                    },
                    'abs_copel': {
                        'padrao': '**/abs_Copel*.png',
                        'descricao': 'Curtailment Absoluto - Copel'
                    },
                    'pct_copel': {
                        'padrao': '**/pct_Copel*.png',
                        'descricao': 'Curtailment Percentual - Copel'
                    },
                    'h_abs_serena': {
                        'padrao': '**/H_abs_Serena*.png',
                        'descricao': 'Curtailment Absoluto - Serena'
                    },
                    'h_pct_serena': {
                        'padrao': '**/H_pct_Serena*.png',
                        'descricao': 'Curtailment Percentual - Serena'
                    },
                    'abs_serena': {
                        'padrao': '**/abs_Serena*.png',
                        'descricao': 'Curtailment Absoluto - Serena'
                    },
                    'pct_serena': {
                        'padrao': '**/pct_Serena*.png',
                        'descricao': 'Curtailment Percentual - Serena'
                    }
                }
            },
            'geracao_usina': {
                'nome': 'Geração por Usina',
                'path': self.base_path / 'Codigos ONS' / 'Geracao por usina',
                'graficos': {
                    'merit_order_historical': {
                        'padrao': '**/merit_order_historical*.png',
                        'descricao': 'Comparação Histórica Curva de Mérito'
                    },
                    'merit_order_curve': {
                        'padrao': '**/merit_order_curve*.png',
                        'descricao': 'Curva de Mérito Atual'
                    },
                    'monthly_pattern': {
                        'padrao': '**/monthly_pattern*.png',
                        'descricao': 'Padrão Mensal CVU'
                    },
                    'top_usinas_cvu': {
                        'padrao': '**/top_usinas_cvu*.png',
                        'descricao': 'Top Usinas por CVU'
                    },
                    'cvu_by_year': {
                        'padrao': '**/cvu_by_year*.png',
                        'descricao': 'CVU por Ano'
                    }
                }
            },
            'commodities_bbg': {
                'nome': 'Commodities Bloomberg',
                'path': self.base_path / 'Codigos Agro' / 'Commodities BBG' / 'output' / 'charts',
                'graficos': {
                    'basis_charts': {
                        'padrao': 'basis_*.png',
                        'descricao': 'Gráficos de Basis'
                    },
                    'curva_precos': {
                        'padrao': 'curva_precos_*.png',
                        'descricao': 'Curvas de Preços'
                    }
                }
            },
            'frete_vidal': {
                'nome': 'Frete Vidal',
                'path': self.base_path / 'Codigos Agro' / 'Frete Vidal' / 'output',
                'graficos': {
                    'frete_principal': {
                        'padrao': '*.png',
                        'descricao': 'Gráficos de Frete Principal'
                    },
                    'ajustado_diesel': {
                        'padrao': 'ajustado_diesel/*.png',
                        'descricao': 'Frete Ajustado Diesel'
                    },
                    'custo_escoamento': {
                        'padrao': 'custo_escoamento/*.png',
                        'descricao': 'Custo de Escoamento'
                    }
                }
            },
            'secex': {
                'nome': 'SECEX - Exportação',
                'path': self.base_path / 'Codigos Agro' / 'SECEX' / 'output' / 'charts',
                'graficos': {
                    'exportacao_grains': {
                        'padrao': 'grains_export*.png',
                        'descricao': 'Exportação de Grãos'
                    },
                    'medias_diarias': {
                        'padrao': 'medias_diarias*.png',
                        'descricao': 'Médias Diárias'
                    },
                    'medias_diarias_proteinas': {
                        'padrao': 'medias_diarias_proteinas*.png',
                        'descricao': 'Médias Diárias Proteínas'
                    },
                    'mom_exportacao': {
                        'padrao': 'MoM_Exporta*.png',
                        'descricao': 'Exportação MoM'
                    }
                }
            }
        }
    
    def _configurar_logging(self):
        """Configura sistema de logging."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "gerador_relatorios.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def encontrar_graficos(self, projeto_key):
        """Encontra gráficos de um projeto específico."""
        projeto = self.projetos[projeto_key]
        graficos_encontrados = {}
        
        self.logger.info(f"Procurando gráficos em: {projeto['path']}")
        
        for grafico_key, config in projeto['graficos'].items():
            # Usar glob.glob para padrões mais complexos
            import glob
            padrao_completo = str(projeto['path'] / config['padrao'])
            arquivos = glob.glob(padrao_completo, recursive=True)
            arquivos = [Path(arquivo) for arquivo in arquivos]
            
            if arquivos:
                # Para carga líquida e rotinas Agro, pegar todos os arquivos que correspondem ao padrão
                if projeto_key in ['carga_liquida', 'commodities_bbg', 'frete_vidal', 'secex']:
                    for arquivo in arquivos:
                        # Criar chave única baseada no nome do arquivo
                        chave_unica = f"{grafico_key}_{arquivo.stem}"
                        graficos_encontrados[chave_unica] = {
                            'path': arquivo,
                            'descricao': config['descricao'],
                            'nome_arquivo': arquivo.name
                        }
                        self.logger.info(f"  ✓ {chave_unica}: {arquivo.name}")
                else:
                    # Para outros projetos, pegar o arquivo mais recente
                    arquivo_mais_recente = max(arquivos, key=os.path.getctime)
                    graficos_encontrados[grafico_key] = {
                        'path': arquivo_mais_recente,
                        'descricao': config['descricao'],
                        'nome_arquivo': arquivo_mais_recente.name
                    }
                    self.logger.info(f"  ✓ {grafico_key}: {arquivo_mais_recente.name}")
            else:
                self.logger.warning(f"  ✗ {grafico_key}: Nenhum arquivo encontrado com padrão {config['padrao']}")
        
        # Ordenar gráficos conforme requisitos específicos
        if projeto_key == 'curtailment_brasil':
            # Ordenar: h_abs_brasil, h_pct_brasil primeiro (fileira de cima)
            graficos_ordenados = {}
            ordem_prioritaria = ['h_abs_brasil', 'h_pct_brasil']
            for key in ordem_prioritaria:
                if key in graficos_encontrados:
                    graficos_ordenados[key] = graficos_encontrados[key]
            for key, value in graficos_encontrados.items():
                if key not in ordem_prioritaria:
                    graficos_ordenados[key] = value
            graficos_encontrados = graficos_ordenados
        
        elif projeto_key == 'precos_energia':
            # Ordenar: pld_se, price_se primeiro (fileira de cima)
            graficos_ordenados = {}
            ordem_prioritaria = ['pld_se', 'price_se']
            for key in ordem_prioritaria:
                if key in graficos_encontrados:
                    graficos_ordenados[key] = graficos_encontrados[key]
            for key, value in graficos_encontrados.items():
                if key not in ordem_prioritaria:
                    graficos_ordenados[key] = value
            graficos_encontrados = graficos_ordenados
        
        return graficos_encontrados
    
    def gerar_relatorio_completo(self):
        """Gera relatório completo com todas as rotinas na ordem especificada."""
        self.logger.info("Iniciando geração do relatório completo ONS")
        
        # Ordem das seções conforme especificado
        ordem_secoes = [
            'carga',
            'carga_liquida', 
            'curtailment_brasil',
            'precos_energia',
            'captura_ena',
            'curtailment_empresas',
            'geracao_usina',
            'commodities_bbg',
            'frete_vidal',
            'secex'
        ]
        
        # Coletar gráficos de todas as seções
        todas_secoes = {}
        for secao in ordem_secoes:
            graficos = self.encontrar_graficos(secao)
            if graficos:
                todas_secoes[secao] = graficos
        
        if not todas_secoes:
            self.logger.error("Nenhum gráfico encontrado para gerar relatório")
            return False
        
        # Criar PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = self.output_path / f"relatorio_completo_ons_{timestamp}.pdf"
        
        with PdfPages(pdf_path) as pdf:
            # Página 1: Cabeçalho
            self._criar_pagina_cabecalho(pdf, "Relatório Completo ONS")
            
            # Páginas das seções na ordem especificada
            for secao in ordem_secoes:
                if secao in todas_secoes:
                    if secao == 'carga_liquida':
                        self._criar_paginas_carga_liquida(pdf, todas_secoes[secao])
                    elif secao == 'curtailment_empresas':
                        self._criar_paginas_curtailment_empresas(pdf, todas_secoes[secao])
                    elif secao == 'commodities_bbg':
                        self._criar_paginas_commodities_bbg(pdf, todas_secoes[secao])
                    elif secao == 'frete_vidal':
                        self._criar_paginas_frete_vidal(pdf, todas_secoes[secao])
                    elif secao == 'secex':
                        self._criar_paginas_secex(pdf, todas_secoes[secao])
                    elif secao == 'captura_ena':
                        self._criar_paginas_captura_ena(pdf, todas_secoes[secao])
                    else:
                        self._criar_pagina_secao(pdf, self.projetos[secao]['nome'], todas_secoes[secao])
        
        self.logger.info(f"Relatório completo gerado com sucesso: {pdf_path}")
        return str(pdf_path)
    
    def _criar_paginas_carga_liquida(self, pdf, graficos):
        """Cria páginas específicas para carga líquida conforme requisitos."""
        # Separar gráficos por tipo
        componentes_geracao = {}
        graficos_diarios = {}
        grafico_soma = {}
        
        for key, info in graficos.items():
            if 'componentes_geracao' in key:
                componentes_geracao[key] = info
            elif 'grafico_2025-' in info['nome_arquivo']:
                graficos_diarios[key] = info
            elif 'grafico_soma_valores' in key:
                grafico_soma[key] = info
        
        # Página 1: Componentes de Geração
        if componentes_geracao:
            self._criar_pagina_secao(pdf, "Análise de Carga Líquida - Componentes de Geração", componentes_geracao)
        
        # Página 2: Gráficos Diários
        if graficos_diarios:
            self._criar_pagina_secao(pdf, "Análise de Carga Líquida - Gráficos Diários", graficos_diarios)
        
        # Página 3: Soma de Valores
        if grafico_soma:
            self._criar_pagina_secao(pdf, "Análise de Carga Líquida - Soma de Valores", grafico_soma)
    
    def _criar_paginas_captura_ena(self, pdf, graficos):
        """Cria páginas específicas para Captura ENA conforme requisitos."""
        # Separar gráficos por tipo
        monthly_rankings = {}
        comparison_chart = {}
        
        for key, info in graficos.items():
            if 'monthly_ranking' in key:
                monthly_rankings[key] = info
            elif 'comparison_chart' in key:
                comparison_chart[key] = info
        
        # Página 1: Monthly Rankings (ambos na mesma página)
        if monthly_rankings:
            self._criar_pagina_secao(pdf, "Captura ENA - Monthly Rankings", monthly_rankings)
        
        # Página 2: Comparação ENA
        if comparison_chart:
            self._criar_pagina_secao(pdf, "Captura ENA - Comparação ENA", comparison_chart)
    
    def _criar_paginas_curtailment_empresas(self, pdf, graficos):
        """Cria uma página por empresa para curtailment."""
        # Agrupar gráficos por empresa
        empresas = {}
        
        for key, info in graficos.items():
            # Extrair nome da empresa do nome do arquivo
            nome_arquivo = info['nome_arquivo']
            if 'Auren' in nome_arquivo:
                empresa = 'Auren-AES'
            elif 'Comerc' in nome_arquivo:
                empresa = 'Comerc'
            elif 'Alupar' in nome_arquivo:
                empresa = 'Alupar'
            elif 'Engie' in nome_arquivo:
                empresa = 'Engie'
            elif 'Neoenergia' in nome_arquivo:
                empresa = 'Neoenergia'
            elif 'CPFL' in nome_arquivo:
                empresa = 'CPFL'
            elif 'EQTL' in nome_arquivo:
                empresa = 'EQTL'
            elif 'Copel' in nome_arquivo:
                empresa = 'Copel'
            elif 'Serena' in nome_arquivo:
                empresa = 'Serena'
            else:
                empresa = 'Outras'
            
            if empresa not in empresas:
                empresas[empresa] = {}
            empresas[empresa][key] = info
        
        # Criar uma página por empresa
        for empresa, graficos_empresa in empresas.items():
            if graficos_empresa:  # Só criar página se houver gráficos
                # Ordenar gráficos: H_abs e H_pct primeiro (fileira de cima)
                graficos_ordenados = {}
                ordem_prioritaria = []
                
                # Identificar gráficos mensais (H_abs e H_pct) para esta empresa
                for key in graficos_empresa.keys():
                    if key.startswith('h_abs_') or key.startswith('h_pct_'):
                        ordem_prioritaria.append(key)
                
                # Adicionar gráficos mensais primeiro
                for key in ordem_prioritaria:
                    if key in graficos_empresa:
                        graficos_ordenados[key] = graficos_empresa[key]
                
                # Adicionar os demais gráficos
                for key, value in graficos_empresa.items():
                    if key not in ordem_prioritaria:
                        graficos_ordenados[key] = value
                
                self._criar_pagina_secao(pdf, f"Curtailment - {empresa}", graficos_ordenados)
    
    def _criar_paginas_commodities_bbg(self, pdf, graficos):
        """Cria páginas específicas para Commodities BBG conforme requisitos."""
        # Separar gráficos por tipo
        curva_precos = {}
        basis_paranagua = {}
        basis_sorriso = {}
        outros_graficos = {}
        
        for key, info in graficos.items():
            nome_arquivo = info['nome_arquivo']
            if 'curva_precos' in key:
                curva_precos[key] = info
            elif 'basis_soja_paranagua' in key or 'basis_milho_paranagua' in key:
                if 'sorriso' in key:
                    basis_sorriso[key] = info
                else:
                    basis_paranagua[key] = info
            else:
                outros_graficos[key] = info
        
        # Página 1: Curvas de Preços
        if curva_precos:
            self._criar_pagina_secao(pdf, "Commodities BBG - Curvas de Preços", curva_precos)
        
        # Página 2: Basis Paranaguá
        if basis_paranagua:
            self._criar_pagina_secao(pdf, "Commodities BBG - Basis Paranaguá", basis_paranagua)
        
        # Página 3: Basis Sorriso
        if basis_sorriso:
            self._criar_pagina_secao(pdf, "Commodities BBG - Basis Sorriso", basis_sorriso)
        
        # Página 4: Outros gráficos
        if outros_graficos:
            self._criar_pagina_secao(pdf, "Commodities BBG - Outros Gráficos", outros_graficos)
    
    def _criar_paginas_frete_vidal(self, pdf, graficos):
        """Cria páginas específicas para Frete Vidal conforme requisitos."""
        # Separar gráficos por tipo
        frete_principal = {}
        ajustado_diesel = {}
        custo_escoamento = {}
        outros_graficos = {}
        
        for key, info in graficos.items():
            if 'ajustado_diesel' in key:
                ajustado_diesel[key] = info
            elif 'custo_escoamento' in key:
                custo_escoamento[key] = info
            elif 'frete_principal' in key:
                frete_principal[key] = info
            else:
                outros_graficos[key] = info
        
        # Página 1: Frete Principal
        if frete_principal:
            self._criar_pagina_secao(pdf, "Frete Vidal - Frete Principal", frete_principal)
        
        # Página 2: Ajustado Diesel
        if ajustado_diesel:
            self._criar_pagina_secao(pdf, "Frete Vidal - Ajustado Diesel", ajustado_diesel)
        
        # Página 3: Custo de Escoamento
        if custo_escoamento:
            self._criar_pagina_secao(pdf, "Frete Vidal - Custo de Escoamento", custo_escoamento)
        
        # Página 4: Outros gráficos
        if outros_graficos:
            self._criar_pagina_secao(pdf, "Frete Vidal - Outros Gráficos", outros_graficos)
    
    def _criar_paginas_secex(self, pdf, graficos):
        """Cria páginas específicas para SECEX conforme requisitos."""
        # Separar gráficos por tipo e remover duplicatas
        medias_diarias_agro = {}
        medias_diarias_proteinas = {}
        outros_graficos = {}
        
        # Usar set para evitar duplicatas baseado no nome do arquivo
        arquivos_processados = set()
        
        for key, info in graficos.items():
            nome_arquivo = info['nome_arquivo']
            
            # Pular se já processamos este arquivo
            if nome_arquivo in arquivos_processados:
                continue
            
            arquivos_processados.add(nome_arquivo)
            
            if 'medias_diarias_proteinas' in key:
                medias_diarias_proteinas[key] = info
            elif 'medias_diarias_agro' in key:
                medias_diarias_agro[key] = info
            else:
                outros_graficos[key] = info
        
        # Página 1: Médias Diárias Agro
        if medias_diarias_agro:
            self._criar_pagina_secao(pdf, "SECEX - Médias Diárias Agro", medias_diarias_agro)
        
        # Página 2: Médias Diárias Proteínas
        if medias_diarias_proteinas:
            self._criar_pagina_secao(pdf, "SECEX - Médias Diárias Proteínas", medias_diarias_proteinas)
        
        # Página 3: Outros gráficos
        if outros_graficos:
            self._criar_pagina_secao(pdf, "SECEX - Outros Gráficos", outros_graficos)
    
    def gerar_relatorio_carga_precos(self):
        """Gera relatório combinando gráficos de Carga e Preços de Energia."""
        self.logger.info("Iniciando geração do relatório Carga + Preços de Energia")
        
        # Coletar gráficos
        graficos_carga = self.encontrar_graficos('carga')
        graficos_precos = self.encontrar_graficos('precos_energia')
        
        if not graficos_carga and not graficos_precos:
            self.logger.error("Nenhum gráfico encontrado para gerar relatório")
            return False
        
        # Criar PDF
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_path = self.output_path / f"relatorio_carga_precos_{timestamp}.pdf"
        
        with PdfPages(pdf_path) as pdf:
            # Página 1: Cabeçalho
            self._criar_pagina_cabecalho(pdf, "Relatório de Carga e Preços de Energia")
            
            # Página 2: Seção Carga (2 colunas)
            if graficos_carga:
                self._criar_pagina_secao(pdf, "Análise de Carga Energética", graficos_carga)
            
            # Página 3: Seção Preços (2 colunas)
            if graficos_precos:
                self._criar_pagina_secao(pdf, "Sistema de Preços de Energia BR", graficos_precos)
        
        self.logger.info(f"Relatório gerado com sucesso: {pdf_path}")
        return str(pdf_path)
    
    def _criar_pagina_cabecalho(self, pdf, titulo):
        """Cria página de cabeçalho do relatório."""
        fig, ax = plt.subplots(figsize=(11.69, 8.27))  # A4
        ax.axis('off')
        
        # Título principal
        ax.text(0.5, 0.8, titulo, 
                fontsize=24, fontweight='bold', ha='center', va='center',
                transform=ax.transAxes)
        
        # Data de geração
        data_geracao = datetime.now().strftime("%d/%m/%Y às %H:%M")
        ax.text(0.5, 0.7, f"Gerado em: {data_geracao}",
                fontsize=14, ha='center', va='center',
                transform=ax.transAxes)
        
        # Informações do sistema
        ax.text(0.5, 0.6, "Orquestrador Central ONS",
                fontsize=12, ha='center', va='center',
                transform=ax.transAxes)
        
        # Seções incluídas
        ax.text(0.5, 0.5, "Seções incluídas:",
                fontsize=14, fontweight='bold', ha='center', va='center',
                transform=ax.transAxes)
        
        # Lista de seções (ajustar posição baseado no título)
        secoes_lista = [
            "• Análise de Carga Energética",
            "• Análise de Carga Líquida", 
            "• Curtailment - Nível Brasil",
            "• Sistema de Preços de Energia BR",
            "• Captura ENA",
            "• Curtailment - Nível Empresa",
            "• Geração por Usina",
            "• Commodities Bloomberg",
            "• Frete Vidal",
            "• SECEX - Exportação"
        ]
        
        # Posicionar lista de seções
        y_pos = 0.4
        for i, secao in enumerate(secoes_lista):
            if i < 4:  # Primeiras 4 seções
                ax.text(0.5, y_pos, secao,
                       fontsize=11, ha='center', va='center',
                       transform=ax.transAxes)
                y_pos -= 0.05
            else:  # Restantes seções em coluna 2
                ax.text(0.5, y_pos, secao,
                       fontsize=11, ha='center', va='center',
                       transform=ax.transAxes)
                y_pos -= 0.05
        
        pdf.savefig(fig, bbox_inches='tight', dpi=300)
        plt.close()
    
    def _criar_pagina_secao(self, pdf, titulo_secao, graficos):
        """Cria página com gráficos de uma seção específica."""
        if not graficos:
            return
        
        # Calcular layout baseado no número de gráficos
        num_graficos = len(graficos)
        
        # Dividir gráficos em páginas de no máximo 4
        graficos_list = list(graficos.items())
        for pagina in range(0, len(graficos_list), 4):
            graficos_pagina = graficos_list[pagina:pagina + 4]
            num_graficos_pagina = len(graficos_pagina)
            
            # Criar figura com tamanho fixo A4
            fig = plt.figure(figsize=(11.69, 8.27))  # A4 - todas as páginas do mesmo tamanho
            
            # Título da seção
            if len(graficos_list) > 4:
                fig.suptitle(f"{titulo_secao} (Página {pagina//4 + 1})", fontsize=18, fontweight='bold', y=0.95)
            else:
                fig.suptitle(titulo_secao, fontsize=18, fontweight='bold', y=0.95)
            
            # Layout baseado no número de gráficos na página
            if num_graficos_pagina == 1:
                # Um gráfico ocupa toda a página
                ax = plt.subplot(1, 1, 1)
                ax.set_position([0.05, 0.1, 0.9, 0.8])  # Margens para centralizar
                
                try:
                    # Carregar e exibir imagem
                    grafico_info = graficos_pagina[0][1]
                    img = mpimg.imread(grafico_info['path'])
                    ax.imshow(img)
                    ax.axis('off')
                    
                    # Título do gráfico
                    ax.set_title(grafico_info['descricao'], fontsize=12, pad=20)
                    
                except Exception as e:
                    self.logger.error(f"Erro ao carregar gráfico {grafico_info['path']}: {e}")
                    ax.text(0.5, 0.5, f"Erro ao carregar:\n{grafico_info['nome_arquivo']}",
                           ha='center', va='center', transform=ax.transAxes,
                           fontsize=10, color='red')
                    ax.axis('off')
            
            elif num_graficos_pagina == 2:
                # Dois gráficos lado a lado
                for i, (grafico_key, grafico_info) in enumerate(graficos_pagina):
                    ax = plt.subplot(1, 2, i + 1)
                    
                    try:
                        # Carregar e exibir imagem
                        img = mpimg.imread(grafico_info['path'])
                        ax.imshow(img)
                        ax.axis('off')
                        
                        # Título do gráfico
                        ax.set_title(grafico_info['descricao'], fontsize=10, pad=10)
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao carregar gráfico {grafico_info['path']}: {e}")
                        ax.text(0.5, 0.5, f"Erro ao carregar:\n{grafico_info['nome_arquivo']}",
                               ha='center', va='center', transform=ax.transAxes,
                               fontsize=10, color='red')
                        ax.axis('off')
            
            elif num_graficos_pagina == 3:
                # Três gráficos: 2 em cima, 1 embaixo centralizado
                for i, (grafico_key, grafico_info) in enumerate(graficos_pagina):
                    if i < 2:
                        # Primeiros dois gráficos em cima
                        ax = plt.subplot(2, 2, i + 1)
                    else:
                        # Terceiro gráfico embaixo centralizado
                        ax = plt.subplot(2, 2, (3, 4))
                    
                    try:
                        # Carregar e exibir imagem
                        img = mpimg.imread(grafico_info['path'])
                        ax.imshow(img)
                        ax.axis('off')
                        
                        # Título do gráfico
                        ax.set_title(grafico_info['descricao'], fontsize=10, pad=10)
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao carregar gráfico {grafico_info['path']}: {e}")
                        ax.text(0.5, 0.5, f"Erro ao carregar:\n{grafico_info['nome_arquivo']}",
                               ha='center', va='center', transform=ax.transAxes,
                               fontsize=10, color='red')
                        ax.axis('off')
            
            else:  # 4 gráficos
                # Quatro gráficos em grade 2x2
                for i, (grafico_key, grafico_info) in enumerate(graficos_pagina):
                    ax = plt.subplot(2, 2, i + 1)
                    
                    try:
                        # Carregar e exibir imagem
                        img = mpimg.imread(grafico_info['path'])
                        ax.imshow(img)
                        ax.axis('off')
                        
                        # Título do gráfico
                        ax.set_title(grafico_info['descricao'], fontsize=10, pad=10)
                        
                    except Exception as e:
                        self.logger.error(f"Erro ao carregar gráfico {grafico_info['path']}: {e}")
                        ax.text(0.5, 0.5, f"Erro ao carregar:\n{grafico_info['nome_arquivo']}",
                               ha='center', va='center', transform=ax.transAxes,
                               fontsize=10, color='red')
                        ax.axis('off')
            
            # Ajustar layout para centralizar e distribuir
            plt.tight_layout(pad=2.0)
            pdf.savefig(fig, bbox_inches='tight', dpi=300)
            plt.close()
    
    def listar_graficos_disponiveis(self):
        """Lista todos os gráficos disponíveis em todos os projetos."""
        self.logger.info("Listando gráficos disponíveis:")
        
        for projeto_key, projeto in self.projetos.items():
            self.logger.info(f"\n=== {projeto['nome']} ===")
            graficos = self.encontrar_graficos(projeto_key)
            
            if graficos:
                for grafico_key, info in graficos.items():
                    self.logger.info(f"  {grafico_key}: {info['nome_arquivo']}")
            else:
                self.logger.info("  Nenhum gráfico encontrado")


def main():
    """Função principal."""
    gerador = GeradorRelatorios()
    
    # Listar gráficos disponíveis
    gerador.listar_graficos_disponiveis()
    
    # Gerar relatório completo
    print("\n" + "="*60)
    print("GERANDO RELATÓRIO COMPLETO ONS")
    print("="*60)
    
    pdf_path = gerador.gerar_relatorio_completo()
    
    if pdf_path:
        print(f"\n✅ Relatório completo gerado com sucesso!")
        print(f"📄 Arquivo: {pdf_path}")
        print(f"📁 Pasta: {gerador.output_path}")
    else:
        print("\n❌ Erro ao gerar relatório")


if __name__ == "__main__":
    main()
