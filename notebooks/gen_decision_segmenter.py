#!/usr/bin/env python3
"""Generate notebooks/train_decision_segmenter.ipynb.

Run: python notebooks/gen_decision_segmenter.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path


def cell_id() -> str:
    return uuid.uuid4().hex[:12]


def code_cell(source: str) -> dict:
    return {
        "cell_type": "code",
        "id": cell_id(),
        "metadata": {},
        "source": source,
        "outputs": [],
        "execution_count": None,
    }


def md_cell(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "id": cell_id(),
        "metadata": {},
        "source": source,
    }


# ---------------------------------------------------------------------------
# Notebook cells
# ---------------------------------------------------------------------------

cells = [
    md_cell(
        "# Train Decision Segmenter — CausaGanha\n\n"
        "Fine-tunes `neuralmind/bert-base-portuguese-cased` to **identify and segment** "
        "the three structural parts of a Brazilian judicial decision:\n\n"
        "| Label | Section | Description |\n"
        "|---|---|---|\n"
        "| `RELATORIO` | Relatório | Case history and facts summary |\n"
        "| `FUNDAMENTACAO` | Fundamentação | Legal reasoning |\n"
        "| `DISPOSITIVO` | Dispositivo | Operative ruling (the actual decision) |\n\n"
        "> **Runtime**: GPU (T4 recommended). Enable via Runtime → Change runtime type."
    ),

    md_cell("## 1. Setup — clone repo & install deps"),

    code_cell(
        'REPO_URL  = "https://github.com/franklinbaldo/causaganha.git"\n'
        'BRANCH    = "feat/embedder-smart-truncate-and-privacy-dataset-v2"\n'
        'REPO_DIR  = "/content/causaganha"\n'
    ),

    code_cell(
        "import os\n"
        "if not os.path.exists(REPO_DIR):\n"
        "    !git clone --branch {BRANCH} --depth 1 {REPO_URL} {REPO_DIR}\n"
        "else:\n"
        "    !git -C {REPO_DIR} pull\n"
        "os.chdir(REPO_DIR)\n"
        'print(f"Working directory: {os.getcwd()}")\n'
    ),

    code_cell(
        "!curl -LsSf https://astral.sh/uv/install.sh | sh\n"
        "import os\n"
        "os.environ['PATH'] = f\"/root/.local/bin:{os.environ['PATH']}\"\n"
        "!uv --version\n"
    ),

    code_cell(
        '!uv pip install --system -e ".[embeddings]" transformers accelerate datasets seqeval\n'
    ),

    md_cell("## 2. Download data from Internet Archive"),

    code_cell(
        "import os, urllib.request\n\n"
        "PARQUET_DIR = f\"{REPO_DIR}/data/test_parquets\"\n"
        "os.makedirs(PARQUET_DIR, exist_ok=True)\n\n"
        "FILES = {\n"
        '    "textos.parquet": '
        '"https://archive.org/download/causaganha-test-parquets/textos.parquet",\n'
        "}\n\n"
        "for fname, url in FILES.items():\n"
        "    dest = os.path.join(PARQUET_DIR, fname)\n"
        "    if os.path.exists(dest):\n"
        '        print(f"  Already exists: {fname}")\n'
        "        continue\n"
        '    print(f"  Downloading {fname} ...")\n'
        "    urllib.request.urlretrieve(url, dest)\n"
        "    size = os.path.getsize(dest)\n"
        '    print(f"  OK {fname} ({size:,} bytes)")\n\n'
        "print('All files ready.')\n"
    ),

    md_cell(
        "## 3. Prepare labeled dataset\n\n"
        "Uses heuristic markers (`ante o exposto`, `fundamentação`, etc.) to label "
        "each document's paragraphs. These are **silver labels** — good enough to "
        "bootstrap a classifier that will outperform the heuristic on unseen text."
    ),

    code_cell(
        "import sys\n"
        "sys.path.insert(0, f\"{REPO_DIR}/src\")\n\n"
        "import re, json, random\n"
        "import ibis\n"
        "from pathlib import Path\n\n"
        "_DISPOSITIVO_RE = re.compile(\n"
        "    r'(?:ante\\s+o\\s+exposto|posto\\s+isso|isso\\s+posto|'\n"
        "    r'diante\\s+do\\s+exposto|pelo\\s+exposto|em\\s+face\\s+do\\s+exposto|'\n"
        "    r'por\\s+tais\\s+fundamentos|nestes\\s+termos|em\\s+conclus[\\u00e3a]o|'\n"
        "    r'pelo\\s+que\\s+exposto|em\\s+vista\\s+do\\s+exposto)',\n"
        "    re.IGNORECASE,\n"
        ")\n"
        "_FUNDAMENTACAO_RE = re.compile(\n"
        "    r'(?:fundament[ao](?:\\u00e7\\u00e3o)?|m[\\u00e9e]rito|an[\\u00e1a]lise\\s+do\\s+pedido|'\n"
        "    r'da\\s+an[\\u00e1a]lise|do\\s+m[\\u00e9e]rito|'\n"
        "    r'fundamenta[\\u00e7c][\\u00e3a]o\\s+(?:jur[\\u00edi]dica|do\\s+ju[\\u00edi]zo))',\n"
        "    re.IGNORECASE,\n"
        ")\n\n"
        "def split_paragraphs(text):\n"
        "    \"\"\"Split text into (start, end, paragraph) tuples.\"\"\"\n"
        "    paras = []\n"
        "    pos = 0\n"
        "    for para in re.split(r'\\n{2,}', text):\n"
        "        if para.strip():\n"
        "            paras.append((pos, pos + len(para), para))\n"
        "        pos += len(para) + 2  # account for split separator\n"
        "    return paras\n\n"
        "def label_document(text):\n"
        "    \"\"\"Label each paragraph: 0=relatorio, 1=fundamentacao, 2=dispositivo.\"\"\"\n"
        "    disp_m = _DISPOSITIVO_RE.search(text)\n"
        "    if not disp_m:\n"
        "        return None\n"
        "    disp_start = disp_m.start()\n"
        "    pre_disp = text[:disp_start]\n"
        "    fund_m = _FUNDAMENTACAO_RE.search(pre_disp)\n"
        "    fund_start = fund_m.start() if fund_m else len(pre_disp) // 2\n\n"
        "    paras = split_paragraphs(text)\n"
        "    labeled = []\n"
        "    for start, end, para in paras:\n"
        "        mid = (start + end) / 2\n"
        "        if mid < fund_start:\n"
        "            label = 0  # RELATORIO\n"
        "        elif mid < disp_start:\n"
        "            label = 1  # FUNDAMENTACAO\n"
        "        else:\n"
        "            label = 2  # DISPOSITIVO\n"
        "        labeled.append({'text': para, 'label': label})\n"
        "    return labeled\n\n"
        "t = ibis.read_parquet(Path(PARQUET_DIR) / 'textos.parquet')\n"
        "df = t.filter(t.texto.notnull()).execute()\n"
        "print(f'Loaded {len(df):,} documents')\n\n"
        "all_paras = []\n"
        "skipped = 0\n"
        "for _, row in df.iterrows():\n"
        "    labeled = label_document(row['texto'])\n"
        "    if labeled is None:\n"
        "        skipped += 1\n"
        "        continue\n"
        "    all_paras.extend(labeled)\n\n"
        "print(f'Paragraphs: {len(all_paras):,} (skipped {skipped} docs without dispositivo)')\n"
        "label_counts = {0: 0, 1: 0, 2: 0}\n"
        "for p in all_paras:\n"
        "    label_counts[p['label']] += 1\n"
        "labels_map = {0: 'RELATORIO', 1: 'FUNDAMENTACAO', 2: 'DISPOSITIVO'}\n"
        "for k, v in sorted(label_counts.items()):\n"
        "    print(f'  {labels_map[k]}: {v:,}')\n"
    ),

    md_cell("## 4. Build HuggingFace Dataset"),

    code_cell(
        "from datasets import Dataset\n"
        "import random\n\n"
        "random.seed(42)\n"
        "random.shuffle(all_paras)\n\n"
        "n = len(all_paras)\n"
        "train_end = int(n * 0.8)\n"
        "val_end   = train_end + int(n * 0.1)\n\n"
        "train_ds = Dataset.from_list(all_paras[:train_end])\n"
        "val_ds   = Dataset.from_list(all_paras[train_end:val_end])\n"
        "test_ds  = Dataset.from_list(all_paras[val_end:])\n\n"
        "print(f'Train: {len(train_ds):,}  Val: {len(val_ds):,}  Test: {len(test_ds):,}')\n"
    ),

    md_cell(
        "## 5. Tokenize\n\n"
        "Using `neuralmind/bert-base-portuguese-cased` — 110M params, trained on "
        "Brazilian Portuguese corpora, strong baseline for legal PT-BR."
    ),

    code_cell(
        "from transformers import AutoTokenizer\n\n"
        'MODEL_NAME = "neuralmind/bert-base-portuguese-cased"\n'
        "tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n\n"
        "def tokenize(batch):\n"
        "    return tokenizer(\n"
        "        batch['text'],\n"
        "        truncation=True,\n"
        "        max_length=512,\n"
        "        padding='max_length',\n"
        "    )\n\n"
        "train_ds = train_ds.map(tokenize, batched=True)\n"
        "val_ds   = val_ds.map(tokenize,   batched=True)\n"
        "test_ds  = test_ds.map(tokenize,  batched=True)\n\n"
        "train_ds = train_ds.rename_column('label', 'labels')\n"
        "val_ds   = val_ds.rename_column('label',   'labels')\n"
        "test_ds  = test_ds.rename_column('label',  'labels')\n\n"
        "train_ds.set_format('torch', columns=['input_ids','attention_mask','token_type_ids','labels'])\n"
        "val_ds.set_format('torch',   columns=['input_ids','attention_mask','token_type_ids','labels'])\n"
        "test_ds.set_format('torch',  columns=['input_ids','attention_mask','token_type_ids','labels'])\n\n"
        "print('Tokenization done.')\n"
    ),

    md_cell("## 6. Fine-tune"),

    code_cell(
        "from transformers import (\n"
        "    AutoModelForSequenceClassification,\n"
        "    TrainingArguments,\n"
        "    Trainer,\n"
        ")\n"
        "import numpy as np\n"
        "from sklearn.metrics import classification_report\n\n"
        "ID2LABEL = {0: 'RELATORIO', 1: 'FUNDAMENTACAO', 2: 'DISPOSITIVO'}\n"
        "LABEL2ID = {v: k for k, v in ID2LABEL.items()}\n\n"
        "model = AutoModelForSequenceClassification.from_pretrained(\n"
        "    MODEL_NAME,\n"
        "    num_labels=3,\n"
        "    id2label=ID2LABEL,\n"
        "    label2id=LABEL2ID,\n"
        ")\n\n"
        "def compute_metrics(eval_pred):\n"
        "    logits, labels = eval_pred\n"
        "    preds = np.argmax(logits, axis=-1)\n"
        "    report = classification_report(\n"
        "        labels, preds,\n"
        "        target_names=list(ID2LABEL.values()),\n"
        "        output_dict=True,\n"
        "        zero_division=0,\n"
        "    )\n"
        "    return {\n"
        "        'accuracy': report['accuracy'],\n"
        "        'f1_relatorio':     report['RELATORIO']['f1-score'],\n"
        "        'f1_fundamentacao': report['FUNDAMENTACAO']['f1-score'],\n"
        "        'f1_dispositivo':   report['DISPOSITIVO']['f1-score'],\n"
        "        'macro_f1':         report['macro avg']['f1-score'],\n"
        "    }\n\n"
        "training_args = TrainingArguments(\n"
        '    output_dir="/content/decision_segmenter",\n'
        "    num_train_epochs=3,\n"
        "    per_device_train_batch_size=16,\n"
        "    per_device_eval_batch_size=32,\n"
        "    learning_rate=2e-5,\n"
        "    warmup_ratio=0.1,\n"
        "    weight_decay=0.01,\n"
        "    eval_strategy='epoch',\n"
        "    save_strategy='epoch',\n"
        "    load_best_model_at_end=True,\n"
        "    metric_for_best_model='macro_f1',\n"
        "    fp16=True,\n"
        "    logging_steps=50,\n"
        "    report_to='none',\n"
        ")\n\n"
        "trainer = Trainer(\n"
        "    model=model,\n"
        "    args=training_args,\n"
        "    train_dataset=train_ds,\n"
        "    eval_dataset=val_ds,\n"
        "    compute_metrics=compute_metrics,\n"
        ")\n\n"
        "trainer.train()\n"
    ),

    md_cell("## 7. Evaluate on test set"),

    code_cell(
        "import numpy as np\n"
        "from sklearn.metrics import classification_report\n\n"
        "preds_out = trainer.predict(test_ds)\n"
        "preds     = np.argmax(preds_out.predictions, axis=-1)\n"
        "labels    = preds_out.label_ids\n\n"
        "print(classification_report(\n"
        "    labels, preds,\n"
        "    target_names=['RELATORIO', 'FUNDAMENTACAO', 'DISPOSITIVO'],\n"
        "    zero_division=0,\n"
        "))\n"
    ),

    md_cell("## 8. Save & download model"),

    code_cell(
        "import shutil\n"
        "from google.colab import files\n\n"
        'MODEL_OUT = "/content/decision_segmenter_best"\n'
        "trainer.save_model(MODEL_OUT)\n"
        "tokenizer.save_pretrained(MODEL_OUT)\n"
        'print(f"Model saved to {MODEL_OUT}")\n\n'
        "shutil.make_archive('/content/decision_segmenter', 'zip', MODEL_OUT)\n"
        "files.download('/content/decision_segmenter.zip')\n"
        "print('Downloaded decision_segmenter.zip')\n"
    ),
]

# ---------------------------------------------------------------------------
# Assemble and write notebook
# ---------------------------------------------------------------------------

notebook = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.12.0",
        },
        "colab": {
            "provenance": [],
            "gpuType": "T4",
        },
        "accelerator": "GPU",
    },
    "cells": cells,
}

output = Path(__file__).parent / "train_decision_segmenter.ipynb"
output.write_text(json.dumps(notebook, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Written: {output}")
print(
    "\nColab URL:\n"
    "https://colab.research.google.com/github/franklinbaldo/causaganha/blob/"
    "feat/embedder-smart-truncate-and-privacy-dataset/notebooks/train_decision_segmenter.ipynb"
)
