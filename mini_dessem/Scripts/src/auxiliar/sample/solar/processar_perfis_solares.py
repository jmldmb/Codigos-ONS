"""
Processamento de Perfis Horários Solares
========================================

Este script processa dados históricos de geração solar e extrai perfis 
horários médios por mês para uso em simulações.

Autor: ONS
Data: Novembro 2024
"""

import sys
import pandas as pd
import numpy as np
import json
from pathlib import Path

# Configurar encoding UTF-8 para Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Definir diretórios
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
DATA_PATH = BASE_DIR / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment" / "por_mes" / "perfil_hora_por_mes.csv"
OUTPUT_DIR = BASE_DIR / "output" / "sample" / "solar"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def processar_perfis_horarios():
    """
    Processa dados históricos e extrai perfis horários médios por mês
    
    Returns:
        dict: Dicionário com perfis horários por mês
    """
    print("="*70)
    print("PROCESSAMENTO DE PERFIS HORÁRIOS SOLARES")
    print("="*70)
    
    # Carregar dados
    print(f"\n[1/4] Carregando dados de: {DATA_PATH}")
    df = pd.read_csv(DATA_PATH)
    df['mes'] = pd.to_datetime(df['mes'])
    df['mes_num'] = df['mes'].dt.month
    
    print(f"  ✓ {len(df)} registros carregados")
    print(f"  ✓ Período: {df['mes'].min()} a {df['mes'].max()}")
    
    # Calcular perfis médios por mês
    print("\n[2/4] Calculando perfis horários médios por mês...")
    
    perfis = {}
    
    for mes_num in range(1, 13):
        dados_mes = df[df['mes_num'] == mes_num]
        
        if len(dados_mes) == 0:
            print(f"  ⚠️  Mês {mes_num:02d}: Sem dados, usando interpolação")
            continue
        
        # Perfil horário médio DIÁRIO (MWh por hora, média entre dias)
        # O arquivo já contém médias diárias por hora
        perfil_hora = dados_mes.groupby('hora')['potencial_total_mwh_media'].mean()
        
        # Total diário típico (soma das 24 horas)
        total_diario = perfil_hora.sum()
        
        # Total mensal típico (assumindo ~30 dias)
        n_dias_medio = 30.5
        total_mensal = total_diario * n_dias_medio
        
        # Proporção de cada hora em relação ao total diário
        proporcoes = (perfil_hora / total_diario).to_dict()
        
        perfis[mes_num] = {
            'mes': mes_num,
            'nome_mes': pd.Timestamp(2024, mes_num, 1).strftime('%B'),
            'n_observacoes': len(dados_mes['mes'].unique()),
            'total_diario_medio_mwh': float(total_diario),
            'total_mensal_medio_mwh': float(total_mensal),
            'perfil_absoluto_mwh': {int(k): float(v) for k, v in perfil_hora.items()},
            'perfil_proporcional': {int(k): float(v) for k, v in proporcoes.items()}
        }
        
        print(f"  ✓ Mês {mes_num:02d} ({perfis[mes_num]['nome_mes']:>9s}): "
              f"{perfis[mes_num]['n_observacoes']} observações, "
              f"média diária = {total_diario:>8,.0f} MWh, "
              f"total mensal ≈ {total_mensal:>10,.0f} MWh")
    
    # Interpolar meses faltantes se necessário
    meses_com_dados = list(perfis.keys())
    if len(meses_com_dados) < 12:
        print("\n  ℹ️  Interpolando meses faltantes...")
        for mes_num in range(1, 13):
            if mes_num not in perfis:
                # Interpolar entre meses vizinhos
                mes_antes = max([m for m in meses_com_dados if m < mes_num], default=None)
                mes_depois = min([m for m in meses_com_dados if m > mes_num], default=None)
                
                if mes_antes and mes_depois:
                    # Interpolação linear
                    peso_antes = (mes_depois - mes_num) / (mes_depois - mes_antes)
                    peso_depois = (mes_num - mes_antes) / (mes_depois - mes_antes)
                    
                    perfil_interp = {}
                    for hora in range(24):
                        val_antes = perfis[mes_antes]['perfil_proporcional'][hora]
                        val_depois = perfis[mes_depois]['perfil_proporcional'][hora]
                        perfil_interp[hora] = peso_antes * val_antes + peso_depois * val_depois
                    
                    perfis[mes_num] = {
                        'mes': mes_num,
                        'nome_mes': pd.Timestamp(2024, mes_num, 1).strftime('%B'),
                        'n_observacoes': 0,
                        'total_mensal_medio_mwh': None,
                        'perfil_absoluto_mwh': None,
                        'perfil_proporcional': perfil_interp,
                        'interpolado': True
                    }
                    print(f"  ✓ Mês {mes_num:02d} interpolado")
    
    # Estatísticas gerais
    print("\n[3/4] Estatísticas dos perfis:")
    
    # Hora de pico por mês
    for mes_num in sorted(perfis.keys()):
        prop = perfis[mes_num]['perfil_proporcional']
        hora_pico = max(prop.items(), key=lambda x: x[1])[0]
        valor_pico = prop[hora_pico] * 100
        
        print(f"  • {perfis[mes_num]['nome_mes']:>9s}: Pico às {hora_pico:02d}h ({valor_pico:>5.2f}% do total)")
    
    # Salvar perfis
    print("\n[4/4] Salvando perfis...")
    
    output_file = OUTPUT_DIR / "perfis_horarios.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(perfis, f, indent=2, ensure_ascii=False)
    
    print(f"  ✓ Perfis salvos em: {output_file}")
    
    # Salvar também em formato CSV para fácil visualização
    csv_data = []
    for mes_num, dados in perfis.items():
        for hora, proporcao in dados['perfil_proporcional'].items():
            csv_data.append({
                'mes': mes_num,
                'nome_mes': dados['nome_mes'],
                'hora': hora,
                'proporcao': proporcao,
                'perfil_absoluto_mwh': dados.get('perfil_absoluto_mwh', {}).get(hora) if dados.get('perfil_absoluto_mwh') else None
            })
    
    df_perfis = pd.DataFrame(csv_data)
    csv_file = OUTPUT_DIR / "perfis_horarios.csv"
    df_perfis.to_csv(csv_file, index=False)
    print(f"  ✓ Perfis salvos em CSV: {csv_file}")
    
    print("\n" + "="*70)
    print("PROCESSAMENTO CONCLUÍDO COM SUCESSO!")
    print("="*70)
    
    return perfis


if __name__ == "__main__":
    perfis = processar_perfis_horarios()

