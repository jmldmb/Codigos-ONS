#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ORQUESTRADOR - PREÇOS DE ENERGIA BR
===================================

Versão robusta do orquestrador para gerar gráficos e relatórios.
Baseado no notebook orchestrator.ipynb.
"""

import sys
import logging
from pathlib import Path
import datetime as dt
import pandas as pd
import yaml
import importlib
from jinja2 import Environment, FileSystemLoader
import matplotlib.pyplot as plt

# Configurar logging com encoding UTF-8
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('orchestrator.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class OrquestradorPrecos:
    """Orquestrador para geração de gráficos e relatórios de preços."""
    
    def __init__(self):
        """Inicializa o orquestrador."""
        self.setup_paths()
        self.setup_imports()
        self.load_config()
        
    def setup_paths(self):
        """Configura os caminhos do projeto."""
        try:
            # Detectar diretório base
            if hasattr(sys, '_getframe'):
                # Script Python
                BASE = Path(__file__).resolve().parent
            else:
                # Notebook/Interativo
                BASE = Path.cwd()
            
            # Verificar se estamos no diretório correto
            if BASE.name != "Scripts":
                # Procurar pelo diretório Scripts
                for parent in BASE.parents:
                    scripts_dir = parent / "Scripts"
                    if scripts_dir.exists():
                        BASE = scripts_dir
                        break
            
            self.BASE = BASE
            self.ROOT = BASE.parent
            self.TODAY = dt.date.today().isoformat()
            
            # Adicionar ao path se necessário
            if str(BASE) not in sys.path:
                sys.path.append(str(BASE))
            
            logger.info(f"BASE: {self.BASE}")
            logger.info(f"ROOT: {self.ROOT}")
            
        except Exception as e:
            logger.error(f"Erro ao configurar caminhos: {e}")
            raise
    
    def setup_imports(self):
        """Configura as importações dos módulos."""
        try:
            # Importar módulos
            from data_ingest import update_all
            import plot_utils
            
            # Recarregar módulos se necessário
            importlib.reload(plot_utils)
            
            # Atalhos para funções
            self.update_all = update_all
            self.plot_price = plot_utils.plot_price
            self.plot_spread = plot_utils.plot_spread
            self.plot_price_daily = plot_utils.plot_price_daily
            self.plot_spread_daily = plot_utils.plot_spread_daily
            self.plot_spread_armazenamento_diario = plot_utils.plot_spread_armazenamento_diario
            
            logger.info("Modulos importados com sucesso")
            
        except ImportError as e:
            logger.error(f"Erro ao importar modulos: {e}")
            raise
    
    def load_config(self):
        """Carrega a configuração do arquivo YAML."""
        try:
            config_path = self.BASE / "config.yaml"
            if not config_path.exists():
                logger.error(f"Arquivo de configuracao nao encontrado: {config_path}")
                raise FileNotFoundError(f"Configuração não encontrada: {config_path}")
            
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            
            logger.info("Configuracao carregada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao carregar configuracao: {e}")
            raise
    
    def resolve_date(self, token):
        """Resolve tokens de data para objetos date."""
        try:
            today = dt.date.today()
            
            if token == "today":
                return today
            elif token.startswith("today-") and token.endswith("d"):
                n = int(token.split("-")[1][:-1])
                return today - dt.timedelta(days=n)
            else:
                return dt.datetime.strptime(token, "%Y-%m-%d").date()
                
        except Exception as e:
            logger.error(f"Erro ao resolver data '{token}': {e}")
            raise
    
    def check_parquet_dependencies(self):
        """Verifica se as dependências para parquet estão instaladas."""
        try:
            import pyarrow
            logger.info("pyarrow disponivel")
            return True
        except ImportError:
            try:
                import fastparquet
                logger.info("fastparquet disponivel")
                return True
            except ImportError:
                logger.error("Nenhuma dependencia para parquet encontrada")
                logger.error("Instale: pip install pyarrow ou pip install fastparquet")
                return False
    
    def update_data(self):
        """Atualiza os dados."""
        try:
            logger.info("Atualizando dados...")
            self.update_all()
            logger.info("Dados atualizados com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao atualizar dados: {e}")
            raise
    
    def load_data(self):
        """Carrega os dados processados."""
        try:
            # Verificar dependências primeiro
            if not self.check_parquet_dependencies():
                raise ImportError("Dependencias para parquet nao encontradas")
            
            parq_path = self.ROOT / "Data" / "processed" / "pld" / "base_master.parquet"
            
            if not parq_path.exists():
                logger.error(f"Arquivo de dados nao encontrado: {parq_path}")
                raise FileNotFoundError(f"Dados não encontrados: {parq_path}")
            
            self.df_pld = pd.read_parquet(parq_path)
            logger.info(f"Dados carregados: {len(self.df_pld)} registros")
            
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}")
            raise
    
    def setup_output_dirs(self):
        """Configura os diretórios de saída."""
        try:
            # Diretório de gráficos
            self.CHART_DIR = self.ROOT / "charts" / self.TODAY
            self.CHART_DIR.mkdir(parents=True, exist_ok=True)
            
            # Diretório de relatórios
            self.REP_DIR = self.ROOT / "report_out"
            self.REP_DIR.mkdir(exist_ok=True)
            
            logger.info(f"Diretorios configurados: {self.CHART_DIR}")
            
        except Exception as e:
            logger.error(f"Erro ao configurar diretorios: {e}")
            raise
    
    def generate_charts(self):
        """Gera os gráficos conforme configuração."""
        generated = []
        
        try:
            charts_config = self.config.get("charts", [])
            logger.info(f"Gerando {len(charts_config)} graficos...")
            
            for item in charts_config:
                try:
                    # Resolver datas
                    start = self.resolve_date(item["start"])
                    end = self.resolve_date(item["end"])
                    name = item["name"]
                    kind = item["kind"]
                    target_sub = item["target_sub"]
                    
                    # Caminho do arquivo
                    png_path = self.CHART_DIR / f"{name}.png"
                    
                    logger.info(f"Gerando {name} ({kind})...")
                    
                    # Gerar gráfico baseado no tipo
                    if kind == "price_daily":
                        fig = self.plot_price_daily(
                            self.df_pld,
                            target_sub=target_sub,
                            start=start, end=end,
                            ma_days=item.get("ma")
                        )
                    elif kind == "spread_daily":
                        fig = self.plot_spread_daily(
                            self.df_pld,
                            target_sub=target_sub,
                            start=start, end=end,
                            ma_days=item.get("ma")
                        )
                    elif kind == "price":
                        fig = self.plot_price(
                            self.df_pld,
                            target_sub=target_sub,
                            start=start, end=end
                        )
                    elif kind == "spread_armazenamento_diario":
                        fig = self.plot_spread_armazenamento_diario(
                            self.df_pld,
                            target_sub=target_sub,
                            start=start, end=end,
                            spread_ma_days=item.get("ma")
                        )
                    else:
                        logger.warning(f"Tipo desconhecido: {kind}")
                        continue
                    
                    # Salvar gráfico
                    fig.savefig(png_path, dpi=150, bbox_inches="tight")
                    plt.close(fig)
                    
                    generated.append({
                        "title": name.replace("_", " ").upper(),
                        "path": png_path
                    })
                    
                    logger.info(f"{png_path.name}")
                    
                except Exception as e:
                    logger.error(f"Erro ao gerar grafico {name}: {e}")
                    continue
            
            logger.info(f"{len(generated)} graficos gerados com sucesso")
            return generated
            
        except Exception as e:
            logger.error(f"Erro ao gerar graficos: {e}")
            raise
    
    def generate_report(self, generated_charts):
        """Gera o relatório HTML."""
        try:
            logger.info("Gerando relatorio HTML...")
            
            # Configurar template
            templates_dir = self.ROOT / "templates"
            if not templates_dir.exists():
                logger.error(f"Diretorio de templates nao encontrado: {templates_dir}")
                raise FileNotFoundError(f"Templates não encontrados: {templates_dir}")
            
            env = Environment(loader=FileSystemLoader(templates_dir))
            template = env.get_template("report.html.jinja")
            
            # Renderizar template
            html_content = template.render(
                date=self.TODAY,
                images=generated_charts
            )
            
            # Salvar relatório
            html_path = self.REP_DIR / f"{self.TODAY}_report.html"
            html_path.write_text(html_content, encoding='utf-8')
            
            logger.info(f"Relatorio salvo: {html_path}")
            return html_path
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatorio: {e}")
            raise
    
    def run(self):
        """Executa o orquestrador completo."""
        try:
            logger.info("Iniciando orquestrador...")
            
            # 1. Atualizar dados
            self.update_data()
            
            # 2. Carregar dados
            self.load_data()
            
            # 3. Configurar diretórios
            self.setup_output_dirs()
            
            # 4. Gerar gráficos
            generated_charts = self.generate_charts()
            
            # 5. Gerar relatório
            if generated_charts:
                report_path = self.generate_report(generated_charts)
                logger.info(f"Processo concluido! Relatorio: {report_path}")
            else:
                logger.warning("Nenhum grafico foi gerado")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro no orquestrador: {e}")
            return False

def main():
    """Função principal."""
    try:
        orchestrator = OrquestradorPrecos()
        success = orchestrator.run()
        
        if success:
            print("Orquestrador executado com sucesso!")
            return 0
        else:
            print("Erro na execucao do orquestrador")
            return 1
            
    except Exception as e:
        print(f"Erro critico: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 