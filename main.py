from typing import Optional
import os
import pandas as pd # pyright: ignore[reportMissingModuleSource]
from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from google.genai import Client
import json
from dotenv import load_dotenv  # type: ignore
import csv

load_dotenv()

app = FastAPI(title="API de IA - Análise de sentimento")

class Mensagem(BaseModel):
    texto: str

class Comentario(BaseModel):
    comentario: str

def get_api_key() -> str:
    chave = os.getenv("GEMINI_API_KEY")
    if not chave:
        raise Exception("A conexão com o Gemini não foi concluída. Verifique seu .env.")
    return chave

def get_client() -> Client:
    key = get_api_key()
    return Client(api_key=key)

print("Chave lida:", os.getenv("GEMINI_API_KEY"))

@app.get("/")
def root():
    return {"message": "API funcionando"}

@app.post("/mensagem")
def receber_mensagem(msg: Mensagem):
    try:
        client = get_client()

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=msg.texto
        )

        return {"resposta": response.text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao chamar Gemini: {e}")

@app.post("/sentimento")
def analisar_sentimento(data: Comentario):

    prompt = f"""
    Você é um analisador de sentimento de atendimento ao cliente.
    RETORNE APENAS JSON PURO. NADA ALÉM DE JSON.
    
    Analise o comentário abaixo:
    "{data.comentario}"

    Formato obrigatório:
    {{
        "sentimento": "positivo|negativo|neutro",
        "justificativa": "1 frase explicando",
        "possiveis_causas": ["causa1", "causa2"],
        "recomendado": "ação prática"
    }}
    """

    try:
        client = get_client()
        resposta = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        texto = resposta.text.strip()

        if texto.startswith("```"):
            texto = texto.strip("`")
            texto = texto.replace("json", "", 1).strip()

        saida = json.loads(texto)
        return saida

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"O Gemini não retornou JSON válido. Resposta recebida: {texto}"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao chamar Gemini: {e}"
        )
    
def carregar_csv(caminho: str):
    comentarios = []
    try:
        with open(caminho, "r", encoding="utf-8") as arquivo:
            leitor = csv.DictReader(arquivo)
            for linha in leitor:
                comentarios.append(linha["comentario"])
        return comentarios
    except Exception as e:
        raise Exception(f"Erro ao carrear CSV: {e}")

"""@app.get("/testar_csv")
def testar_csv():
        try:
            dados = carregar_csv("comentarios.csv")
            return {
                "quantidade": len(dados), 
                "exemplo_primeiros_5": dados[:5]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
"""   

@app.post("/analisar_csv")
def analisar_csv(file: UploadFile= File(...)):
    try:
        df = pd.read_csv(file.file)
        resultados=[]

        client = get_client()

        for comentario in df["comentario"]:
            prompt = f"""
            Você é um analisador de sentimento especializado em atendimento ao cliente.
            Analise o seguinte comentario: "{comentario}"
            Responda APENAS no formato JSON abaixo:
            {{
            "sentimento": "<positivo|negativo|neutro>",
            "justificativa": "<explique em 1 frase>",
            "possiveis_causas": ["causa1", "causa2"],
            "recomendado": "<ação prática>"
            }}
            """

            resposta = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt
            )

            try:
                data = json.loads(resposta.text)
            except:
                data = {
                    "sentimento": "erro",
                    "justificativa": "IA retornou JSON inválido",
                    "possiveis_causas": [],
                    "recomendado": ""
                }

                resultados.append({"comentario": comentario, **data
                                   })
        return {"total_analisados": len(resultados), "resultados_exemplo": resultados[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar CSV: {e}")
