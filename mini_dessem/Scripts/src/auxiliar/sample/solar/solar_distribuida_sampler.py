"""
Gerador de Perfis Horários Solares - Geração Distribuída
==========================================================

Módulo para gerar perfis horários de geração solar DISTRIBUÍDA.

Diferente da geração centralizada:
- Pico mais cedo (11h vs 14h)
- Mais concentrada no meio do dia
- Rampas mais suaves

Autor: ONS
Data: Novembro 2024
"""

import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Union, Dict


class SolarDistribuidaSampler:
    """
    Gerador de perfis horários solares para geração DISTRIBUÍDA
    
    Usa perfis históricos calculados a partir de:
    Total (BALANCO_ENERGIA) - Centralizada (curtailment)
    """
    
    def __init__(self, perfis_path: Union[str, Path] = None, shape_exponent: float = 1.0):
        """
        Inicializa o sampler de distribuída
        
        Args:
            perfis_path: Caminho para arquivo JSON com perfis horários.
                        Se None, usa caminho padrão.
            shape_exponent: Expoente para ajustar shape da curva (default=1.0).
                           > 1.0: Acentua pico, suaviza rampas
                           = 1.0: Perfil original
                           Recomendado: 1.0 a 1.5 (distribuída já é mais concentrada)
        """
        if perfis_path is None:
            base_dir = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
            perfis_path = base_dir / "output" / "sample" / "solar_distribuida" / "perfis_horarios_distribuida.json"
        
        self.perfis_path = Path(perfis_path)
        self.shape_exponent = shape_exponent
        self.perfis = self._carregar_perfis()
    
    def _carregar_perfis(self) -> Dict:
        """Carrega perfis horários do arquivo JSON"""
        if not self.perfis_path.exists():
            raise FileNotFoundError(
                f"Arquivo de perfis não encontrado: {self.perfis_path}\n"
                "Execute 'calcular_geracao_distribuida_solar.py' primeiro."
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
        Gera perfil horário de geração solar distribuída
        
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
            Array com 24 valores (geração por hora em MW) para UM dia típico
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
            'total_diario_medio_mwh': perfil.get('total_diario_mwh'),
            'media_mw': perfil.get('media_mw'),
            'interpolado': perfil.get('interpolado', False)
        }


# Funções de conveniência
def gerar_perfil_solar_distribuida(mes: int, geracao_total_mwh: float) -> np.ndarray:
    """
    Função conveniente para gerar perfil horário de distribuída
    
    Args:
        mes: Mês (1-12)
        geracao_total_mwh: Geração total do dia (MWh)
    
    Returns:
        Array com 24 valores (MWh por hora)
    """
    sampler = SolarDistribuidaSampler()
    return sampler.gerar_perfil_horario(mes, geracao_total_mwh)


def gerar_dia_tipico_distribuida(mes: int, mw_medios: float) -> np.ndarray:
    """
    Função conveniente para gerar perfil de um dia típico distribuído
    
    Args:
        mes: Mês (1-12)
        mw_medios: Potência média do mês em MW (MWmédios)
    
    Returns:
        Array com 24 valores (MW por hora) para um dia típico
    """
    sampler = SolarDistribuidaSampler()
    return sampler.gerar_perfil_dia(mes, mw_medios)


if __name__ == "__main__":
    # Exemplo de uso
    print("="*70)
    print("EXEMPLO DE USO - SOLAR DISTRIBUÍDA SAMPLER")
    print("="*70)
    
    # Criar sampler
    sampler = SolarDistribuidaSampler()
    
    # Exemplo: Perfil para setembro
    print("\n[Exemplo] Perfil de geração distribuída em setembro:")
    mw_medios_set = 6487  # Valor calculado
    perfil_dia = sampler.gerar_perfil_dia(mes=9, mw_medios=mw_medios_set)
    
    print(f"  Input: {mw_medios_set:,.0f} MWmédios")
    print(f"  Output: 24 valores (um dia típico)")
    print(f"  Total do dia: {perfil_dia.sum():,.0f} MWh")
    print(f"  Hora de pico: {perfil_dia.argmax()}h com {perfil_dia.max():,.0f} MW")
    print(f"  Média: {perfil_dia.mean():,.0f} MW")
    
    # Info do perfil
    info = sampler.get_info_perfil(9)
    print(f"\n  Informações do perfil:")
    print(f"    Mês: {info['nome_mes']}")
    print(f"    Hora de pico: {info['hora_pico']:02d}h")
    print(f"    N observações: {info['n_observacoes']}")
    print(f"    Interpolado: {info['interpolado']}")







