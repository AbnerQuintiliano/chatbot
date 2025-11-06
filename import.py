import pandas as pd

def ler_arquivo_inmet(caminho):
    # Lê as 8 primeiras linhas de metadados
    with open(caminho, 'r', encoding='latin-1') as f:
        linhas = [next(f).strip() for _ in range(8)]

    # Extrai os metadados (antes do :)
    meta_desejada = ["REGIAO", "UF", "ESTACAO"]
    meta = {}
    for linha in linhas:
        if ":" in linha:
            chave, valor = linha.split(";", 1)
            chave = chave.split(":")[0].strip().replace(" ", "_").upper()
            if chave in meta_desejada:
                valor = valor.replace(";", "").strip()
                meta[chave] = valor

    # Agora lê o resto do CSV (a partir da linha 9)
    df = pd.read_csv(
        caminho,
        sep=';',
        skiprows=8,
        encoding='latin-1',
        na_values=['', '-', 'null', 'NaN']
    )

    # Corrige separador decimal (vírgula -> ponto)
    df = df.apply(lambda col: col.str.replace(',', '.', regex=False)
                  if col.dtype == 'object' else col)
    
    df['FALTANDO_DADO'] = df.isna().any(axis=1)

    # Adiciona os metadados como colunas
    for k, v in meta.items():
        print(f"  {k}: {v}")
        df[k] = v

    return df

import glob

arquivos = glob.glob("C:/Users/Abner/Downloads/2024/*.csv")

df_total = pd.concat([ler_arquivo_inmet(arq) for arq in arquivos], ignore_index=True)
df_total.to_csv("dados.csv", index=False, encoding='utf-8')