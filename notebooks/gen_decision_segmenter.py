#!/usr/bin/env python3
"""Generate notebooks/train_decision_segmenter.ipynb.

Run: python notebooks/gen_decision_segmenter.py
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path


def cell_id() -> str:  # noqa: D103
    return uuid.uuid4().hex[:12]


def code_cell(source: str) -> dict:  # noqa: D103
    return {
        "cell_type": "code",
        "id": cell_id(),
        "metadata": {},
        "source": source,
        "outputs": [],
        "execution_count": None,
    }


def md_cell(source: str) -> dict:  # noqa: D103
    return {
        "cell_type": "markdown",
        "id": cell_id(),
        "metadata": {},
        "source": source,
    }


# ---------------------------------------------------------------------------
# Label taxonomy — kept in sync with scripts/prepare_privacy_filter_dataset.py
# ---------------------------------------------------------------------------

SPAN_CLASS_NAMES = [
    "O",
    "sec_cabecalho",
    "sec_relatorio",
    "sec_fundamentacao",
    "sec_dispositivo",
    "sec_assinatura",
    "elem_nao_textual",
    "parte_autor",
    "parte_reu",
    "parte_terceiro",
    "nome_advogado",
    "oab",
    "nome_juiz",
    "cpf_cnpj",
    "processo_cnj",
    "classe_processual",
    "id_lei",
    "id_precedente",
    "citacao_precedente",
    "data",
]

def _label_type(name: str) -> str:
    return "section" if name.startswith("sec_") or name == "elem_nao_textual" else "entity"


_LABEL_TABLE_ROWS = "\n".join(
    f"| `{name}` | {i} | {_label_type(name)} |"
    for i, name in enumerate(SPAN_CLASS_NAMES)
)

# ---------------------------------------------------------------------------
# Notebook cells
# ---------------------------------------------------------------------------

cells = [
    md_cell(
        "# Train Decision Segmenter — CausaGanha\n\n"
        "Fine-tunes **`openai/privacy-filter`** (token classifier, Apache 2.0) to "
        "**identify and segment** Brazilian judicial decisions with a rich 20-class taxonomy.\n\n"
        "## Label taxonomy\n\n"
        "| Label | ID | Type |\n"
        "|---|---|---|\n"
        + _LABEL_TABLE_ROWS + "\n\n"
        "### Heuristic coverage in training data\n\n"
        "| Layer | Labels | Coverage |\n"
        "|---|---|---|\n"
        "| Structural sections | `sec_*` | ✓ high (regex markers) |\n"
        "| Legal identifiers | `processo_cnj`, `id_lei`, `id_precedente`, `classe_processual` |"
        " ✓ high |\n"
        "| PII / registration | `cpf_cnpj`, `oab` | ✓ high |\n"
        "| Dates | `data` | ✓ high |\n"
        "| Lawyer name | `nome_advogado` | ~ partial (adjacent-to-OAB) |\n"
        "| Party / judge names | `parte_*`, `nome_juiz` | ✗ needs LLM pass |\n"
        "| Direct quotes | `citacao_precedente` | ✗ needs LLM pass |\n"
        "| Non-textual | `elem_nao_textual` | ✗ needs LLM pass |\n\n"
        "**Why `openai/privacy-filter` as base?**\n"
        "- Already a token classifier — we replace its 33-class PII head"
        " with a fresh 20-class head.\n"
        "- 128K-token context window (handles complete judicial decisions in one pass).\n"
        "- Token-level labels give **exact character boundaries**, not just paragraph labels.\n"
        "- Apache 2.0 license; open weights; official `opf train` CLI for fine-tuning.\n\n"
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
        '!uv pip install --system -e ".[embeddings]" '
        "transformers accelerate datasets scikit-learn\n"
    ),

    md_cell("## 2. Download data from Internet Archive"),

    code_cell(
        "import os, urllib.request\n\n"
        'PARQUET_DIR = f"{REPO_DIR}/data/test_parquets"\n'
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
        "Heuristic segmentation produces **silver labels**. "
        "Pattern-based labels (processo CNJ, CPF, lei, precedente, datas, OAB) are high-precision. "
        "Section boundaries use textual markers (`ante o exposto`, `RELATÓRIO`, etc.). "
        "Party/judge names and direct precedent quotes require a future LLM annotation pass.\n\n"
        "Entity spans **overwrite** section spans when they overlap — entities are more specific."
    ),

    code_cell(
        "import sys, re, random, json\n"
        "import numpy as np\n"
        "import ibis\n"
        "from pathlib import Path\n\n"
        'sys.path.insert(0, f"{REPO_DIR}/src")\n\n'
        "# Import label taxonomy and segmentation logic from the repo script\n"
        "import importlib.util, types\n"
        "spec = importlib.util.spec_from_file_location(\n"
        "    'prepare_ds', f'{REPO_DIR}/scripts/prepare_privacy_filter_dataset.py'\n"
        ")\n"
        "mod = importlib.util.module_from_spec(spec)\n"
        "spec.loader.exec_module(mod)\n\n"
        "SPAN_CLASS_NAMES = mod.SPAN_CLASS_NAMES\n"
        "LABEL_SPACE      = mod.LABEL_SPACE\n"
        "_segment         = mod._segment\n\n"
        "ID2LABEL = {i: name for i, name in enumerate(SPAN_CLASS_NAMES)}\n"
        "LABEL2ID = {name: i for i, name in enumerate(SPAN_CLASS_NAMES)}\n"
        "NUM_LABELS = len(SPAN_CLASS_NAMES)  # 20\n\n"
        "t = ibis.read_parquet(Path(PARQUET_DIR) / 'textos.parquet')\n"
        "df = t.filter(t.texto.notnull()).execute()\n"
        "print(f'Loaded {len(df):,} documents')\n\n"
        "records, skipped = [], 0\n"
        "for _, row in df.iterrows():\n"
        "    spans = _segment(row['texto'])\n"
        "    if spans is None:\n"
        "        skipped += 1\n"
        "        continue\n"
        "    records.append({'text': row['texto'], 'spans': spans})\n\n"
        "print(f'Documents with spans: {len(records):,}  "
        "(skipped {skipped} without dispositivo)')\n\n"
        "# Label coverage report\n"
        "from collections import Counter\n"
        "cov = Counter(lbl for r in records for lbl in r['spans'])\n"
        "print('\\nLabel coverage:')\n"
        "for lbl, cnt in sorted(cov.items(), key=lambda x: -x[1]):\n"
        "    print(f'  {lbl:<22} {cnt:>5}  ({cnt/len(records):.0%})')\n"
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
        "with `num_labels=20` replacing its 33-class PII head with a fresh 20-class head. "
        "(`ignore_mismatched_sizes=True` keeps all encoder weights.)\n\n"
        "Token labels are aligned from character spans via `return_offsets_mapping=True`. "
        "Special tokens (CLS/SEP) get label `-100` (ignored in loss).\n\n"
        "**Priority rule**: entity labels overwrite section labels when spans overlap — "
        "entities are more specific and the model benefits from the hierarchical signal."
    ),

    code_cell(
        "from transformers import AutoTokenizer\n\n"
        'MODEL_NAME = "openai/privacy-filter"\n'
        "tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)\n\n"
        "_SECTION_LABELS = frozenset([\n"
        "    'sec_cabecalho', 'sec_relatorio', 'sec_fundamentacao',\n"
        "    'sec_dispositivo', 'sec_assinatura', 'elem_nao_textual',\n"
        "])\n\n"
        "def tokenize_and_label(example):\n"
        "    text  = example['text']\n"
        "    spans = example['spans']\n\n"
        "    # Build char-level label array: default O=0\n"
        "    char_labels = np.zeros(len(text), dtype=np.int32)\n\n"
        "    # Pass 1: section labels (lower priority)\n"
        "    for label_name, span_list in spans.items():\n"
        "        if label_name not in _SECTION_LABELS:\n"
        "            continue\n"
        "        lid = LABEL2ID.get(label_name, 0)\n"
        "        for start, end in span_list:\n"
        "            char_labels[start:min(end, len(text))] = lid\n\n"
        "    # Pass 2: entity labels (higher priority — overwrite sections)\n"
        "    for label_name, span_list in spans.items():\n"
        "        if label_name in _SECTION_LABELS:\n"
        "            continue\n"
        "        lid = LABEL2ID.get(label_name, 0)\n"
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
        "# Label distribution in first doc (exclude O and -100)\n"
        "dist = {\n"
        "    ID2LABEL[l]: train_ds[0]['labels'].count(l)\n"
        "    for l in range(NUM_LABELS) if train_ds[0]['labels'].count(l) > 0\n"
        "}\n"
        "print(f'  Label dist (first doc): {dist}')\n"
    ),

    md_cell("## 6. Fine-tune"),

    code_cell(
        "from transformers import (\n"
        "    AutoModelForTokenClassification,\n"
        "    DataCollatorForTokenClassification,\n"
        "    TrainingArguments,\n"
        "    Trainer,\n"
        ")\n"
        "from sklearn.metrics import classification_report\n\n"
        "model = AutoModelForTokenClassification.from_pretrained(\n"
        "    MODEL_NAME,\n"
        "    num_labels=NUM_LABELS,\n"
        "    id2label=ID2LABEL,\n"
        "    label2id=LABEL2ID,\n"
        "    ignore_mismatched_sizes=True,  # replaces 33-class PII head\n"
        "    trust_remote_code=True,\n"
        ")\n\n"
        "def compute_metrics(p):\n"
        "    logits, labels = p\n"
        "    preds = np.argmax(logits, axis=-1)\n"
        "    y_true, y_pred = [], []\n"
        "    for pred_row, label_row in zip(preds, labels):\n"
        "        for p_id, l_id in zip(pred_row, label_row):\n"
        "            if l_id == -100:\n"
        "                continue\n"
        "            y_true.append(ID2LABEL[l_id])\n"
        "            y_pred.append(ID2LABEL[p_id])\n"
        "    report = classification_report(\n"
        "        y_true, y_pred,\n"
        "        labels=[n for n in SPAN_CLASS_NAMES if n != 'O'],\n"
        "        output_dict=True, zero_division=0,\n"
        "    )\n"
        "    macro = report.get('macro avg', {})\n"
        "    # Return per-class F1 for key labels\n"
        "    result = {\n"
        "        'macro_f1':          macro.get('f1-score', 0),\n"
        "        'macro_precision':   macro.get('precision', 0),\n"
        "        'macro_recall':      macro.get('recall', 0),\n"
        "    }\n"
        "    for lbl in ['sec_dispositivo', 'sec_fundamentacao', 'sec_relatorio',\n"
        "                'processo_cnj', 'id_lei', 'id_precedente', 'data']:\n"
        "        result[f'f1_{lbl}'] = report.get(lbl, {}).get('f1-score', 0)\n"
        "    return result\n\n"
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
        "y_true, y_pred = [], []\n"
        "for pred_row, label_row in zip(preds, labels):\n"
        "    for p_id, l_id in zip(pred_row, label_row):\n"
        "        if l_id == -100:\n"
        "            continue\n"
        "        y_true.append(ID2LABEL[l_id])\n"
        "        y_pred.append(ID2LABEL[p_id])\n\n"
        "print(classification_report(\n"
        "    y_true, y_pred,\n"
        "    labels=[n for n in SPAN_CLASS_NAMES if n != 'O'],\n"
        "    zero_division=0,\n"
        "))\n"
    ),

    md_cell("## 8. Save label_space.json + model"),

    code_cell(
        "import shutil, json\n"
        "from google.colab import files\n\n"
        'MODEL_OUT = "/content/decision_segmenter_best"\n'
        "trainer.save_model(MODEL_OUT)\n"
        "tokenizer.save_pretrained(MODEL_OUT)\n\n"
        "# Save label_space.json — required for opf eval / deployment\n"
        "label_space_path = f'{MODEL_OUT}/label_space.json'\n"
        "with open(label_space_path, 'w') as f:\n"
        "    json.dump(LABEL_SPACE, f, indent=2, ensure_ascii=False)\n\n"
        'print(f"Model + label_space.json saved to {MODEL_OUT}")\n\n'
        "shutil.make_archive('/content/decision_segmenter', 'zip', MODEL_OUT)\n"
        "files.download('/content/decision_segmenter.zip')\n"
        "print('Downloaded decision_segmenter.zip')\n"
    ),

    md_cell(
        "## 9. Use with `opf train` (alternative to HuggingFace Trainer)\n\n"
        "The JSONL files produced by `scripts/prepare_privacy_filter_dataset.py` "
        "are also compatible with the official `opf` CLI:\n\n"
        "```bash\n"
        "pip install opf\n"
        "opf train data/privacy_filter/train.jsonl \\\n"
        "    --validation-dataset data/privacy_filter/validation.jsonl \\\n"
        "    --label-space-json   data/privacy_filter/label_space.json \\\n"
        "    --output-dir         checkpoints/decision_segmenter\n"
        "```\n\n"
        "The `opf` approach uses the model's own fine-tuning infrastructure "
        "(gradient checkpointing, mixed precision) without any HuggingFace Trainer setup."
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
print(f"Written: {output}")  # noqa: T201
print(  # noqa: T201
    "\nColab URL:\n"
    "https://colab.research.google.com/github/franklinbaldo/causaganha/blob/"
    "feat/embedder-smart-truncate-and-privacy-dataset-v2/notebooks/train_decision_segmenter.ipynb"
)
