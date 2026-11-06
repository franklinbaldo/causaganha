import os
import sys
import time
import json
import socket
import torch

# 1. Bloqueio estrito de rede em nivel de sistema operacional / processo
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HTTP_PROXY"] = "http://127.0.0.1:9999"
os.environ["HTTPS_PROXY"] = "http://127.0.0.1:9999"
os.environ["THX02_CPU_DTYPE"] = "bfloat16"
os.environ["THX02_DEVICE"] = "cpu"

# Bloqueio total no socket do Python para provar execucao 100% offline
orig_connect = socket.socket.connect
def blocked_connect(self, address):
    raise RuntimeError(f"PROVA DE ISOLAMENTO: Tentativa de conexao bloqueada para {address}")
socket.socket.connect = blocked_connect

sys.modules.setdefault("fla", None)

from thx02 import THX02

checkpoint_path = r"C:\Users\76450694220\.cache\huggingface\hub\models--HAL-X-AI--THX-02\snapshots\8262da06636501d98a060edf8d81b4c1b1eea46a"

print("=" * 60)
print("[PROVA OFFLINE] Executando com rede COMPLETAMENTE BLOQUEADA")
print("=" * 60)

t0 = time.time()
m = THX02.load(checkpoint_path, device="cpu")
print(f"Modelo carregado OFFLINE com sucesso em {time.time() - t0:.2f}s!")

texto_sentenca = "SENTENÇA. O autor pediu a restituição de valores. Ante o exposto, JULGO PROCEDENTE o pedido inicial, integralmente, com resolução do mérito."

questions = {
    "resultado": {
        "type": "choice",
        "instructions": "Qual é o resultado da decisão?",
        "criteria": {
            "procedente": "Julga procedente o pedido inicial",
            "improcedente": "Julga improcedente o pedido inicial",
            "parcialmente_procedente": "Julga parcialmente procedente o pedido",
            "desconhecido": "Resultado desconhecido ou outro"
        }
    },
    "tipo_decisao": {
        "type": "choice",
        "instructions": "Qual é o tipo de decisão?",
        "criteria": {
            "sentenca": "Sentença",
            "acordao": "Acórdão",
            "decisao_monocratica": "Decisão monocrática",
            "despacho": "Despacho ou outro provimento"
        }
    },
    "polo_vencedor": {
        "type": "choice",
        "instructions": "Qual polo venceu a demanda?",
        "criteria": {
            "ativo": "Polo ativo / autor",
            "passivo": "Polo passivo / réu",
            "nenhum": "Nenhum ou ambos parcialmente",
            "desconhecido": "Não informado ou inconclusivo"
        }
    }
}

t_inf0 = time.time()
res = m.decide(state=texto_sentenca, questions=questions, think=False, tta=1)
print(f"Inferencia OFFLINE concluida em {time.time() - t_inf0:.2f}s!")
print("\nResultado:")
print(json.dumps(res, indent=2, ensure_ascii=False))
