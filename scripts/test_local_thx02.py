import os
import sys
import time
import json
import torch

# Força execucao em CPU com bfloat16 para caber na RAM (15.35 GB)
os.environ["THX02_CPU_DTYPE"] = "bfloat16"
os.environ["THX02_DEVICE"] = "cpu"

# Garante fallback de linear attention sem triton/GPU
sys.modules.setdefault("fla", None)

from thx02 import THX02

checkpoint_path = r"C:\Users\76450694220\.cache\huggingface\hub\models--HAL-X-AI--THX-02\snapshots\8262da06636501d98a060edf8d81b4c1b1eea46a"

print(f"[1] Iniciando carregamento do modelo a partir de: {checkpoint_path}")
print(f"    PyTorch version: {torch.__version__}")
print(f"    Device: cpu, Dtype: bfloat16")
print(f"    CPU threads: {torch.get_num_threads()}")

t0 = time.time()
m = THX02.load(checkpoint_path, device="cpu")
load_time = time.time() - t0
print(f"[2] Modelo carregado com sucesso em {load_time:.2f}s!")

# Sentenca minima do teste da Hand-off
texto_sentenca = "SENTENÇA. O autor pediu a restituição de valores. Ante o exposto, JULGO PROCEDENTE o pedido inicial, integralmente, com resolução do mérito."

# Perguntas conforme protocolo THX-02 / CausaGanha
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

print("\n[3] Executando inferencia local...")
t_inf0 = time.time()
res = m.decide(state=texto_sentenca, questions=questions, think=False, tta=1)
inf_time = time.time() - t_inf0
print(f"[4] Inferencia concluida em {inf_time:.2f}s!")
print("\n[5] Resposta integral do runtime:")
print(json.dumps(res, indent=2, ensure_ascii=False))
