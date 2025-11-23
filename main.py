from typing import Optional
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.genai import Client
import json
from dotenv import load_dotenv  # type: ignore

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

        # algumas respostas podem vir com ```json ... ```
        if texto.startswith("```"):
            texto = texto.strip("`")
            texto = texto.replace("json", "", 1).strip()

        # tenta decodificar o JSON
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