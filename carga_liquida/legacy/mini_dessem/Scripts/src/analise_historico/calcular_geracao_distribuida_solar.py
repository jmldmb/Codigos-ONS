"""
Cálculo de Geração Solar Distribuída
=====================================

Separa a geração solar total (BALANCO_ENERGIA) em:
- Centralizada pós-curtailment (do CSV de curtailment)
- Distribuída pós-curtailment (calculada por diferença)

Período: 2024-04 até 2025-10

Autor: ONS
Data: Novembro 2024
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from datetime import datetime

# Configurar encoding
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def carregar_balanco_energia(anos=[2024, 2025]):
    """Carrega dados totais de geração solar do BALANCO_ENERGIA."""
    
    print("="*90)
    print("  FASE 1: Carregar Dados de BALANCO_ENERGIA (Total)")
    print("="*90)
    
    base_dir = Path(__file__).parent.parent
    
    dfs = []
    
    for ano in anos:
        xlsx_path = base_dir / "Data" / "raw_data" / f"BALANCO_ENERGIA_SUBSISTEMA_{ano}.xlsx"
        
        if not xlsx_path.exists():
            print(f"\n[AVISO] Arquivo nao encontrado: {xlsx_path}")
            continue
        
        print(f"\nCarregando {ano}...")
        df = pd.read_excel(xlsx_path, sheet_name=0)
        
        # Filtrar SIN
        id_col = None
        for cand in ['id_subsistema', 'id_subsistena', 'nom_subsistema']:
            if cand in df.columns:
                id_col = cand
                break
        
        if id_col:
            df[id_col] = df[id_col].astype(str).str.upper().str.strip()
            df = df[df[id_col] == 'SIN'].copy()
        
        df['din_instante'] = pd.to_datetime(df['din_instante'], errors='coerce')
        df = df.dropna(subset=['din_instante'])
        
        df['ano'] = df['din_instante'].dt.year
        df['mes'] = df['din_instante'].dt.month
        df['dia'] = df['din_instante'].dt.day
        df['hora'] = df['din_instante'].dt.hour
        df['ano_mes'] = df['din_instante'].dt.to_period('M')
        
        df['val_gersolar'] = pd.to_numeric(df['val_gersolar'], errors='coerce')
        
        dfs.append(df)
        print(f"  [OK] {len(df):,} registros")
    
    if not dfs:
        raise ValueError("Nenhum arquivo BALANCO_ENERGIA encontrado!")
    
    df_total = pd.concat(dfs, ignore_index=True)
    df_total = df_total.sort_values(['ano', 'mes', 'dia', 'hora']).reset_index(drop=True)
    
    print(f"\n[OK] Total: {len(df_total):,} registros")
    print(f"     Periodo: {df_total['din_instante'].min()} ate {df_total['din_instante'].max()}")
    
    return df_total


def carregar_centralizada_csv():
    """Carrega dados de geração centralizada pós-curtailment do CSV."""
    
    print("\n" + "="*90)
    print("  FASE 2: Carregar Dados de Centralizada (CSV Curtailment)")
    print("="*90)
    
    csv_path = Path(__file__).parent.parent / "output" / "curtailment" / "solar" / "comparacao_perfil_curtailment" / "por_mes" / "perfil_hora_por_mes.csv"
    
    print(f"\nCarregando: {csv_path.name}")
    
    df_csv = pd.read_csv(csv_path)
    df_csv['mes'] = pd.to_datetime(df_csv['mes'])
    df_csv['ano_mes'] = df_csv['mes'].dt.to_period('M')
    df_csv['ano'] = df_csv['mes'].dt.year
    df_csv['mes_num'] = df_csv['mes'].dt.month
    
    print(f"  [OK] {len(df_csv):,} registros")
    print(f"     Periodo: {df_csv['mes'].min()} ate {df_csv['mes'].max()}")
    print(f"     Colunas: {df_csv.columns.tolist()}")
    
    return df_csv


def calcular_distribuida(df_balanco, df_centralizada):
    """Calcula geração distribuída por diferença."""
    
    print("\n" + "="*90)
    print("  FASE 3: Calcular Geração Distribuída (Total - Centralizada)")
    print("="*90)
    
    # Agregar balanco por ano_mes e hora
    print("\nAgregando BALANCO_ENERGIA por mes e hora...")
    df_bal_agg = df_balanco.groupby(['ano_mes', 'hora'])['val_gersolar'].mean().reset_index()
    df_bal_agg.columns = ['ano_mes', 'hora', 'total_mw']
    
    print(f"  [OK] {len(df_bal_agg):,} registros agregados")
    
    # Preparar centralizada
    print("\nPreparando dados de centralizada...")
    df_cent = df_centralizada[['ano_mes', 'hora', 'geracao_mwh_media']].copy()
    df_cent.columns = ['ano_mes', 'hora', 'centralizada_mw']
    
    # Merge
    print("\nCombinando dados...")
    df_combined = pd.merge(df_bal_agg, df_cent, on=['ano_mes', 'hora'], how='inner')
    
    print(f"  [OK] {len(df_combined):,} registros combinados")
    
    # Calcular distribuída
    print("\nCalculando geracao distribuida = total - centralizada...")
    df_combined['distribuida_mw'] = df_combined['total_mw'] - df_combined['centralizada_mw']
    
    # Validar
    negativos = (df_combined['distribuida_mw'] < 0).sum()
    
    if negativos > 0:
        print(f"\n[AVISO] {negativos} registros com distribuida negativa!")
        print("        Ajustando para zero...")
        df_combined.loc[df_combined['distribuida_mw'] < 0, 'distribuida_mw'] = 0
    
    # Adicionar metadados
    df_combined['ano'] = df_combined['ano_mes'].dt.year
    df_combined['mes'] = df_combined['ano_mes'].dt.month
    
    # Estatísticas
    print("\n" + "-"*90)
    print("  Estatisticas Gerais")
    print("-"*90)
    
    print(f"\nMedia Total:        {df_combined['total_mw'].mean():>12,.0f} MW")
    print(f"Media Centralizada: {df_combined['centralizada_mw'].mean():>12,.0f} MW ({(df_combined['centralizada_mw'].mean()/df_combined['total_mw'].mean()*100):.1f}%)")
    print(f"Media Distribuida:  {df_combined['distribuida_mw'].mean():>12,.0f} MW ({(df_combined['distribuida_mw'].mean()/df_combined['total_mw'].mean()*100):.1f}%)")
    
    return df_combined


def calcular_perfis_horarios(df_combined):
    """Calcula perfis horários proporcionais por mês."""
    
    print("\n" + "="*90)
    print("  FASE 4: Calcular Perfis Horários por Mês")
    print("="*90)
    
    perfis_centralizada = {}
    perfis_distribuida = {}
    medias_mensais = {}
    
    meses_unicos = sorted(df_combined['ano_mes'].unique())
    
    print(f"\nProcessando {len(meses_unicos)} meses...")
    
    for ano_mes in meses_unicos:
        df_mes = df_combined[df_combined['ano_mes'] == ano_mes].copy()
        
        ano = df_mes['ano'].iloc[0]
        mes = df_mes['mes'].iloc[0]
        
        # Média por hora
        cent_por_hora = df_mes.groupby('hora')['centralizada_mw'].mean()
        dist_por_hora = df_mes.groupby('hora')['distribuida_mw'].mean()
        total_por_hora = df_mes.groupby('hora')['total_mw'].mean()
        
        # Totais diários (soma das 24h)
        total_cent_dia = cent_por_hora.sum()
        total_dist_dia = dist_por_hora.sum()
        total_dia = total_por_hora.sum()
        
        # Perfis proporcionais
        if total_cent_dia > 0:
            perfil_prop_cent = (cent_por_hora / total_cent_dia).to_dict()
        else:
            perfil_prop_cent = {h: 0.0 for h in range(24)}
        
        if total_dist_dia > 0:
            perfil_prop_dist = (dist_por_hora / total_dist_dia).to_dict()
        else:
            perfil_prop_dist = {h: 0.0 for h in range(24)}
        
        # Armazenar
        perfis_centralizada[str(ano_mes)] = {
            'ano': ano,
            'mes': mes,
            'nome_mes': pd.Timestamp(ano, mes, 1).strftime('%B'),
            'perfil_proporcional': {int(h): float(v) for h, v in perfil_prop_cent.items()},
            'perfil_absoluto_mw': {int(h): float(v) for h, v in cent_por_hora.items()},
            'total_diario_mwh': float(total_cent_dia),
            'media_mw': float(cent_por_hora.mean())
        }
        
        perfis_distribuida[str(ano_mes)] = {
            'ano': ano,
            'mes': mes,
            'nome_mes': pd.Timestamp(ano, mes, 1).strftime('%B'),
            'perfil_proporcional': {int(h): float(v) for h, v in perfil_prop_dist.items()},
            'perfil_absoluto_mw': {int(h): float(v) for h, v in dist_por_hora.items()},
            'total_diario_mwh': float(total_dist_dia),
            'media_mw': float(dist_por_hora.mean())
        }
        
        medias_mensais[str(ano_mes)] = {
            'ano': int(ano),
            'mes': int(mes),
            'total_mw': float(total_por_hora.mean()),
            'centralizada_mw': float(cent_por_hora.mean()),
            'distribuida_mw': float(dist_por_hora.mean()),
            'pct_centralizada': float((cent_por_hora.mean() / total_por_hora.mean()) * 100) if total_por_hora.mean() > 0 else 0.0,
            'pct_distribuida': float((dist_por_hora.mean() / total_por_hora.mean()) * 100) if total_por_hora.mean() > 0 else 0.0
        }
        
        print(f"  {ano}-{mes:02d}: Total={total_por_hora.mean():>8,.0f} MW "
              f"| Cent={cent_por_hora.mean():>8,.0f} MW ({medias_mensais[str(ano_mes)]['pct_centralizada']:.1f}%) "
              f"| Dist={dist_por_hora.mean():>8,.0f} MW ({medias_mensais[str(ano_mes)]['pct_distribuida']:.1f}%)")
    
    return perfis_centralizada, perfis_distribuida, medias_mensais


def agregar_perfis_por_mes_numero(perfis_dict):
    """Agrega perfis por número do mês (média de todos os anos disponíveis)."""
    
    print("\nAgregando perfis por mes (media de anos disponiveis)...")
    
    perfis_agregados = {}
    
    for mes_num in range(1, 13):
        # Buscar todos os registros deste mês
        dados_mes = []
        
        for ano_mes_str, dados in perfis_dict.items():
            if dados['mes'] == mes_num:
                dados_mes.append(dados)
        
        if not dados_mes:
            print(f"  Mes {mes_num:02d}: Sem dados (sera interpolado depois)")
            continue
        
        # Calcular perfil médio
        perfil_medio = {}
        perfil_absoluto_medio = {}
        
        for hora in range(24):
            props = [d['perfil_proporcional'][hora] for d in dados_mes if hora in d['perfil_proporcional']]
            absolutos = [d['perfil_absoluto_mw'][hora] for d in dados_mes if hora in d['perfil_absoluto_mw']]
            
            perfil_medio[hora] = float(np.mean(props)) if props else 0.0
            perfil_absoluto_medio[hora] = float(np.mean(absolutos)) if absolutos else 0.0
        
        # Renormalizar perfil proporcional
        soma_prop = sum(perfil_medio.values())
        if soma_prop > 0:
            perfil_medio = {h: v/soma_prop for h, v in perfil_medio.items()}
        
        total_diario = sum(perfil_absoluto_medio.values())
        media_mw = total_diario / 24 if total_diario > 0 else 0
        
        perfis_agregados[mes_num] = {
            'mes': mes_num,
            'nome_mes': dados_mes[0]['nome_mes'],
            'n_observacoes': len(dados_mes),
            'perfil_proporcional': perfil_medio,
            'perfil_absoluto_mw': perfil_absoluto_medio,
            'total_diario_mwh': float(total_diario),
            'media_mw': float(media_mw),
            'interpolado': False
        }
        
        print(f"  Mes {mes_num:02d} ({perfis_agregados[mes_num]['nome_mes']:>9s}): "
              f"{len(dados_mes)} observacoes, media={media_mw:>8,.0f} MW")
    
    return perfis_agregados


def interpolar_meses_faltantes(perfis_agregados):
    """Interpola meses sem dados usando vizinhos."""
    
    meses_com_dados = sorted(perfis_agregados.keys())
    
    if len(meses_com_dados) == 12:
        print("\n  [OK] Todos os 12 meses tem dados!")
        return perfis_agregados
    
    print(f"\n  Interpolando {12 - len(meses_com_dados)} meses faltantes...")
    
    for mes_num in range(1, 13):
        if mes_num in perfis_agregados:
            continue
        
        # Encontrar vizinhos
        mes_antes = max([m for m in meses_com_dados if m < mes_num], default=None)
        mes_depois = min([m for m in meses_com_dados if m > mes_num], default=None)
        
        # Interpolação circular (dezembro -> janeiro)
        if mes_antes is None:
            mes_antes = max(meses_com_dados)
        if mes_depois is None:
            mes_depois = min(meses_com_dados)
        
        # Pesos para interpolação
        if mes_antes < mes_depois:
            dist_total = mes_depois - mes_antes
            peso_antes = (mes_depois - mes_num) / dist_total
            peso_depois = (mes_num - mes_antes) / dist_total
        else:
            # Caso circular
            peso_antes = 0.5
            peso_depois = 0.5
        
        # Interpolar perfil
        perfil_interp = {}
        perfil_abs_interp = {}
        
        for hora in range(24):
            val_antes = perfis_agregados[mes_antes]['perfil_proporcional'][hora]
            val_depois = perfis_agregados[mes_depois]['perfil_proporcional'][hora]
            perfil_interp[hora] = peso_antes * val_antes + peso_depois * val_depois
            
            abs_antes = perfis_agregados[mes_antes]['perfil_absoluto_mw'][hora]
            abs_depois = perfis_agregados[mes_depois]['perfil_absoluto_mw'][hora]
            perfil_abs_interp[hora] = peso_antes * abs_antes + peso_depois * abs_depois
        
        # Renormalizar
        soma_prop = sum(perfil_interp.values())
        if soma_prop > 0:
            perfil_interp = {h: v/soma_prop for h, v in perfil_interp.items()}
        
        total_diario = sum(perfil_abs_interp.values())
        
        perfis_agregados[mes_num] = {
            'mes': mes_num,
            'nome_mes': pd.Timestamp(2024, mes_num, 1).strftime('%B'),
            'n_observacoes': 0,
            'perfil_proporcional': perfil_interp,
            'perfil_absoluto_mw': perfil_abs_interp,
            'total_diario_mwh': float(total_diario),
            'media_mw': float(total_diario / 24),
            'interpolado': True,
            'interpolado_de': f"{mes_antes}-{mes_depois}"
        }
        
        print(f"  Mes {mes_num:02d} interpolado de {mes_antes:02d} e {mes_depois:02d}")
    
    return perfis_agregados


def salvar_resultados(df_combined, perfis_centralizada, perfis_distribuida, medias_mensais):
    """Salva todos os resultados."""
    
    print("\n" + "="*90)
    print("  FASE 5: Salvar Resultados")
    print("="*90)
    
    output_dir = Path(__file__).parent.parent / "output" / "sample" / "solar_distribuida"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. CSV detalhado
    csv_path = output_dir / "geracao_distribuida_2024_2025.csv"
    print(f"\n[1/4] Salvando CSV detalhado...")
    print(f"      {csv_path.name}")
    
    df_combined.to_csv(csv_path, index=False)
    print(f"      [OK] {len(df_combined):,} registros")
    
    # 2. Perfis agregados centralizada
    perfis_cent_agregados = agregar_perfis_por_mes_numero(perfis_centralizada)
    perfis_cent_agregados = interpolar_meses_faltantes(perfis_cent_agregados)
    
    json_cent_path = output_dir / "perfis_horarios_centralizada.json"
    print(f"\n[2/4] Salvando perfis centralizados...")
    print(f"      {json_cent_path.name}")
    
    # Converter chaves para string
    perfis_cent_json = {str(k): v for k, v in perfis_cent_agregados.items()}
    
    with open(json_cent_path, 'w', encoding='utf-8') as f:
        json.dump(perfis_cent_json, f, indent=2, ensure_ascii=False)
    
    print(f"      [OK] {len(perfis_cent_json)} meses")
    
    # 3. Perfis agregados distribuída
    perfis_dist_agregados = agregar_perfis_por_mes_numero(perfis_distribuida)
    perfis_dist_agregados = interpolar_meses_faltantes(perfis_dist_agregados)
    
    json_dist_path = output_dir / "perfis_horarios_distribuida.json"
    print(f"\n[3/4] Salvando perfis distribuidos...")
    print(f"      {json_dist_path.name}")
    
    perfis_dist_json = {str(k): v for k, v in perfis_dist_agregados.items()}
    
    with open(json_dist_path, 'w', encoding='utf-8') as f:
        json.dump(perfis_dist_json, f, indent=2, ensure_ascii=False)
    
    print(f"      [OK] {len(perfis_dist_json)} meses")
    
    # 4. Médias mensais para data.py
    medias_path = output_dir / "medias_mensais_para_data_py.json"
    print(f"\n[4/4] Salvando medias mensais (para data.py)...")
    print(f"      {medias_path.name}")
    
    with open(medias_path, 'w', encoding='utf-8') as f:
        json.dump(medias_mensais, f, indent=2, ensure_ascii=False)
    
    print(f"      [OK] {len(medias_mensais)} registros")
    
    print("\n" + "="*90)
    print("  ARQUIVOS SALVOS EM:")
    print("="*90)
    print(f"\n  {output_dir}")
    print(f"    ├─ geracao_distribuida_2024_2025.csv")
    print(f"    ├─ perfis_horarios_centralizada.json")
    print(f"    ├─ perfis_horarios_distribuida.json")
    print(f"    └─ medias_mensais_para_data_py.json")
    
    return output_dir


def main():
    print("\n" + "="*90)
    print("  CALCULO DE GERACAO SOLAR DISTRIBUIDA")
    print("  Total (BALANCO) - Centralizada (CSV) = Distribuida")
    print("="*90)
    
    try:
        # Carregar dados
        df_balanco = carregar_balanco_energia([2024, 2025])
        df_centralizada = carregar_centralizada_csv()
        
        # Calcular distribuída
        df_combined = calcular_distribuida(df_balanco, df_centralizada)
        
        # Calcular perfis
        perfis_cent, perfis_dist, medias = calcular_perfis_horarios(df_combined)
        
        # Salvar
        output_dir = salvar_resultados(df_combined, perfis_cent, perfis_dist, medias)
        
        # Resumo final
        print("\n" + "="*90)
        print("  CALCULO CONCLUIDO COM SUCESSO!")
        print("="*90)
        
        print("\nProximos passos:")
        print("  1. Revisar arquivos gerados em:")
        print(f"     {output_dir}")
        print("  2. Comparar perfis centralizada vs distribuida")
        print("  3. Atualizar data.py com novos dicionarios")
        print("  4. Criar sampler para distribuida")
        
        return 0
        
    except Exception as e:
        print(f"\n[ERRO] {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())

