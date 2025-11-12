
import pandas as pd
import ollama
from textwrap import dedent
import json
import operator

import unicodedata
def remover_acentos(texto):
    if isinstance(texto, str):
        nfkd = unicodedata.normalize('NFD', texto)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return texto

def FilterData(info: dict, df):
    data_str = info["data"].strip()
    if not data_str or not isinstance(data_str, str):
        return df

    data_str = data_str.strip()

    try:
        if " - " in data_str:
            data_inicio_str, data_fim_str = data_str.split(" - ")
            data_inicio = pd.to_datetime(data_inicio_str.strip(), dayfirst=True, errors="coerce")
            data_fim = pd.to_datetime(data_fim_str.strip(), dayfirst=True, errors="coerce")
        else:
            data_inicio = pd.to_datetime(data_str, dayfirst=True, errors="coerce")
            data_fim = data_inicio
    except Exception:
        return df

    if pd.isna(data_inicio) or pd.isna(data_fim):
        return df

    data_str = info["data"].strip()
    if " - " in data_str:
        data_inicio_str, data_fim_str = data_str.split(" - ")
        data_inicio = pd.to_datetime(data_inicio_str, dayfirst=True)
        data_fim = pd.to_datetime(data_fim_str, dayfirst=True)
    else:
        data_inicio = pd.to_datetime(data_str, dayfirst=True)
        data_fim = data_inicio  # mesma data

    df["Data"] = pd.to_datetime(df["Data"], format="%Y/%m/%d", errors="coerce")

    df_filtrado = df[df["Data"].between(data_inicio, data_fim)]

    return df_filtrado

def aplicar_filtros(df: pd.DataFrame, filtros: list) -> pd.DataFrame:
    ops = {
        "==": operator.eq,
        "=": operator.eq,
        ">": operator.gt,
        ">=": operator.ge,
        "<": operator.lt,
        "<=": operator.le
    }

    filtro_total = pd.Series(True, index=df.index)
    if not isinstance(filtros, list):
        return "Houveu m problema, poderia pergunta novamente?"
    for filtro in filtros:
        coluna, op, valor = filtro
        if coluna not in df.columns:
            print(f"Aviso: coluna '{coluna}' não encontrada no DataFrame.")
            continue
        if op not in ops:
            print(f"Aviso: operador '{op}' inválido. Pulando filtro.")
            continue

        try:
            filtro_coluna = ops[op](df[coluna], valor)
        except Exception as e:
            print(f"Erro ao aplicar filtro {coluna} {op} {valor}: {e}")
            continue

        filtro_total &= filtro_coluna

    return df[filtro_total]

mensagem = dedent("""
    não se preocupe em trazer as informações da pergunta, apenas saber o que está sendo perguntado pelo usuário,
    precisa que tire as seguintes informações: data, informação que deseja pegar, local (cidade / região).
    Caso na pergunta não tenha essas informações traga uma string vazia "" ou seja caso não seja expecificado data traga ""
    
    pode conter tambem um filtro para um campo ex: caso queira pegar informações onde teve temperatura do ar maior que 32
    nesse caso teve ser incorporado no json:
    {
        filtro: [["TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)", >,32]]
    }
    1- indica qual campo, 2- indica se e maior (ou maior ou igual), menor (ou menor ou igual)  e igual, 3- o valor
    para filtro pode ter o campo "Hora UTC" sendo colocado sempre no valor inteiro da hora ex : 1200 que é 12:00
    
    retorno deve ser sempre em um json com: 
    região (UF - ex: SP), 
    cidade,
    data (caso seja um espaço de tempo usar uma string com - entre as datas. E sempre formate em dd/mm/aaaa), 
    informações requeridas
    informações requeridas classifique em: 
    "PRECIPITAÇÃO TOTAL, HORÁRIO (mm)"
    PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO
    "HORARIA (mB),PRESSÃO ATMOSFERICA MAX.NA HORA ANT. (AUT) (mB)"
    PRESSÃO ATMOSFERICA MIN. NA HORA ANT. (AUT) (mB)
    RADIACAO GLOBAL (Kj/m²)
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)"
    TEMPERATURA DO PONTO DE ORVALHO (°C)
    TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)
    TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C)
    TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT) (°C)
    TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT) (°C)
    "UMIDADE RELATIVA DO AR, HORARIA (%)"
    UMIDADE REL. MAX. NA HORA ANT. (AUT) (%)
    UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)
    "VENTO, VELOCIDADE HORARIA (m/s)"
    "VENTO, DIREÇÃO HORARIA (gr) (° (gr))"
    "VENTO, RAJADA MAXIMA (m/s)"
                  
    (Sua função e apenas interpretar a pergunta, não responde-la)
    exemplo:
    {
        "regiao": "SP",
        "cidade": "São Paulo",
        "data": "",
        "informacoes_requeridas": [
          "PRECIPITAÇÃO TOTAL",
          "VENTO, VELOCIDADE HORARIA (m/s)",
          "VENTO, DIREÇÃO HORARIA (gr) (° (gr))"
        ]
        filtro: [
                  ["TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)", >,32],
                  ["VENTO, RAJADA MAXIMA (m/s)", "==", 2]
                ]
    }
""")

def chat():
    pergunta = input("Digite sua pergunta: ")
    resposta = ollama.chat(
        model="gemma3:4b",
         messages=[
            {
                "role": "system", 
                "content": mensagem},
            {"role": "user", "content": pergunta}
        ]
    )

    print(resposta["message"]["content"])
    df = pd.read_csv("dados.csv", sep=",")

    info = resposta["message"]["content"]
    info = info.strip("` \n")
    if info.startswith("json"):
        info = info[4:].strip()   

    info = json.loads(info)

    df_filtrado = FilterData(info, df)

    filtro_cidade = df_filtrado["ESTACAO"].str.contains(
        remover_acentos(info["cidade"]), case=False, na=False
    )

    filtro_uf = df_filtrado["UF"].str.contains(
        remover_acentos(info["regiao"]), case=False, na=False
    )
    df_filtrado = aplicar_filtros(df_filtrado.loc[filtro_cidade & filtro_uf], info["filtro"])
    if not isinstance(df_filtrado, pd.DataFrame):
        print(df_filtrado)
        return

    colunas_desejadas = [c.strip().lower() for c in info["informacoes_requeridas"]]

    colunas_csv = ["Data", "Hora UTC", "ESTACAO", "UF"] + [c for c in df.columns if any(req in c.lower() for req in colunas_desejadas)]

    resultado = df_filtrado[colunas_csv]
    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_colwidth", None)
    print(resultado)

while True:
    chat()