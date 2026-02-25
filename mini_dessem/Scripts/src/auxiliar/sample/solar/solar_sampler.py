"""
Gerador de Perfis Horários Solares
===================================

Módulo para gerar perfis horários de geração solar dado:
- Mês do ano
- Geração total mensal (MWh)

Retorna: Perfil horário (24 valores) com geração por hora

Autor: ONS
Data: Novembro 2024
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, Dict, List


class SolarSampler:
    """
    Gerador de perfis horários solares
    
    Usa perfis históricos médios para distribuir a geração mensal
    nas 24 horas do dia.
    """
    
    def __init__(self, perfis_path: Union[str, Path] = None, shape_exponent: float = 1.0):
        """
        Inicializa o sampler
        
        Args:
            perfis_path: Caminho para arquivo JSON com perfis horários.
                        Se None, usa caminho padrão.
            shape_exponent: Expoente para ajustar shape da curva (default=1.0).
                           > 1.0: Acentua pico, suaviza rampas
                           = 1.0: Perfil original
                           Recomendado: 1.3 a 1.8
        """
        if perfis_path is None:
            base_dir = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
            perfis_path = base_dir / "output" / "sample" / "solar" / "perfis_horarios.json"
        
        self.perfis_path = Path(perfis_path)
        self.shape_exponent = shape_exponent
        self.perfis = self._carregar_perfis()
    
    def _carregar_perfis(self) -> Dict:
        """Carrega perfis horários do arquivo JSON"""
        if not self.perfis_path.exists():
            raise FileNotFoundError(
                f"Arquivo de perfis não encontrado: {self.perfis_path}\n"
                "Execute 'processar_perfis_solares.py' primeiro."
            )
        
        with open(self.perfis_path, 'r', encoding='utf-8') as f:
            perfis = json.load(f)
        
        # Converter chaves para int
        perfis_int = {}
        for mes_str, dados in perfis.items():
            mes = int(mes_str)
            perfis_int[mes] = dados
            # Converter chaves do perfil_proporcional para int
            perfis_int[mes]['perfil_proporcional'] = {
                int(h): v for h, v in dados['perfil_proporcional'].items()
            }
        
        return perfis_int
    
    def gerar_perfil_horario(
        self, 
        mes: int, 
        geracao_total_mwh: float
    ) -> np.ndarray:
        """
        Gera perfil horário de geração solar
        
        Args:
            mes: Mês do ano (1-12)
            geracao_total_mwh: Geração total do dia (MWh)
        
        Returns:
            Array com 24 valores (geração por hora em MWh)
        """
        if mes not in self.perfis:
            raise ValueError(f"Mês {mes} não encontrado nos perfis. Use 1-12.")
        
        # Buscar perfil proporcional do mês
        proporcoes = self.perfis[mes]['perfil_proporcional']
        
        # Aplicar transformação de shape se configurado
        if self.shape_exponent != 1.0:
            # Power transform: eleva proporções ao expoente
            proporcoes_array = np.array([proporcoes[h] for h in range(24)])
            proporcoes_transform = proporcoes_array ** self.shape_exponent
            proporcoes_transform = proporcoes_transform / proporcoes_transform.sum()
            proporcoes = {h: float(proporcoes_transform[h]) for h in range(24)}
        
        # Gerar perfil horário
        perfil = np.zeros(24)
        for hora in range(24):
            perfil[hora] = proporcoes[hora] * geracao_total_mwh
        
        # Normalizar para somar exatamente geracao_total_mwh
        perfil = perfil * (geracao_total_mwh / perfil.sum())
        
        return perfil
    
    def gerar_perfil_dia(
        self,
        mes: int,
        mw_medios: float
    ) -> np.ndarray:
        """
        Gera perfil horário de UM dia típico do mês
        
        Args:
            mes: Mês (1-12)
            mw_medios: Potência média do mês em MW (MWmédios)
                      MWmédios = Energia Total Mensal (MWh) / Número de Horas no Mês
        
        Returns:
            Array com 24 valores (geração por hora em MWh) para UM dia típico
        """
        # MWmédios já é a potência média ao longo do mês inteiro
        # Para um dia típico, multiplicamos por 24 horas
        geracao_diaria_tipica = mw_medios * 24
        
        # Aplicar perfil horário do mês
        perfil_dia = self.gerar_perfil_horario(mes, geracao_diaria_tipica)
        
        return perfil_dia
    
    def get_info_perfil(self, mes: int) -> Dict:
        """
        Retorna informações sobre o perfil de um mês
        
        Args:
            mes: Mês (1-12)
        
        Returns:
            Dicionário com informações do perfil
        """
        if mes not in self.perfis:
            raise ValueError(f"Mês {mes} não encontrado. Use 1-12.")
        
        perfil = self.perfis[mes]
        proporcoes = perfil['perfil_proporcional']
        
        # Hora de pico
        hora_pico = max(proporcoes.items(), key=lambda x: x[1])[0]
        prop_pico = proporcoes[hora_pico]
        
        return {
            'mes': mes,
            'nome_mes': perfil['nome_mes'],
            'n_observacoes': perfil.get('n_observacoes', 0),
            'hora_pico': hora_pico,
            'proporcao_pico': prop_pico,
            'total_mensal_medio_mwh': perfil.get('total_mensal_medio_mwh'),
            'interpolado': perfil.get('interpolado', False)
        }
    
    def get_todos_perfis(self) -> pd.DataFrame:
        """
        Retorna todos os perfis em formato DataFrame
        
        Returns:
            DataFrame com perfis de todos os meses
        """
        dados = []
        for mes in range(1, 13):
            proporcoes = self.perfis[mes]['perfil_proporcional']
            for hora in range(24):
                dados.append({
                    'mes': mes,
                    'nome_mes': self.perfis[mes]['nome_mes'],
                    'hora': hora,
                    'proporcao': proporcoes[hora]
                })
        
        return pd.DataFrame(dados)


# Funções de conveniência
def gerar_perfil_solar(mes: int, geracao_total_mwh: float) -> np.ndarray:
    """
    Função conveniente para gerar perfil horário
    
    Args:
        mes: Mês (1-12)
        geracao_total_mwh: Geração total do dia (MWh)
    
    Returns:
        Array com 24 valores (MWh por hora)
    """
    sampler = SolarSampler()
    return sampler.gerar_perfil_horario(mes, geracao_total_mwh)


def gerar_dia_tipico(mes: int, mw_medios: float) -> np.ndarray:
    """
    Função conveniente para gerar perfil de um dia típico
    
    Args:
        mes: Mês (1-12)
        mw_medios: Potência média do mês em MW (MWmédios)
    
    Returns:
        Array com 24 valores (MWh por hora) para um dia típico
    """
    sampler = SolarSampler()
    return sampler.gerar_perfil_dia(mes, mw_medios)


if __name__ == "__main__":
    # Exemplo de uso
    print("="*70)
    print("EXEMPLO DE USO - SOLAR SAMPLER")
    print("="*70)
    
    # Criar sampler
    sampler = SolarSampler()
    
    # Exemplo 1: Gerar perfil de um dia
    print("\n[Exemplo 1] Perfil de um dia em dezembro:")
    perfil_dia = sampler.gerar_perfil_horario(mes=12, geracao_total_mwh=4000)
    
    print(f"  Geração total: {perfil_dia.sum():.2f} MWh")
    print(f"  Hora de pico: {perfil_dia.argmax()}h com {perfil_dia.max():.2f} MWh")
    print("\n  Primeiras 6 horas:")
    for h in range(6):
        print(f"    {h:02d}h: {perfil_dia[h]:>8.2f} MWh")
    
    # Exemplo 2: Info do perfil
    print("\n[Exemplo 2] Informações dos perfis:")
    for mes in [1, 6, 12]:
        info = sampler.get_info_perfil(mes)
        print(f"  {info['nome_mes']:>9s}: Pico às {info['hora_pico']:02d}h ({info['proporcao_pico']*100:.2f}%)")
    
    # Exemplo 3: Gerar dia típico
    print("\n[Exemplo 3] Gerar dia típico de dezembro:")
    mw_medios_dez = 166.67  # Se o mês tem 124.000 MWh / 744 horas
    perfil_dia = sampler.gerar_perfil_dia(mes=12, mw_medios=mw_medios_dez)
    print(f"  Input: {mw_medios_dez:.2f} MWmédios")
    print(f"  Output: 24 valores (um dia típico)")
    print(f"  Total do dia: {perfil_dia.sum():,.2f} MWh")
    print(f"  Hora de pico: {perfil_dia.argmax()}h com {perfil_dia.max():.2f} MWh")

