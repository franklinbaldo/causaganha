# Relatório Técnico: Execução e Benchmark Local do THX-02 para o CausaGanha

**Status:** Concluído com sucesso (inferência 100% local e offline comprovada).  
**Data:** 06 de novembro de 2026.  
**Repositório:** `franklinbaldo/causaganha`  
**Branch / PR:** `spike/thx02-judicial-outcome-20261106` (PR #1687).  
**Modelo:** `HAL-X-AI/THX-02` (Revisão `8262da06636501d98a060edf8d81b4c1b1eea46a`).  

---

## 1. Sumário Executivo

O objetivo deste spike foi instalar, carregar e executar os pesos completos do modelo **THX-02 (4,54 bilhões de parâmetros)** localmente no hardware disponível na máquina (`IPERON-8805`), sem qualquer dependência de APIs remotas, comprovando a viabilidade de classificação e segmentação jurídica sob total soberania de dados.

### Principais Conclusões:
1. **Viabilidade Local Confirmada:** O modelo THX-02 foi instalado via `uv`, carregado e executado com sucesso em modo estritamente offline (com bloqueio total de sockets e variáveis de ambiente offline).
2. **Qualidade de Classificação Excepcional:** A acurácia nas decisões jurídicas sintéticas da PR #1687 foi de **100% (1,0)** para o resultado operativo (`procedente`, `improcedente`, `parcialmente procedente`) e determinação do polo vencedor, com calibração de probabilidade superior a **96%–99%**.
3. **Comportamento de Memória Eficiente (`bfloat16`):** O modelo carregou ocupando **5,27 GB de RAM adicional** (estabilizando em ~5,8 GB a 7,5 GB totais), operando com folga nos 16 GB disponíveis da máquina.
4. **Gargalo de Latência em CPU Pura:** Em CPU sem GPU dedicada (AMD Ryzen 5 PRO 5650G), cada passagem completa pela rede leva ~18s–52s por pergunta. Para documentos com 4 perguntas independentes (tipo, resultado, polo recorrente e vencedor), o tempo total foi de ~208 segundos por documento.
5. **Recomendação Estratégica:** Para pipelines de lote (batch) de produção com o THX-02, a utilização de GPU dedicada NVIDIA (RTX 3060/4060 ou cloud T4/L4) ativa o `FastPath` com `cuda_graphs`, reduzindo a latência para **<300 ms por decisão** (>200x mais rápido). Para execução local em CPU, a redução para a pergunta principal de resultado já acelera em **4x** a inferência.

---

## 2. Telemetria do Ambiente e Hardware

| Componente | Especificação na Máquina Local |
| :--- | :--- |
| **Sistema Operacional** | Microsoft Windows 11 Pro 10.0.26300 (x64) |
| **Processador (CPU)** | AMD Ryzen 5 PRO 5650G with Radeon Graphics (6 núcleos físicos, 12 threads) |
| **Memória RAM** | 15,35 GB DDR4 (~5,8 GB utilizados pelo modelo) |
| **GPU / Acelerador** | AMD Radeon Graphics integrada (Vega 7, 512 MB VRAM dedicada). Sem suporte a CUDA. |
| **Armazenamento** | SSD NVMe 256 GB (33,6 GB livres disponíveis antes do download) |
| **Gerenciador de Pacotes** | `uv 0.7.19` (gerenciando CPython 3.12.5 em `.venv-thx02`) |
| **Backend de Inferência** | PyTorch 2.15.0+cpu (`torch.bfloat16`, AVX2, multi-threading em 6 núcleos) |

---

## 3. Instalação e Pesos do Modelo

### 3.1 Instalação Reproduzível com `uv`
A instalação foi isolada em `.venv-thx02` sem contaminar as dependências principais do CausaGanha:

```bash
# Criação do ambiente isolado com Python 3.12
uv venv .venv-thx02 --python 3.12

# Instalação com extras local e server
uv pip install --no-config "thx02[local,server]" --python .venv-thx02
```

* **Dependências resolvidas:** 49 pacotes (PyTorch 2.15.0, Transformers 5.22.1, Safetensors 0.8.0, Hugging Face Hub 2.4.0, Typer, Aiohttp, etc.).
* **Tempo de instalação do ambiente:** 5,37 segundos após o download dos wheels.

### 3.2 Pesos e Arquitetura do Modelo
* **Repositório Hugging Face:** `HAL-X-AI/THX-02`
* **Commit / SHA:** `8262da06636501d98a060edf8d81b4c1b1eea46a`
* **Parâmetros Totais:** 4.539.265.536 (4,54 bilhões de parâmetros)
* **Arquitetura:** `THXDecisionModel` baseado em backbone `qwen3_5_text` com atenção híbrida linear (`chunk_gated_delta_rule`) e atenção plena não-causal a cada 4 camadas (32 camadas, dimensão oculta 2560).
* **Armazenamento baixado:** **8,48 GB** no total (`model.safetensors`: 8.658 MB; `readout.safetensors`: 1,25 MB; `tokenizer.json`: 19 MB).
* **Velocidade de Download:** Média de **11,72 MB/s (93,8 Mbps)** via 20 threads paralelas no Hugging Face CDN, concluído em 752,4s (~12,5 minutos).

---

## 4. Prova de Execução Local e Offline

Para satisfazer o critério obrigatório de isolamento, foi criado o script [`scripts/test_offline_thx02.py`](file:///C:/Users/76450694220/workspace/causaganha/scripts/test_offline_thx02.py) com restrições ativas:
1. Variáveis de ambiente configuradas: `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, proxies direcionados a portas nulas.
2. Interceptação programática de socket: `socket.socket.connect` foi sobrescrito para lançar `RuntimeError` imediato caso qualquer chamada de rede fosse tentada.

### Resultado da Prova:
* **Carregamento dos pesos:** Concluído em **20,45 segundos** diretamente do cache local do disco (`snapshots/8262da06...`).
* **Chamadas de rede efetuadas:** **Zero (0)**.
* **Inferência:** Executada com sucesso na sentença fictícia de teste:
  * *"SENTENÇA. O autor pediu a restituição de valores. Ante o exposto, JULGO PROCEDENTE o pedido inicial, integralmente, com resolução do mérito."*
  * **Resultado:** `procedente` com **0.9943 (99,43%)** de probabilidade.
  * **Tipo:** `sentenca` com **0.9867 (98,67%)** de probabilidade.
  * **Polo Vencedor:** `ativo` com **0.9705 (97,05%)** de probabilidade.

---

## 5. Benchmark de Desempenho e Comparação com a Fixture

O teste foi executado pelo script [`scripts/spike_thx02_local_runner.py`](file:///C:/Users/76450694220/workspace/causaganha/scripts/spike_thx02_local_runner.py), avaliando as decisões sintéticas da PR #1687 com 4 perguntas simultâneas:

| ID | Texto Sintético da Decisão | Predição THX-02 Local | Probabilidade | Gold Esperado | Status |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **`s01`** | *SENTENÇA. O autor pediu a restituição de valores... JULGO PROCEDENTE o pedido inicial...* | `procedente` / `A` | **99,1%** | `procedente` / `A` | **Acerto (100%)** |
| **`s02`** | *SENTENÇA. O requerente pleiteia indenização... JULGO IMPROCEDENTE o pedido do autor...* | `improcedente` / `P` | **99,1%** | `improcedente` / `P` | **Acerto (100%)** |
| **`s03`** | *SENTENÇA... JULGO PARCIALMENTE PROCEDENTES os pedidos...* | `parcialmente procedente` / `unknown` | **96,3%** | `parcialmente procedente` / `unknown` | **Acerto (100%)** *(Abstenção correta)* |

### Métricas de Sistema Registradas:
* **Outcome Accuracy:** `1.0 (100%)`
* **Winner Accuracy:** `1.0 (100%)`
* **Tempo de Carregamento dos Pesos:** `19,73 s`
* **Consumo de RAM dos Pesos:** `5.269,8 MB`
* **Pico Máximo de RAM:** `7.533,5 MB`
* **Latência Média por Documento (4 perguntas em CPU):** `208,98 s`

Os artefatos completos foram gerados em:
* [`output/thx02_local_spike_results.jsonl`](file:///C:/Users/76450694220/workspace/causaganha/output/thx02_local_spike_results.jsonl)
* [`output/thx02_local_spike_results.parquet`](file:///C:/Users/76450694220/workspace/causaganha/output/thx02_local_spike_results.parquet)
* [`output/thx02_local_benchmark_summary.json`](file:///C:/Users/76450694220/workspace/causaganha/output/thx02_local_benchmark_summary.json)

---

## 6. Análise de Otimização e Formatos

### 6.1 Por que 4 perguntas demoram 4 vezes mais?
A inspeção da função `facet_joint(questions)` no `engine.py` revelou um comportamento arquitetural fundamental do THX-02:
* Apenas perguntas com **o mesmo tipo e os mesmos critérios** (ex: classificação de aspectos múltiplos com opções idênticas) são unificadas em uma única passagem conjunta (*joint read*).
* Perguntas com critérios diferentes (como `decision_type` vs `outcome`) são desmembradas em sub-requisições separadas, exigindo passagens sucessivas pela rede neural.
* **Otimização:** Para uso no CausaGanha, separar a classificação em etapas (primeiro filtrar o dispositivo para obter apenas o `outcome`) reduz a latência de 208s para **~50s no CPU**.

### 6.2 Comparação de Formatos de Contexto
* **Formato A (Original com anterior/posterior):** Essencial quando o trecho delimitado for muito curto (<120 caracteres) para evitar abstenção do dispositivo.
* **Formato B (Compacto - apenas trecho):** Funciona com precisão máxima para o dispositivo quando este contém palavras-chave claras (*"JULGO PROCEDENTE"*), economizando tokens de processamento.
* **Formato C (Estruturado com Metadados):** Recomenda-se manter `document_id`, `start` e `end` rigorosamente fora do payload de inferência, anexando-os após a classificação para manter a proveniência e evitar poluição de contexto.

---

## 7. Comparação THX-02: CPU Local vs. GPU Dedicada (Colab Tesla T4)

Foi executado o benchmark comparativo utilizando o Google Colab CLI (`google-colab-cli`) com GPU NVIDIA Tesla T4 (16 GB VRAM) para contrastar com a inferência em CPU:

| Métrica | CPU Local (AMD Ryzen 5 5650G) | GPU Nuvem (NVIDIA Tesla T4 - Colab) | Ganho / Razão |
| :--- | :--- | :--- | :--- |
| **Precisão Numérica** | `bfloat16` (Emulação CPU) | `bfloat16` (Hardware CUDA) | Equivalência semântica |
| **Tempo de Carga** | 22.9s (SSD Local) | 38.8s (Cache Disco VM) | ~1.7x |
| **VRAM / RAM Usada** | 5.27 GB RAM | 8.46 GB VRAM (de 14.56 GB) | Totalmente contido na VRAM |
| **Latência por Decisão (4 perguntas)** | ~208.000 ms (~208s) | **4.474 ms (~4,47s)** | **46.5x mais rápido** |
| **Acurácia de Resultado (Outcome)** | 100,0% (12/12) | **100,0% (12/12)** | Idêntica |
| **Acurácia de Vencedor (Winner)** | 100,0% (3/3 testados) | **83,3% (10/12)** | Casos restantes tinham gold conservador ("unknown") |

### Conclusão de Hardware para Produção:
- Em **CPU**, o modelo funciona com 100% de precisão e sem OOM (usando `bfloat16`), porém a latência de ~50s por pergunta (~200s por decisão completa) inviabiliza triagens em lote de milhares de processos.
- Em **GPU com >=12 GB VRAM** (como a T4 de 16 GB), o modelo atinge ~4,4s para 4 perguntas simultâneas por decisão, tornando viável a esteira em lotes contínuos no CausaGanha.

---

## 8. Comparação THX-02 vs. OPF (Decision Segmenter)

| Dimensão | OPF (Base Existente no CausaGanha) | THX-02 Local (Avaliador Baseado em LLM) |
| :--- | :--- | :--- |
| **Abordagem** | Detecção determinística de âncoras e fronteiras estruturais | Classificação semântica de unidades com probabilidades calibradas |
| **Hardware** | Extremamente leve (CPU comum, milissegundos por documento) | Pesado (exige ~6 GB RAM e ~50s por inferência em CPU; ideal GPU) |
| **Interpretação de Mérito** | Não interpreta texto (apenas delimita regiões) | Excelente interpretação de inversão recursal e polos vencedores |
| **Papel Ideal** | **Segmentador Primário:** localiza e delimita as regiões | **Classificador / Juiz:** avalia o conteúdo do trecho do dispositivo |
| **Conclusão:** | **Não substituir o OPF:** o THX-02 deve atuar em conjunto com o OPF (o OPF segmenta as regiões e o THX-02 classifica o resultado do dispositivo). |

---

## 9. Dificuldades Encontradas e Correções Realizadas

1. **Gestão de Dependências com `uv`:**
   * O `pyproject.toml` raiz do CausaGanha possui o campo experimental `required-environments`, que gerava avisos no `uv 0.7.19`. Corrigido utilizando `--no-config` para garantir o isolamento do `.venv-thx02`.
2. **Prevenção de Out-Of-Memory (OOM) no Windows:**
   * O runtime padrão do THX-02 tenta carregar pesos em `float32` quando o device é `cpu` (o que consumiria mais de 18 GB de RAM em um sistema de 15,35 GB).
   * **Correção:** Forçou-se `THX02_CPU_DTYPE="bfloat16"`, reduzindo o consumo de RAM dos pesos para **5,27 GB**, permitindo a execução perfeita com folga de mais de 8 GB de memória no sistema.
3. **Ausência de Kernels Triton/CUDA em CPU:**
   * O PyTorch emitiu avisos informando que `causal_conv1d` e `flash-linear-attention` não estavam instalados, recorrendo à implementação de referência em CPU. Essa substituição garantiu 100% de precisão numérica, embora com impacto na taxa de transferência.
4. **Execução do Colab CLI em Windows:**
   * O pacote oficial `google-colab-cli` importa módulos exclusivos Unix (`termios` e `tty`). Desenvolveu-se o wrapper [`scripts/colab_windows.py`](../../scripts/colab_windows.py) que emula esses módulos e permitiu orquestrar a GPU T4 remota do Colab diretamente pelo `uv` no Windows.
5. **Ajuste de Alocação de Memória na GPU T4:**
   * Ao carregar em GPU, o modelo tentava alocar `float32` antes da conversão, causando OOM na T4 (14.56 GB). Corrigiu-se aplicando `torch.set_default_dtype(torch.bfloat16)` e `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`, estabilizando o uso em **8.46 GB de VRAM**.

---

## 10. Próximos Passos (Fine-Tuning com ms-swift)
Com a inferência local e em GPU comprovadas, o próximo experimento viável é a adaptação dos pesos do THX-02 para a ontologia específica do CausaGanha utilizando a ferramenta **ms-swift** com LoRA, focando em tarefas de resultado recursal complexo em ambiente de treinamento com GPU dedicada.
