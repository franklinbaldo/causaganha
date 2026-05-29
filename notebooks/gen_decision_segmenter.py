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
        "Fine-tunes **`openai/privacy-filter`** (token classifier, Apache 2.0) to "
        "**identify and segment** the three structural parts of a Brazilian judicial decision.\n\n"
        "| Label | Section | Description |\n"
        "|---|---|---|\n"
        "| `RELATORIO` | Relatório | Case history and facts summary |\n"
        "| `FUNDAMENTACAO` | Fundamentação | Legal reasoning |\n"
        "| `DISPOSITIVO` | Dispositivo | Operative ruling (the actual decision) |\n\n"
        "**Why `openai/privacy-filter` as base?**\n"
        "- Already a token classifier — we just replace its 33-class PII head with a 3-class section head.\n"
        "- 128K-token context window (handles complete judicial decisions in one pass).\n"
        "- Token-level labels give **exact character boundaries** between sections, not just paragraph labels.\n"
        "- Apache 2.0 license; open weights.\n\n"
        "**Architecture note**: uses banded attention (128-token window per token). "
        "That's fine here — section boundaries are marked by local phrases "
        "(`ante o exposto`, `RELATÓRIO`, etc.), not global document context.\n\n"
        "> **Runtime**: GPU (T4). Enable via Runtime → Change runtime type."
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
        "Uses heuristic markers (`ante o exposto`, `fundamentação`, etc.) to "
        "assign **character-level section spans** to each document. "
        "These are silver labels — good enough to bootstrap a model that will "
        "outperform the heuristic on unseen text, especially cases without explicit markers.\n\n"
        "Each document becomes one training example with char-level spans. "
        "Tokenization (next cell) aligns these spans to token-level labels."
    ),

    code_cell(
        "import sys, re, random\n"
        "import numpy as np\n"
        "import ibis\n"
        "from pathlib import Path\n\n"
        "sys.path.insert(0, f\"{REPO_DIR}/src\")\n\n"
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
        "def segment_document(text):\n"
        "    \"\"\"Return char-level span dict or None if dispositivo not found.\"\"\"\n"
        "    disp_m = _DISPOSITIVO_RE.search(text)\n"
        "    if not disp_m:\n"
        "        return None\n"
        "    disp_start = disp_m.start()\n"
        "    pre = text[:disp_start]\n"
        "    fund_m = _FUNDAMENTACAO_RE.search(pre)\n"
        "    fund_start = fund_m.start() if fund_m else len(pre) // 2\n"
        "    spans = {}\n"
        "    if fund_start > 0:\n"
        "        spans['relatorio'] = [[0, fund_start]]\n"
        "    if disp_start > fund_start:\n"
        "        spans['fundamentacao'] = [[fund_start, disp_start]]\n"
        "    spans['dispositivo'] = [[disp_start, len(text)]]\n"
        "    return spans\n\n"
        "t = ibis.read_parquet(Path(PARQUET_DIR) / 'textos.parquet')\n"
        "df = t.filter(t.texto.notnull()).execute()\n"
        "print(f'Loaded {len(df):,} documents')\n\n"
        "records, skipped = [], 0\n"
        "for _, row in df.iterrows():\n"
        "    spans = segment_document(row['texto'])\n"
        "    if spans is None:\n"
        "        skipped += 1\n"
        "        continue\n"
        "    records.append({'text': row['texto'], 'spans': spans})\n\n"
        "print(f'Documents with spans: {len(records):,} (skipped {skipped} without dispositivo)')\n"
    ),

    md_cell("## 4. Build HuggingFace Dataset"),

    code_cell(
        "from datasets import Dataset\n\n"
        "random.seed(42)\n"
        "random.shuffle(records)\n"
        "n = len(records)\n"
        "train_end = int(n * 0.8)\n"
        "val_end   = train_end + int(n * 0.1)\n\n"
        "raw_train = Dataset.from_list(records[:train_end])\n"
        "raw_val   = Dataset.from_list(records[train_end:val_end])\n"
        "raw_test  = Dataset.from_list(records[val_end:])\n\n"
        "print(f'Train: {len(raw_train):,}  Val: {len(raw_val):,}  Test: {len(raw_test):,}')\n"
    ),

    md_cell(
        "## 5. Tokenize + align labels to tokens\n\n"
        "`openai/privacy-filter` is already a token classifier — we load it "
        "with `num_labels=3` replacing its 33-class PII head with a fresh 3-class "
        "section head. Token labels are aligned from the character spans using "
        "`return_offsets_mapping=True`. Special tokens (CLS/SEP) get label `-100` "
        "(ignored in loss)."
    ),

    code_cell(
        "from transformers import AutoTokenizer\n\n"
        'MODEL_NAME = "openai/privacy-filter"\n'
        "tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n\n"
        "ID2LABEL = {0: 'RELATORIO', 1: 'FUNDAMENTACAO', 2: 'DISPOSITIVO'}\n"
        "LABEL2ID = {v: k for k, v in ID2LABEL.items()}\n\n"
        "def tokenize_and_label(example):\n"
        "    text  = example['text']\n"
        "    spans = example['spans']\n\n"
        "    # Build char-level label array (default: RELATORIO=0)\n"
        "    char_labels = np.zeros(len(text), dtype=np.int32)\n"
        "    for section, span_list in spans.items():\n"
        "        lid = LABEL2ID.get(section.upper(), 0)\n"
        "        for start, end in span_list:\n"
        "            char_labels[start:min(end, len(text))] = lid\n\n"
        "    enc = tokenizer(\n"
        "        text,\n"
        "        truncation=True,\n"
        "        max_length=512,\n"
        "        return_offsets_mapping=True,\n"
        "    )\n"
        "    offsets = enc.pop('offset_mapping')\n\n"
        "    token_labels = []\n"
        "    for start, end in offsets:\n"
        "        if start == end:   # special token\n"
        "            token_labels.append(-100)\n"
        "        else:\n"
        "            token_labels.append(int(char_labels[start]))\n\n"
        "    enc['labels'] = token_labels\n"
        "    return enc\n\n"
        "train_ds = raw_train.map(tokenize_and_label, remove_columns=['text', 'spans'])\n"
        "val_ds   = raw_val.map(tokenize_and_label,   remove_columns=['text', 'spans'])\n"
        "test_ds  = raw_test.map(tokenize_and_label,  remove_columns=['text', 'spans'])\n\n"
        "print('Tokenization done.')\n"
        "print(f'  Example token count: {len(train_ds[0][\"input_ids\"])}')\n"
        "print(f'  Label distribution in first doc:', {ID2LABEL[l]: train_ds[0][\"labels\"].count(l) for l in range(3)})\n"
    ),

    md_cell("## 6. Fine-tune"),

    code_cell(
        "from transformers import (\n"
        "    AutoModelForTokenClassification,\n"
        "    DataCollatorForTokenClassification,\n"
        "    TrainingArguments,\n"
        "    Trainer,\n"
        ")\n"
        "import numpy as np\n"
        "from seqeval.metrics import classification_report as seq_report\n\n"
        "model = AutoModelForTokenClassification.from_pretrained(\n"
        "    MODEL_NAME,\n"
        "    num_labels=3,\n"
        "    id2label=ID2LABEL,\n"
        "    label2id=LABEL2ID,\n"
        "    ignore_mismatched_sizes=True,  # replaces 33-class PII head with 3-class section head\n"
        ")\n\n"
        "def compute_metrics(p):\n"
        "    logits, labels = p\n"
        "    preds = np.argmax(logits, axis=-1)\n"
        "    true_seqs, pred_seqs = [], []\n"
        "    for pred_row, label_row in zip(preds, labels):\n"
        "        true_seq, pred_seq = [], []\n"
        "        for p_id, l_id in zip(pred_row, label_row):\n"
        "            if l_id == -100:\n"
        "                continue\n"
        "            true_seq.append(ID2LABEL[l_id])\n"
        "            pred_seq.append(ID2LABEL[p_id])\n"
        "        true_seqs.append(true_seq)\n"
        "        pred_seqs.append(pred_seq)\n"
        "    report = seq_report(true_seqs, pred_seqs, output_dict=True, zero_division=0)\n"
        "    return {\n"
        "        'macro_f1':           report.get('macro avg', {}).get('f1-score', 0),\n"
        "        'f1_relatorio':       report.get('RELATORIO', {}).get('f1-score', 0),\n"
        "        'f1_fundamentacao':   report.get('FUNDAMENTACAO', {}).get('f1-score', 0),\n"
        "        'f1_dispositivo':     report.get('DISPOSITIVO', {}).get('f1-score', 0),\n"
        "    }\n\n"
        "total_steps = (len(train_ds) // 16) * 3\n"
        "warmup_steps = max(50, total_steps // 10)\n\n"
        "training_args = TrainingArguments(\n"
        '    output_dir="/content/decision_segmenter",\n'
        "    num_train_epochs=3,\n"
        "    per_device_train_batch_size=16,\n"
        "    per_device_eval_batch_size=32,\n"
        "    learning_rate=2e-5,\n"
        "    warmup_steps=warmup_steps,\n"
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
        "    data_collator=DataCollatorForTokenClassification(tokenizer),\n"
        "    compute_metrics=compute_metrics,\n"
        ")\n\n"
        "trainer.train()\n"
    ),

    md_cell("## 7. Evaluate on test set"),

    code_cell(
        "preds_out = trainer.predict(test_ds)\n"
        "preds  = np.argmax(preds_out.predictions, axis=-1)\n"
        "labels = preds_out.label_ids\n\n"
        "true_seqs, pred_seqs = [], []\n"
        "for pred_row, label_row in zip(preds, labels):\n"
        "    t, p = [], []\n"
        "    for p_id, l_id in zip(pred_row, label_row):\n"
        "        if l_id == -100:\n"
        "            continue\n"
        "        t.append(ID2LABEL[l_id])\n"
        "        p.append(ID2LABEL[p_id])\n"
        "    true_seqs.append(t)\n"
        "    pred_seqs.append(p)\n\n"
        "print(seq_report(true_seqs, pred_seqs, zero_division=0))\n"
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
    "feat/embedder-smart-truncate-and-privacy-dataset-v2/notebooks/train_decision_segmenter.ipynb"
)
