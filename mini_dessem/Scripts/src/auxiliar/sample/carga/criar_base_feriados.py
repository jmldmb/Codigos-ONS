"""
Criar base de feriados brasileiros (2023-2025)
"""
import pandas as pd
from pathlib import Path
from datetime import datetime

print("="*100)
print("  CRIANDO BASE DE FERIADOS BRASILEIROS")
print("="*100)

# Feriados NACIONAIS fixos
feriados_fixos = [
    # 2023
    ('2023-01-01', 'Ano Novo'),
    ('2023-04-21', 'Tiradentes'),
    ('2023-05-01', 'Dia do Trabalho'),
    ('2023-09-07', 'Independência'),
    ('2023-10-12', 'Nossa Senhora Aparecida'),
    ('2023-11-02', 'Finados'),
    ('2023-11-15', 'Proclamação da República'),
    ('2023-12-25', 'Natal'),
    
    # 2024
    ('2024-01-01', 'Ano Novo'),
    ('2024-04-21', 'Tiradentes'),
    ('2024-05-01', 'Dia do Trabalho'),
    ('2024-09-07', 'Independência'),
    ('2024-10-12', 'Nossa Senhora Aparecida'),
    ('2024-11-02', 'Finados'),
    ('2024-11-15', 'Proclamação da República'),
    ('2024-11-20', 'Consciência Negra'),  # Nacional desde 2024
    ('2024-12-25', 'Natal'),
    
    # 2025
    ('2025-01-01', 'Ano Novo'),
    ('2025-04-21', 'Tiradentes'),
    ('2025-05-01', 'Dia do Trabalho'),
    ('2025-09-07', 'Independência'),
    ('2025-10-12', 'Nossa Senhora Aparecida'),
    ('2025-11-02', 'Finados'),
    ('2025-11-15', 'Proclamação da República'),
    ('2025-11-20', 'Consciência Negra'),
    ('2025-12-25', 'Natal'),
]

# Feriados MÓVEIS (Carnaval, Páscoa, Corpus Christi)
feriados_moveis = [
    # 2023
    ('2023-02-20', 'Carnaval (segunda)'),
    ('2023-02-21', 'Carnaval (terça)'),
    ('2023-02-22', 'Carnaval (quarta cinzas)'),
    ('2023-04-07', 'Sexta-feira Santa'),
    ('2023-06-08', 'Corpus Christi'),
    
    # 2024
    ('2024-02-12', 'Carnaval (segunda)'),
    ('2024-02-13', 'Carnaval (terça)'),
    ('2024-02-14', 'Carnaval (quarta cinzas)'),
    ('2024-03-29', 'Sexta-feira Santa'),
    ('2024-05-30', 'Corpus Christi'),
    
    # 2025
    ('2025-03-03', 'Carnaval (segunda)'),
    ('2025-03-04', 'Carnaval (terça)'),
    ('2025-03-05', 'Carnaval (quarta cinzas)'),
    ('2025-04-18', 'Sexta-feira Santa'),
    ('2025-06-19', 'Corpus Christi'),
]

# Combinar todos
todos_feriados = feriados_fixos + feriados_moveis

# Criar DataFrame
df_feriados = pd.DataFrame(todos_feriados, columns=['data', 'nome'])
df_feriados['data'] = pd.to_datetime(df_feriados['data'])
df_feriados = df_feriados.sort_values('data').reset_index(drop=True)

print(f"\n[INFO] Total de feriados: {len(df_feriados)}")
print(f"       2023: {len(df_feriados[df_feriados['data'].dt.year == 2023])}")
print(f"       2024: {len(df_feriados[df_feriados['data'].dt.year == 2024])}")
print(f"       2025: {len(df_feriados[df_feriados['data'].dt.year == 2025])}")

# Salvar
BASE_DIR = Path(r"C:\Users\joao.barbosa\Desktop\Codigos\Codigos ONS\mini_dessem")
OUTPUT_DIR = BASE_DIR / "Data" / "auxiliares"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

output_path = OUTPUT_DIR / "feriados_nacionais_brasil.csv"
df_feriados.to_csv(output_path, index=False)

print(f"\n[OK] Feriados salvos em: {output_path}")

# Mostrar lista
print("\n" + "="*100)
print("  FERIADOS NACIONAIS BRASILEIROS (2023-2025)")
print("="*100)
print(f"\n{'Data':^12} | {'Dia Semana':^12} | {'Nome':^40}")
print("-"*70)
for _, row in df_feriados.iterrows():
    dia_semana = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'][row['data'].dayofweek]
    print(f"{row['data'].strftime('%Y-%m-%d'):^12} | {dia_semana:^12} | {row['nome']:<40}")

print("\n" + "="*100)





