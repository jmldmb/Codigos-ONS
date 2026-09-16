"""
Gerador Estocástico de Perfis Horários Eólicos
===============================================

Modelo AR(1) com Perfil Horário para geração eólica:
    Y_h = μ_h * (1 + Z_h)
    Z_h = φ * Z_{h-1} + ε_h,  ε_h ~ N(0, σ²_ε)

Baseado em literatura de planejamento energético estocástico.

Autor: ONS
Data: Novembro 2024
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import json
import numpy as np
from pathlib import Path
from typing import Union, Dict


class EolicaSampler:
    """
    Gerador estocástico de perfis horários eólicos usando modelo AR(1)
    
    O modelo combina:
    1. Perfil horário médio (determinístico)
    2. Variabilidade estocástica via processo AR(1)
    """
    
    def __init__(
        self, 
        perfis_path: Union[str, Path] = None,
        parametros_path: Union[str, Path] = None
    ):
        """
        Inicializa o sampler estocástico
        
        Args:
            perfis_path: Caminho para arquivo JSON com perfis horários.
            parametros_path: Caminho para arquivo JSON com parâmetros AR(1).
                           Se None, usa caminhos padrão.
        """
        if perfis_path is None or parametros_path is None:
            base_dir = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
            perfis_path = base_dir / "output" / "sample" / "eolica" / "perfis_horarios.json"
            parametros_path = base_dir / "output" / "sample" / "eolica" / "parametros_ar1.json"
        
        self.perfis_path = Path(perfis_path)
        self.parametros_path = Path(parametros_path)
        
        self.perfis = self._carregar_perfis()
        self.parametros = self._carregar_parametros()
    
    def _carregar_perfis(self) -> Dict:
        """Carrega perfis horários do arquivo JSON"""
        if not self.perfis_path.exists():
            raise FileNotFoundError(
                f"Arquivo de perfis não encontrado: {self.perfis_path}\n"
                "Execute 'processar_perfis_eolicos.py' primeiro."
            )
        
        with open(self.perfis_path, 'r', encoding='utf-8') as f:
            perfis = json.load(f)
        
        # Converter chaves para int
        perfis_int = {}
        for mes_str, dados in perfis.items():
            mes = int(mes_str)
            perfis_int[mes] = dados
            perfis_int[mes]['perfil_proporcional'] = {
                int(h): v for h, v in dados['perfil_proporcional'].items()
            }
        
        return perfis_int
    
    def _carregar_parametros(self) -> Dict:
        """Carrega parâmetros AR(1) do arquivo JSON"""
        if not self.parametros_path.exists():
            raise FileNotFoundError(
                f"Arquivo de parâmetros não encontrado: {self.parametros_path}\n"
                "Execute 'processar_perfis_eolicos.py' primeiro."
            )
        
        with open(self.parametros_path, 'r', encoding='utf-8') as f:
            parametros = json.load(f)
        
        # Converter chaves para int
        return {int(k): v for k, v in parametros.items()}
    
    def gerar_ruido_ar1(self, phi: float, sigma_epsilon: float, n: int = 24, seed: int = None) -> np.ndarray:
        """
        Gera processo AR(1) estacionário
        
        Args:
            phi: Coeficiente de autocorrelação
            sigma_epsilon: Desvio padrão do ruído branco
            n: Número de pontos (horas)
            seed: Seed para reprodutibilidade
        
        Returns:
            Array com n valores do processo AR(1)
        """
        if seed is not None:
            np.random.seed(seed)
        
        # Inicializar processo AR(1) na distribuição estacionária
        # Var(Z) = σ²_ε / (1 - φ²)
        sigma_inicial = sigma_epsilon / np.sqrt(1 - phi**2) if abs(phi) < 1 else sigma_epsilon
        
        Z = np.zeros(n)
        Z[0] = np.random.normal(0, sigma_inicial)
        
        # Gerar sequência AR(1)
        for t in range(1, n):
            epsilon = np.random.normal(0, sigma_epsilon)
            Z[t] = phi * Z[t-1] + epsilon
        
        return Z
    
    def gerar_perfil_dia(
        self,
        mes: int,
        mw_medios: float,
        seed: int = None,
        deterministico: bool = False
    ) -> np.ndarray:
        """
        Gera perfil horário estocástico de geração eólica para UM dia
        
        Args:
            mes: Mês (1-12)
            mw_medios: Potência média do mês em MW (MWmédios)
            seed: Seed para reprodutibilidade (None = aleatório)
            deterministico: Se True, retorna apenas perfil médio (sem ruído)
        
        Returns:
            Array com 24 valores (geração por hora em MWh)
        """
        if mes not in self.perfis:
            raise ValueError(f"Mês {mes} não encontrado nos perfis. Use 1-12.")
        
        # 1. Perfil determinístico base
        proporcoes = self.perfis[mes]['perfil_proporcional']
        perfil_base = np.array([proporcoes[h] for h in range(24)])
        perfil_base = perfil_base * (mw_medios * 24)  # Converter para MWh
        
        # 2. Se deterministico, retornar apenas o perfil médio
        if deterministico:
            return perfil_base
        
        # 3. Gerar ruído estocástico AR(1)
        phi = self.parametros[mes]['phi']
        sigma_epsilon = self.parametros[mes]['sigma_epsilon']
        
        Z = self.gerar_ruido_ar1(phi, sigma_epsilon, n=24, seed=seed)
        
        # 4. Aplicar ruído ao perfil (modelo multiplicativo)
        # Y_h = μ_h * (1 + Z_h)
        perfil_estocastico = perfil_base * (1 + Z)
        
        # 5. Garantir não-negatividade
        perfil_estocastico = np.maximum(perfil_estocastico, 0)
        
        # 6. Normalizar para manter o total (MWmédios * 24)
        total_desejado = mw_medios * 24
        perfil_estocastico = perfil_estocastico * (total_desejado / perfil_estocastico.sum())
        
        return perfil_estocastico
    
    def gerar_multiplos_cenarios(
        self,
        mes: int,
        mw_medios: float,
        n_cenarios: int = 100,
        seed: int = None
    ) -> np.ndarray:
        """
        Gera múltiplos cenários estocásticos
        
        Args:
            mes: Mês (1-12)
            mw_medios: Potência média do mês
            n_cenarios: Número de cenários a gerar
            seed: Seed inicial
        
        Returns:
            Array (n_cenarios, 24) com perfis estocásticos
        """
        cenarios = []
        
        for i in range(n_cenarios):
            seed_i = None if seed is None else seed + i
            cenario = self.gerar_perfil_dia(mes, mw_medios, seed=seed_i)
            cenarios.append(cenario)
        
        return np.array(cenarios)
    
    def get_estatisticas_cenarios(
        self,
        mes: int,
        mw_medios: float,
        n_cenarios: int = 1000,
        seed: int = None
    ) -> Dict:
        """
        Gera estatísticas de múltiplos cenários
        
        Returns:
            Dicionário com média, percentis, etc.
        """
        cenarios = self.gerar_multiplos_cenarios(mes, mw_medios, n_cenarios, seed)
        
        return {
            'media': np.mean(cenarios, axis=0),
            'std': np.std(cenarios, axis=0),
            'p05': np.percentile(cenarios, 5, axis=0),
            'p25': np.percentile(cenarios, 25, axis=0),
            'p50': np.percentile(cenarios, 50, axis=0),
            'p75': np.percentile(cenarios, 75, axis=0),
            'p95': np.percentile(cenarios, 95, axis=0),
            'min': np.min(cenarios, axis=0),
            'max': np.max(cenarios, axis=0)
        }
    
    def get_info_modelo(self, mes: int) -> Dict:
        """
        Retorna informações sobre o modelo de um mês
        
        Args:
            mes: Mês (1-12)
        
        Returns:
            Dicionário com informações do modelo
        """
        if mes not in self.perfis:
            raise ValueError(f"Mês {mes} não encontrado. Use 1-12.")
        
        perfil = self.perfis[mes]
        params = self.parametros[mes]
        proporcoes = perfil['perfil_proporcional']
        
        hora_min = min(proporcoes.items(), key=lambda x: x[1])[0]
        hora_max = max(proporcoes.items(), key=lambda x: x[1])[0]
        
        return {
            'mes': mes,
            'nome_mes': perfil['nome_mes'],
            'n_observacoes': perfil.get('n_observacoes', 0),
            'hora_minima': hora_min,
            'hora_maxima': hora_max,
            'phi': params['phi'],
            'sigma_epsilon': params['sigma_epsilon'],
            'total_diario_medio_mwh': perfil.get('total_diario_medio_mwh')
        }


# Função de conveniência
def gerar_perfil_eolico(mes: int, mw_medios: float, seed: int = None) -> np.ndarray:
    """
    Função conveniente para gerar perfil eólico estocástico
    
    Args:
        mes: Mês (1-12)
        mw_medios: Potência média do mês em MW
        seed: Seed para reprodutibilidade
    
    Returns:
        Array com 24 valores (MWh por hora)
    """
    sampler = EolicaSampler()
    return sampler.gerar_perfil_dia(mes, mw_medios, seed=seed)


if __name__ == "__main__":
    # Exemplo de uso
    print("="*70)
    print("EXEMPLO DE USO - EOLICA SAMPLER (ESTOCÁSTICO AR(1))")
    print("="*70)
    
    sampler = EolicaSampler()
    
    # Exemplo 1: Gerar perfil determinístico
    print("\n[Exemplo 1] Perfil determinístico (sem ruído):")
    perfil_det = sampler.gerar_perfil_dia(mes=9, mw_medios=400, deterministico=True)
    print(f"  Input: 400 MWmédios (Setembro)")
    print(f"  Total do dia: {perfil_det.sum():.2f} MWh")
    print(f"  Hora de pico: {perfil_det.argmax()}h com {perfil_det.max():.2f} MWh")
    
    # Exemplo 2: Gerar perfil estocástico
    print("\n[Exemplo 2] Perfil estocástico (com AR(1)):")
    perfil_stoc = sampler.gerar_perfil_dia(mes=9, mw_medios=400, seed=42)
    print(f"  Input: 400 MWmédios (Setembro)")
    print(f"  Total do dia: {perfil_stoc.sum():.2f} MWh")
    print(f"  Hora de pico: {perfil_stoc.argmax()}h com {perfil_stoc.max():.2f} MWh")
    
    # Exemplo 3: Comparar múltiplos cenários
    print("\n[Exemplo 3] Estatísticas de 100 cenários:")
    stats = sampler.get_estatisticas_cenarios(mes=9, mw_medios=400, n_cenarios=100, seed=42)
    
    print(f"  Hora de pico (11h):")
    print(f"    Média:  {stats['media'][11]:.2f} MWh")
    print(f"    P05-P95: [{stats['p05'][11]:.2f}, {stats['p95'][11]:.2f}] MWh")
    print(f"    Std:    {stats['std'][11]:.2f} MWh")
    
    # Exemplo 4: Info do modelo
    print("\n[Exemplo 4] Informações do modelo:")
    for mes in [1, 6, 12]:
        info = sampler.get_info_modelo(mes)
        print(f"  {info['nome_mes']:>9s}: phi={info['phi']:.3f}, sigma={info['sigma_epsilon']:.4f}, "
              f"Pico={info['hora_maxima']:02d}h, Min={info['hora_minima']:02d}h")

