
import pandas as pd
import ollama
from textwrap import dedent
import json

import unicodedata
def remover_acentos(texto):
    if isinstance(texto, str):
        nfkd = unicodedata.normalize('NFD', texto)
        return ''.join([c for c in nfkd if not unicodedata.combining(c)])
    return texto

mensagem = dedent("""
    não se preocupe em trazer as informações da pergunta, apenas saber o que está sendo perguntado pelo usuário,
    precisa que tire as seguintes informações: data, informação que deseja pegar, local (cidade / região).
    Caso na pergunta não tenha essas informações traga uma string vazia ""
    retorno deve ser sempre em um json com: 
    região (UF - ex: SP), 
    cidade, 
    data (caso seja um espaço de tempo usar uma string com - entre as datas), 
    informações requeridas
    informações requeridas classifique em: 
    "PRECIPITAÇÃO TOTAL,HORÁRIO (mm)",
    PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO,
    "HORARIA (mB),PRESSÃO ATMOSFERICA MAX.NA HORA ANT. (AUT) (mB)",
    PRESSÃO ATMOSFERICA MIN. NA HORA ANT. (AUT) (mB),
    RADIACAO GLOBAL (Kj/m²),
    "TEMPERATURA DO AR - BULBO SECO, HORARIA (°C)",
    TEMPERATURA DO PONTO DE ORVALHO (°C),
    TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C),
    TEMPERATURA MÍNIMA NA HORA ANT. (AUT) (°C),
    TEMPERATURA ORVALHO MAX. NA HORA ANT. (AUT) (°C),
    TEMPERATURA ORVALHO MIN. NA HORA ANT. (AUT) (°C),
    "UMIDADE RELATIVA DO AR, HORARIA (%)",
    UMIDADE REL. MAX. NA HORA ANT. (AUT) (%),
    UMIDADE REL. MIN. NA HORA ANT. (AUT) (%),
    "VENTO, VELOCIDADE HORARIA (m/s)"
    "VENTO, DIREÇÃO HORARIA (gr) (° (gr))",
    "VENTO, RAJADA MAXIMA (m/s)"
                  
    (Sua função e apenas interpretar a pergunta, não responde-la)
    exemplo:
    {
        "regiao": "SP",
        "cidade": "São Paulo",
        "data": "02/11/2024 - 06/11/2024",
        "informacoes_requeridas": [
          "PRECIPITAÇÃO TOTAL",
          "VENTO, VELOCIDADE HORARIA (m/s)",
          "VENTO, DIREÇÃO HORARIA (gr) (° (gr))"
        ]
    }
""")

pergunta = "RJ no dia 02/11/2024? retorne todas as informações"
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

# Agora pode decodificar
info = json.loads(info)

data_str = info["data"].strip()
if " - " in data_str:
    data_inicio_str, data_fim_str = data_str.split(" - ")
    data_inicio = pd.to_datetime(data_inicio_str, dayfirst=True)
    data_fim = pd.to_datetime(data_fim_str, dayfirst=True)
else:
    data_inicio = pd.to_datetime(data_str, dayfirst=True)
    data_fim = data_inicio  # mesma data

df["Data"] = pd.to_datetime(df["Data"],  format="%Y/%m/%d", errors="coerce")


filtro = (
    (df["ESTACAO"].str.contains(remover_acentos(info["cidade"]), case=False, na=False)) &
    (df["Data"].between(data_inicio, data_fim))
)

df_filtrado = df.loc[filtro]

colunas_desejadas = [c.strip().lower() for c in info["informacoes_requeridas"]]

# Encontrar colunas que "batem" com o pedido
colunas_csv = ["Hora UTC", "ESTACAO"] + [c for c in df.columns if any(req in c.lower() for req in colunas_desejadas)]

# Montar resultado final
resultado = df_filtrado[["Data"] + colunas_csv]
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
pd.set_option("display.width", None)
pd.set_option("display.max_colwidth", None)
print(resultado)