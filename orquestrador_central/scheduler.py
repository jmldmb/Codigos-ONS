#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ORQUESTRADOR CENTRAL
====================

Sistema de agendamento para execução automática dos orquestradores.
"""

import schedule
import time
import logging
from pathlib import Path
import yaml
from datetime import datetime
import subprocess
import sys
import threading

class OrquestradorCentral:
    def __init__(self):
        self.config = self._carregar_config()
        self._configurar_logging()
        self.runners = self._inicializar_runners()
        self.running = False
        
    def _carregar_config(self):
        """Carrega configurações de agendamento."""
        config_path = Path(__file__).parent / "config_scheduler.yaml"
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _configurar_logging(self):
        """Configura sistema de logging."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "scheduler.log", encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _inicializar_runners(self):
        """Inicializa os runners para cada projeto."""
        runners = {}
        all_projects = self.get_all_projects()
        for projeto in all_projects:
            if projeto.get('script_type') == 'legacy':
                runner_path = Path(__file__).parent / "runners" / projeto['runner_path']
                if runner_path.exists():
                    runners[projeto['nome']] = runner_path
        return runners
    
    def get_all_projects(self):
        """Retorna todos os projetos de todas as seções."""
        all_projects = []
        if 'secoes' in self.config:
            for secao_key, secao in self.config['secoes'].items():
                for projeto in secao['projetos']:
                    projeto['secao'] = secao_key
                    projeto['secao_nome'] = secao['nome']
                    all_projects.append(projeto)
        elif 'projetos' in self.config:
            # Compatibilidade com estrutura antiga
            for projeto in self.config['projetos']:
                projeto['secao'] = 'ons'
                projeto['secao_nome'] = 'ONS - Operador Nacional do Sistema'
                all_projects.append(projeto)
        return all_projects
    
    def executar_projeto(self, nome_projeto):
        """Executa um projeto específico."""
        try:
            self.logger.info(f"Executando projeto: {nome_projeto}")
            
            # Buscar projeto na configuração usando nova estrutura
            all_projects = self.get_all_projects()
            projeto_config = None
            for projeto in all_projects:
                if projeto['nome'] == nome_projeto:
                    projeto_config = projeto
                    break
            
            if not projeto_config:
                self.logger.error(f"Projeto {nome_projeto} não encontrado na configuração")
                self.logger.error(f"Projetos disponíveis: {[p['nome'] for p in all_projects]}")
                return False
            
            script_type = projeto_config.get('script_type', 'legacy')
            
            # Executar baseado no tipo de script
            if script_type == 'legacy':
                # Sistema antigo usando runners
                runner_path = Path(__file__).parent / "runners" / projeto_config['runner_path']
                if not runner_path.exists():
                    self.logger.error(f"Runner não encontrado: {runner_path}")
                    return False
                
                command = [sys.executable, str(runner_path)]
                working_dir = Path(__file__).parent
                
            elif script_type in ['orchestrator', 'pipeline']:
                # Novos sistemas com modo full
                script_path = Path(__file__).parent / projeto_config['script_path']
                if not script_path.exists():
                    self.logger.error(f"Script não encontrado: {script_path}")
                    return False
                
                command = [sys.executable, str(script_path)]
                
                # Sempre usar modo full para simplificar
                default_mode = projeto_config.get('mode', 'full')
                command.extend(['--mode', default_mode])
                
                # Para projetos que precisam do próprio diretório, mudar o cwd
                if nome_projeto in ['cvu_termicas']:
                    working_dir = script_path.parent
                else:
                    working_dir = Path(__file__).parent
                    
            elif script_type == 'direct':
                # Scripts diretos sem argumentos especiais
                script_path = Path(__file__).parent / projeto_config['script_path']
                if not script_path.exists():
                    self.logger.error(f"Script não encontrado: {script_path}")
                    return False
                
                command = [sys.executable, str(script_path)]
                
                # Para projetos que precisam do próprio diretório, mudar o cwd
                if nome_projeto == 'carga_liquida':
                    working_dir = script_path.parent  # Executar no diretório Scripts
                elif nome_projeto in ['secex', 'commodities_bbg', 'frete_vidal']:
                    working_dir = script_path.parent  # Executar no diretório do projeto Agro
                elif nome_projeto == 'captura_ena':
                    working_dir = script_path.parent  # Executar no diretório do projeto Captura ENA
                else:
                    working_dir = Path(__file__).parent
            
            else:
                self.logger.error(f"Tipo de script não suportado: {script_type}")
                return False
            
            # Executar comando
            self.logger.info(f"Executando: {' '.join(command)}")
            timeout = self.config.get('configuracoes', {}).get('timeout_execucao', 3600)
            
            # Definir variáveis de ambiente para corrigir encoding
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONLEGACYWINDOWSFSENCODING'] = '1'
            
            try:
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout,
                    cwd=working_dir,
                    env=env,
                    encoding='utf-8',
                    errors='replace'  # Substituir caracteres problemáticos
                )
            except UnicodeDecodeError:
                # Fallback para encoding Windows
                result = subprocess.run(
                    command, 
                    capture_output=True, 
                    timeout=timeout,
                    cwd=working_dir,
                    env=env
                )
                # Decodificar manualmente com fallback
                try:
                    stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ""
                    stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ""
                except:
                    stdout = str(result.stdout) if result.stdout else ""
                    stderr = str(result.stderr) if result.stderr else ""
                
                # Criar um objeto similar ao resultado original
                class MockResult:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr
                
                result = MockResult(result.returncode, stdout, stderr)
            
            if result.returncode == 0:
                self.logger.info(f"{nome_projeto} executado com sucesso")
                if result.stdout:
                    self.logger.info(f"Output: {result.stdout}")
                return True
            else:
                self.logger.error(f"Erro em {nome_projeto}: returncode={result.returncode}")
                if result.stderr:
                    self.logger.error(f"Stderr: {result.stderr}")
                if result.stdout:
                    self.logger.error(f"Stdout: {result.stdout}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout ao executar {nome_projeto}")
            return False
        except Exception as e:
            self.logger.error(f"Erro ao executar {nome_projeto}: {e}")
            return False
    
    def configurar_agendamentos(self):
        """Configura agendamentos (DESABILITADO - modo apenas manual)."""
        self.logger.info("Agendamentos automáticos desabilitados. Utilizando apenas modo manual.")
        # Agendamentos automáticos removidos conforme solicitação
        # Apenas execução manual disponível
    
    def executar_manual(self, nome_projeto):
        """Execução manual de um projeto."""
        self.logger.info(f"Execução manual: {nome_projeto}")
        
        # Comandos especiais
        if nome_projeto == 'gerar_relatorio':
            return self.gerar_relatorio()
        elif nome_projeto == 'rotina_completa':
            return self.executar_rotina_completa()
        else:
            # Execução normal de projeto
            return self.executar_projeto(nome_projeto)
    
    def iniciar_scheduler(self):
        """Inicia o orquestrador (modo apenas manual)."""
        self.logger.info("Iniciando Orquestrador Central")
        self.configurar_agendamentos()
        
        print("=" * 60)
        print("ORQUESTRADOR CENTRAL ATIVO - MODO MANUAL")
        print("=" * 60)
        print("Agendamentos automáticos: DESABILITADOS")
        print("Use a interface web para execuções manuais")
        print("=" * 60)
        print("Pressione Ctrl+C para parar")
        print("=" * 60)
        
        self.running = True
        try:
            while self.running:
                # Remover schedule.run_pending() pois não há agendamentos
                time.sleep(10)  # Manter o servidor rodando
                
        except KeyboardInterrupt:
            self.logger.info("Orquestrador Central interrompido pelo usuário")
            print("\nOrquestrador Central parado")
            self.running = False
    
    def parar_scheduler(self):
        """Para o agendador."""
        self.running = False
        self.logger.info("Orquestrador Central parado")

    def executar_todas_rotinas(self):
        """Executa todas as rotinas em sequência."""
        self.logger.info("Iniciando execução de todas as rotinas")
        
        all_projects = self.get_all_projects()
        total_projetos = len(all_projects)
        projetos_executados = 0
        projetos_com_erro = []
        
        for i, projeto in enumerate(all_projects, 1):
            nome_projeto = projeto['nome']
            secao_nome = projeto['secao_nome']
            
            self.logger.info(f"[{i}/{total_projetos}] Executando: {nome_projeto} ({secao_nome})")
            
            try:
                success = self.executar_projeto(nome_projeto)
                if success:
                    projetos_executados += 1
                    self.logger.info(f"✅ {nome_projeto} executado com sucesso")
                else:
                    projetos_com_erro.append(nome_projeto)
                    self.logger.error(f"❌ Erro ao executar {nome_projeto}")
            except Exception as e:
                projetos_com_erro.append(nome_projeto)
                self.logger.error(f"❌ Exceção ao executar {nome_projeto}: {e}")
        
        self.logger.info(f"Execução completa: {projetos_executados}/{total_projetos} projetos executados com sucesso")
        
        if projetos_com_erro:
            self.logger.warning(f"Projetos com erro: {', '.join(projetos_com_erro)}")
        
        return projetos_executados == total_projetos
    
    def gerar_relatorio(self):
        """Gera o relatório completo."""
        self.logger.info("Iniciando geração do relatório")
        
        try:
            from gerador_relatorios import GeradorRelatorios
            gerador = GeradorRelatorios()
            pdf_path = gerador.gerar_relatorio_completo()
            
            if pdf_path:
                self.logger.info(f"✅ Relatório gerado com sucesso: {pdf_path}")
                return True
            else:
                self.logger.error("❌ Erro ao gerar relatório")
                return False
        except Exception as e:
            self.logger.error(f"❌ Exceção ao gerar relatório: {e}")
            return False
    
    def executar_rotina_completa(self):
        """Executa todas as rotinas e depois gera o relatório."""
        self.logger.info("=== INICIANDO ROTINA COMPLETA ===")
        
        # Executar todas as rotinas
        self.logger.info("Passo 1: Executando todas as rotinas...")
        sucesso_rotinas = self.executar_todas_rotinas()
        
        if sucesso_rotinas:
            self.logger.info("✅ Todas as rotinas executadas com sucesso")
        else:
            self.logger.warning("⚠️ Algumas rotinas falharam, mas continuando com geração do relatório")
        
        # Gerar relatório
        self.logger.info("Passo 2: Gerando relatório...")
        sucesso_relatorio = self.gerar_relatorio()
        
        if sucesso_relatorio:
            self.logger.info("✅ Relatório gerado com sucesso")
        else:
            self.logger.error("❌ Erro ao gerar relatório")
        
        self.logger.info("=== ROTINA COMPLETA FINALIZADA ===")
        return sucesso_rotinas and sucesso_relatorio

def criar_servidor():
    """Cria um servidor simples para controle."""
    import http.server
    import socketserver
    import webbrowser
    import json
    import threading
    
    # Variável global para o scheduler
    scheduler_instance = OrquestradorCentral()  # Inicializar imediatamente
    scheduler_thread = None
    
    class SchedulerHandler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html; charset=utf-8')
                self.end_headers()
                
                # Carregar lista de projetos da configuração organizados por seções
                projetos_html = ""
                
                # Carregar projetos da configuração
                if scheduler_instance and hasattr(scheduler_instance, 'config'):
                    # Debug: verificar estrutura da configuração
                    debug_info = f"<!-- DEBUG: Config keys: {list(scheduler_instance.config.keys())} -->"
                    projetos_html += debug_info
                    
                    if 'secoes' in scheduler_instance.config:
                        # Nova estrutura com seções
                        for secao_key, secao in scheduler_instance.config['secoes'].items():
                            projetos_html += f'<h3>{secao["nome"]}</h3>'
                            projetos_html += '<div class="section-projects">'
                            for projeto in secao['projetos']:
                                nome = projeto['nome']
                                descricao = projeto['descricao']
                                projetos_html += f'<button class="button manual" onclick="executarManual(\'{nome}\')">{descricao}</button><br>'
                            projetos_html += '</div><br>'
                    elif 'projetos' in scheduler_instance.config:
                        # Estrutura antiga (compatibilidade)
                        projetos_html += '<h3>ONS - Operador Nacional do Sistema</h3>'
                        projetos_html += '<div class="section-projects">'
                        for projeto in scheduler_instance.config['projetos']:
                            nome = projeto['nome']
                            descricao = projeto['descricao']
                            projetos_html += f'<button class="button manual" onclick="executarManual(\'{nome}\')">{descricao}</button><br>'
                        projetos_html += '</div>'
                else:
                    # Fallback: adicionar botões básicos
                    projetos_html = '''
                    <h3>ONS - Operador Nacional do Sistema</h3>
                    <div class="section-projects">
                    <button class="button manual" onclick="executarManual('curtailment')">Sistema de Curtailment</button><br>
                    <button class="button manual" onclick="executarManual('precos_energia')">Sistema de Precos de Energia BR</button><br>
                    <button class="button manual" onclick="executarManual('geracao_usina')">Geracao por Usina - ONS</button><br>
                    <button class="button manual" onclick="executarManual('analise_carga')">Analise de Carga Energetica - ONS</button><br>
                    <button class="button manual" onclick="executarManual('cvu_termicas')">CVU Termicas - ONS</button><br>
                    <button class="button manual" onclick="executarManual('carga_liquida')">Analise de Carga Liquida - ONS</button><br>
                    </div>
                    '''

                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Orquestrador Central ONS</title>
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        h1 {{ color: #2c3e50; text-align: center; margin-bottom: 30px; }}
                        h2 {{ color: #34495e; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                        .button {{ padding: 12px 24px; margin: 8px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; transition: background-color 0.3s; }}
                        .start {{ background-color: #27ae60; color: white; }}
                        .start:hover {{ background-color: #219a52; }}
                        .stop {{ background-color: #e74c3c; color: white; }}
                        .stop:hover {{ background-color: #c0392b; }}
                        .manual {{ background-color: #3498db; color: white; }}
                        .manual:hover {{ background-color: #2980b9; }}
                        .manual:disabled {{ background-color: #bdc3c7; cursor: not-allowed; }}
                        .manual:disabled:hover {{ background-color: #bdc3c7; }}
                        .status {{ padding: 15px; margin: 15px 0; border-radius: 5px; font-weight: bold; text-align: center; }}
                        .running {{ background-color: #d4edda; border: 1px solid #c3e6cb; color: #155724; }}
                        .stopped {{ background-color: #f8d7da; border: 1px solid #f5c6cb; color: #721c24; }}
                        .log {{ background-color: #2c3e50; color: #ecf0f1; border: 1px solid #34495e; padding: 15px; margin: 15px 0; font-family: 'Courier New', monospace; font-size: 12px; max-height: 300px; overflow-y: auto; border-radius: 5px; }}
                        .projects-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin: 20px 0; }}
                        .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 15px; border-radius: 5px; margin: 15px 0; }}
                        .execution-status {{ background-color: #e8f5e8; border: 2px solid #4caf50; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                        .execution-log {{ background-color: #1e1e1e; color: #00ff00; border: 1px solid #333; padding: 15px; margin: 10px 0; font-family: 'Courier New', monospace; font-size: 11px; max-height: 200px; overflow-y: auto; border-radius: 5px; white-space: pre-wrap; }}
                        h3 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 5px; margin-top: 20px; margin-bottom: 15px; }}
                        .section-projects {{ background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 15px; margin-bottom: 10px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Orquestrador Central ONS & Agro</h1>
                        
                        <div class="warning">
                            <strong>Modo Manual Ativo:</strong> Agendamentos automaticos foram desabilitados conforme solicitacao.
                        </div>
                        
                        <div id="status" class="status stopped">Status: Parado</div>
                        
                        <h2>Controle do Servidor</h2>
                        <button class="button start" onclick="startScheduler()">Iniciar Servidor</button>
                        <button class="button stop" onclick="stopScheduler()">Parar Servidor</button>
                        
                        <h2>Funções Globais</h2>
                        <div style="margin-bottom: 20px;">
                            <button class="button manual" onclick="executarManual('gerar_relatorio')" style="background-color: #9b59b6;">📊 Gerar Relatório</button>
                            <button class="button manual" onclick="executarManual('rotina_completa')" style="background-color: #e67e22;">🚀 Rotina Completa + Relatório</button>
                        </div>
                        
                        <h2>Execucao Manual de Projetos</h2>
                        <div class="projects-grid">
                            {projetos_html}
                        </div>
                        
                        <div id="execution-status" class="execution-status" style="display: none;">
                            <h3>Rotina em Execucao</h3>
                            <div id="current-project"></div>
                            <div class="execution-log" id="execution-log">
                                <strong>Preparando execucao...</strong>
                            </div>
                        </div>
                        
                        <h2>Logs de Execucao</h2>
                        <div class="log" id="log">
                            <strong>Sistema iniciado - Aguardando acoes...</strong>
                        </div>
                    </div>
                    
                    <script>
                        function startScheduler() {{
                            fetch('/start', {{method: 'POST'}})
                                .then(response => response.json())
                                .then(data => {{
                                    document.getElementById('status').innerHTML = 'Status: Executando';
                                    document.getElementById('status').className = 'status running';
                                    addLog('Servidor iniciado com sucesso');
                                }});
                        }}
                        
                        function stopScheduler() {{
                            fetch('/stop', {{method: 'POST'}})
                                .then(response => response.json())
                                .then(data => {{
                                    document.getElementById('status').innerHTML = 'Status: Parado';
                                    document.getElementById('status').className = 'status stopped';
                                    addLog('Servidor parado');
                                }});
                        }}
                        
                        let currentExecution = null;
                        
                        function executarManual(projeto) {{
                            // Evitar execuções paralelas
                            if (currentExecution) {{
                                addLog('Execucao em andamento: ' + currentExecution + '. Aguarde...');
                                return;
                            }}
                            
                            currentExecution = projeto;
                            
                            // Mostrar área de execução
                            document.getElementById('execution-status').style.display = 'block';
                            document.getElementById('current-project').innerHTML = '<strong>Executando: ' + projeto + '</strong>';
                            document.getElementById('execution-log').innerHTML = 'Iniciando execucao...\\n';
                            
                            // Desabilitar botões durante execução
                            const buttons = document.querySelectorAll('.manual');
                            buttons.forEach(btn => btn.disabled = true);
                            
                            addLog('Iniciando execucao de: ' + projeto);
                            
                            // Simular logs de progresso
                            let logProgress = setInterval(() => {{
                                document.getElementById('execution-log').innerHTML += '.';
                            }}, 1000);
                            
                            fetch('/manual/' + projeto, {{method: 'POST'}})
                                .then(response => response.json())
                                .then(data => {{
                                    clearInterval(logProgress);
                                    
                                    if (data.status === 'success') {{
                                        addLog('Execucao concluida com sucesso: ' + projeto);
                                        document.getElementById('execution-log').innerHTML += '\\n\\n=== EXECUCAO CONCLUIDA COM SUCESSO ===';
                                        document.getElementById('execution-status').style.backgroundColor = '#d4edda';
                                        document.getElementById('execution-status').style.borderColor = '#c3e6cb';
                                    }} else {{
                                        addLog('Erro ao executar: ' + projeto);
                                        document.getElementById('execution-log').innerHTML += '\\n\\n=== ERRO NA EXECUCAO ===\\n' + (data.message || 'Erro desconhecido');
                                        document.getElementById('execution-status').style.backgroundColor = '#f8d7da';
                                        document.getElementById('execution-status').style.borderColor = '#f5c6cb';
                                    }}
                                    
                                    // Reabilitar botões
                                    buttons.forEach(btn => btn.disabled = false);
                                    currentExecution = null;
                                    
                                    // Esconder área de execução após 5 segundos
                                    setTimeout(() => {{
                                        document.getElementById('execution-status').style.display = 'none';
                                        document.getElementById('execution-status').style.backgroundColor = '#e8f5e8';
                                        document.getElementById('execution-status').style.borderColor = '#4caf50';
                                    }}, 5000);
                                }})
                                .catch(error => {{
                                    clearInterval(logProgress);
                                    addLog('Erro de comunicacao: ' + error);
                                    document.getElementById('execution-log').innerHTML += '\\n\\n=== ERRO DE COMUNICACAO ===\\n' + error;
                                    document.getElementById('execution-status').style.backgroundColor = '#f8d7da';
                                    document.getElementById('execution-status').style.borderColor = '#f5c6cb';
                                    
                                    // Reabilitar botões
                                    buttons.forEach(btn => btn.disabled = false);
                                    currentExecution = null;
                                    
                                    setTimeout(() => {{
                                        document.getElementById('execution-status').style.display = 'none';
                                        document.getElementById('execution-status').style.backgroundColor = '#e8f5e8';
                                        document.getElementById('execution-status').style.borderColor = '#4caf50';
                                    }}, 5000);
                                }});
                        }}
                        
                        function addLog(message) {{
                            const log = document.getElementById('log');
                            const time = new Date().toLocaleTimeString();
                            log.innerHTML += '<br>' + time + ': ' + message;
                            log.scrollTop = log.scrollHeight;
                        }}
                    </script>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode())
            
            else:
                super().do_GET()
        
        def do_POST(self):
            nonlocal scheduler_instance, scheduler_thread
            
            if self.path == '/start':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Iniciar scheduler em thread separada
                if scheduler_instance is None:
                    scheduler_instance = OrquestradorCentral()
                    scheduler_thread = threading.Thread(target=scheduler_instance.iniciar_scheduler)
                    scheduler_thread.daemon = True
                    scheduler_thread.start()
                
                response = {'status': 'started'}
                self.wfile.write(json.dumps(response).encode())
            
            elif self.path == '/stop':
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Parar scheduler
                if scheduler_instance:
                    scheduler_instance.parar_scheduler()
                    scheduler_instance = None
                    scheduler_thread = None
                
                response = {'status': 'stopped'}
                self.wfile.write(json.dumps(response).encode())
            
            elif self.path.startswith('/manual/'):
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                
                # Executar projeto manualmente
                path_parts = self.path.split('/')[2:]  # Remove '' e 'manual'
                projeto = path_parts[0] if path_parts else None
                
                if scheduler_instance and projeto:
                    success = scheduler_instance.executar_manual(projeto)
                    response = {
                        'status': 'success' if success else 'error', 
                        'projeto': projeto
                    }
                else:
                    response = {'status': 'error', 'message': 'Scheduler não iniciado ou projeto não especificado'}
                
                self.wfile.write(json.dumps(response).encode())
            
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'error': 'Endpoint não encontrado'}
                self.wfile.write(json.dumps(response).encode())
    
    def iniciar_servidor():
        PORT = 8080
        with socketserver.TCPServer(("", PORT), SchedulerHandler) as httpd:
            print(f"Servidor iniciado em http://localhost:{PORT}")
            httpd.serve_forever()
    
    return iniciar_servidor

def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Orquestrador Central")
    parser.add_argument("--projeto", help="Executar projeto específico manualmente")
    parser.add_argument("--agendador", action="store_true", help="Iniciar agendador")
    parser.add_argument("--servidor", action="store_true", help="Iniciar servidor web")
    
    args = parser.parse_args()
    
    scheduler = OrquestradorCentral()
    
    if args.servidor:
        # Iniciar servidor web
        servidor = criar_servidor()
        servidor()
    elif args.projeto:
        # Execução manual
        success = scheduler.executar_manual(args.projeto)
        exit(0 if success else 1)
    else:
        # Iniciar agendador
        scheduler.iniciar_scheduler()

if __name__ == "__main__":
    main() 