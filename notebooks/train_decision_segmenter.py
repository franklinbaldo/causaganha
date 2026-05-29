# /// script
# dependencies = ["-", "accelerate", "datasets", "scikit-learn", "transformers"]
# ///

import marimo

__generated_with = "0.23.8"
app = marimo.App()


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell
def _():
    import subprocess

    return (subprocess,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Train Decision Segmenter — CausaGanha

    Fine-tunes **`openai/privacy-filter`** (token classifier, Apache 2.0) to **identify and segment** Brazilian judicial decisions with a rich 22-class taxonomy.

    ## Label taxonomy

    | Label | ID | Type |
    |---|---|---|
    | `O` | 0 | entity |
    | `sec_cabecalho` | 1 | section |
    | `sec_relatorio` | 2 | section |
    | `sec_fundamentacao` | 3 | section |
    | `sec_dispositivo` | 4 | section |
    | `sec_assinatura` | 5 | section |
    | `elem_nao_textual` | 6 | section |
    | `parte_autor` | 7 | entity |
    | `parte_reu` | 8 | entity |
    | `parte_terceiro` | 9 | entity |
    | `nome_advogado` | 10 | entity |
    | `oab` | 11 | entity |
    | `nome_juiz` | 12 | entity |
    | `cpf_cnpj` | 13 | entity |
    | `processo_cnj` | 14 | entity |
    | `classe_processual` | 15 | entity |
    | `id_lei` | 16 | entity |
    | `id_precedente` | 17 | entity |
    | `citacao_precedente` | 18 | entity |
    | `data` | 19 | entity |
    | `serventuario` | 20 | entity |
    | `valor_monetario` | 21 | entity |

    ### Heuristic coverage in training data

    | Layer | Labels | Coverage |
    |---|---|---|
    | Structural sections | `sec_*` | ✓ high (regex markers) |
    | Legal identifiers | `processo_cnj`, `id_lei`, `id_precedente`, `classe_processual` | ✓ high |
    | PII / registration | `cpf_cnpj`, `oab` | ✓ high |
    | Dates | `data` | ✓ high |
    | Lawyer name | `nome_advogado` | ~ partial (adjacent-to-OAB) |
    | Party / judge names | `parte_*`, `nome_juiz` | ✗ needs LLM pass |
    | Direct quotes | `citacao_precedente` | ✗ needs LLM pass |
    | Non-textual | `elem_nao_textual` | ✗ needs LLM pass |

    **Why `openai/privacy-filter` as base?**
    - Already a token classifier — we replace its 33-class PII head with a fresh 22-class head.
    - 128K-token context window (handles complete judicial decisions in one pass).
    - Token-level labels give **exact character boundaries**, not just paragraph labels.
    - Apache 2.0 license; open weights; official `opf train` CLI for fine-tuning.

    > **Runtime**: GPU (T4). Enable via Runtime → Change runtime type.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Setup — clone repo & install deps
    """)
    return


@app.cell
def _():
    REPO_URL  = "https://github.com/franklinbaldo/causaganha.git"
    BRANCH    = "main"
    REPO_DIR  = "/content/causaganha"
    return BRANCH, REPO_DIR, REPO_URL


@app.cell
def _(BRANCH, REPO_DIR, REPO_URL, subprocess):
    import os
    if not os.path.exists(REPO_DIR):
        #! git clone --branch {BRANCH} --depth 1 {REPO_URL} {REPO_DIR}
        subprocess.call(['git', 'clone', '--branch', str(BRANCH), '--depth', '1', str(REPO_URL), str(REPO_DIR)])
    else:
        #! git -C {REPO_DIR} pull
        subprocess.call(['git', '-C', str(REPO_DIR), 'pull'])
    os.chdir(REPO_DIR)
    print(f"Working directory: {os.getcwd()}")
    return


@app.cell
def _(subprocess):
    #! curl -LsSf https://astral.sh/uv/install.sh | sh
    subprocess.call(['curl', '-LsSf', 'https://astral.sh/uv/install.sh', '|', 'sh'])
    import os
    os.environ['PATH'] = f"/root/.local/bin:{os.environ['PATH']}"
    #! uv --version
    subprocess.call(['uv', '--version'])
    return


@app.cell
def _():
    # packages added via marimo's package management: .[embeddings] transformers accelerate datasets scikit-learn !uv pip install --system -e ".[embeddings]" transformers accelerate datasets scikit-learn
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Build textos.parquet from TJRO 2025 ZIPs
    """)
    return


@app.cell
def _(REPO_DIR):
    # --- Configuration ---
    N_ZIPS      = 50       # ZIPs to process (None = all 384, ~2.8 GB)
    MIN_TEXT    = 200      # minimum text length (chars) to keep
    MAX_WORKERS = 8        # parallel downloads
    IA_ITEM     = 'djen-tjro-2025'
    PARQUET_DIR  = f"{REPO_DIR}/data/test_parquets"
    PARQUET_PATH = f"{PARQUET_DIR}/textos.parquet"
    return IA_ITEM, MAX_WORKERS, MIN_TEXT, N_ZIPS, PARQUET_DIR, PARQUET_PATH


@app.cell
def _(IA_ITEM, MAX_WORKERS, MIN_TEXT, N_ZIPS, PARQUET_DIR, PARQUET_PATH):
    import zipfile, json, io, uuid, os
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import pandas as pd

    NAMESPACE_DJEN = uuid.uuid5(uuid.NAMESPACE_DNS, 'djen.causaganha.org')

    # List ZIPs from Internet Archive metadata
    print('Listing ZIPs from Internet Archive...')
    meta_url = f'https://archive.org/metadata/{IA_ITEM}/files'
    with urllib.request.urlopen(meta_url) as r:
        ia_files = json.loads(r.read()).get('result', [])
    zips = sorted(
        f['name'] for f in ia_files
        if f['name'].startswith('djen-') and f['name'].endswith('.zip')
    )
    if N_ZIPS:
        zips = zips[:N_ZIPS]
    print(f'Processing {len(zips)} ZIPs...')

    def _iter_records(data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            items = data.get('items')
            if isinstance(items, list):
                return items
            return [data]
        return []

    def extract_texts(zip_name):
        url = f'https://archive.org/download/{IA_ITEM}/{zip_name}'
        try:
            with urllib.request.urlopen(url, timeout=120) as r:
                content = r.read()
            rows = []
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                for name in zf.namelist():
                    if not name.endswith('.json'):
                        continue
                    try:
                        data = json.loads(zf.read(name))
                    except json.JSONDecodeError:
                        continue
                    for rec in _iter_records(data):
                        if not isinstance(rec, dict):
                            continue
                        texto = (rec.get('texto') or '').strip()
                        if len(texto) >= MIN_TEXT:
                            uid = str(uuid.uuid5(NAMESPACE_DJEN, texto))
                            rows.append({'id': uid, 'texto': texto})
            return rows
        except (urllib.error.URLError, zipfile.BadZipFile, OSError, ValueError) as e:
            print(f'  WARN {zip_name}: {e}')
            return []

    # Download & extract in parallel
    all_rows = []
    os.makedirs(PARQUET_DIR, exist_ok=True)
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(extract_texts, z): z for z in zips}
        for i, fut in enumerate(as_completed(futures), 1):
            all_rows.extend(fut.result())
            if i % 10 == 0 or i == len(zips):
                print(f'  {i}/{len(zips)} done — {len(all_rows):,} texts so far')

    # Deduplicate & save
    df = pd.DataFrame(all_rows).drop_duplicates('id').reset_index(drop=True)
    df.to_parquet(PARQUET_PATH, index=False)
    print(f'Saved {len(df):,} unique texts → {PARQUET_PATH}')
    return (json,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Prepare labeled dataset

    Heuristic segmentation produces **silver labels**. Pattern-based labels (processo CNJ, CPF, lei, precedente, datas, OAB) are high-precision. Section boundaries use textual markers (`ante o exposto`, `RELATÓRIO`, etc.). Party/judge names and direct precedent quotes require a future LLM annotation pass.

    Entity spans **overwrite** section spans when they overlap — entities are more specific.
    """)
    return


@app.cell
def _(PARQUET_DIR, REPO_DIR):
    import sys, re, random
    import numpy as np
    import ibis
    from pathlib import Path
    sys.path.insert(0, f'{REPO_DIR}/src')
    import importlib.util, types
    spec = importlib.util.spec_from_file_location('prepare_ds', f'{REPO_DIR}/scripts/prepare_privacy_filter_dataset.py')
    # Import label taxonomy and segmentation logic from the repo script
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    SPAN_CLASS_NAMES = mod.SPAN_CLASS_NAMES
    LABEL_SPACE = mod.LABEL_SPACE
    _segment = mod._segment
    ID2LABEL = {i: name for i, name in enumerate(SPAN_CLASS_NAMES)}
    LABEL2ID = {name: i for i, name in enumerate(SPAN_CLASS_NAMES)}
    NUM_LABELS = len(SPAN_CLASS_NAMES)
    t = ibis.read_parquet(Path(PARQUET_DIR) / 'textos.parquet')
    df_1 = t.filter(t.texto.notnull()).execute()
    print(f'Loaded {len(df_1):,} documents')
    records, skipped = ([], 0)
    for _, row in df_1.iterrows():
        spans = _segment(row['texto'])  # 22
        if spans is None:
            skipped = skipped + 1
            continue
        records.append({'text': row['texto'], 'spans': spans})
    print(f'Documents with spans: {len(records):,}  (skipped {skipped} without dispositivo)')
    from collections import Counter
    cov = Counter((lbl for r in records for lbl in r['spans']))
    print('\nLabel coverage:')
    for lbl, cnt in sorted(cov.items(), key=lambda x: -x[1]):
    # Label coverage report
        print(f'  {lbl:<22} {cnt:>5}  ({cnt / len(records):.0%})')
    return (
        ID2LABEL,
        LABEL2ID,
        LABEL_SPACE,
        NUM_LABELS,
        SPAN_CLASS_NAMES,
        np,
        random,
        records,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Build HuggingFace Dataset
    """)
    return


@app.cell
def _(random, records):
    from datasets import Dataset

    random.seed(42)
    random.shuffle(records)
    n = len(records)
    train_end = int(n * 0.8)
    val_end   = train_end + int(n * 0.1)

    raw_train = Dataset.from_list(records[:train_end])
    raw_val   = Dataset.from_list(records[train_end:val_end])
    raw_test  = Dataset.from_list(records[val_end:])

    print(f'Train: {len(raw_train):,}  Val: {len(raw_val):,}  Test: {len(raw_test):,}')
    return raw_test, raw_train, raw_val


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Tokenize + align labels to tokens

    `openai/privacy-filter` is already a token classifier — we load it with `num_labels=22` replacing its 33-class PII head with a fresh 22-class head. (`ignore_mismatched_sizes=True` keeps all encoder weights.)

    Token labels are aligned from character spans via `return_offsets_mapping=True`. Special tokens (CLS/SEP) get label `-100` (ignored in loss).

    **Priority rule**: entity labels overwrite section labels when spans overlap — entities are more specific and the model benefits from the hierarchical signal.
    """)
    return


@app.cell
def _(ID2LABEL, LABEL2ID, NUM_LABELS, np, raw_test, raw_train, raw_val):
    from transformers import AutoTokenizer
    MODEL_NAME = 'openai/privacy-filter'
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    _SECTION_LABELS = frozenset(['sec_cabecalho', 'sec_relatorio', 'sec_fundamentacao', 'sec_dispositivo', 'sec_assinatura', 'elem_nao_textual'])
    _ENTITY_PRIORITY = ['classe_processual', 'data', 'valor_monetario', 'citacao_precedente', 'id_lei', 'id_precedente', 'parte_autor', 'parte_reu', 'parte_terceiro', 'nome_advogado', 'nome_juiz', 'serventuario', 'oab', 'processo_cnj', 'cpf_cnpj']

    def tokenize_and_label(example):
        text = example['text']
        spans = example['spans']
        char_labels = np.zeros(len(text), dtype=np.int32)
    # Entity labels in ascending priority order (last written wins on overlap).
    # More specific labels are written last so they overwrite broader ones.
        for label_name, span_list in spans.items():
            if label_name not in _SECTION_LABELS:
                continue
            lid = LABEL2ID.get(label_name, 0)
            for start, end in span_list:
                char_labels[start:min(end, len(text))] = lid
        remaining = {k: v for k, v in spans.items() if k not in _SECTION_LABELS}
        ordered = [l for l in _ENTITY_PRIORITY if l in remaining]
        ordered = ordered + [l for l in remaining if l not in _ENTITY_PRIORITY]
        for label_name in ordered:
            lid = LABEL2ID.get(label_name, 0)
            for start, end in remaining[label_name]:
                char_labels[start:min(end, len(text))] = lid  # Build char-level label array: default O=0
        enc = tokenizer(text, truncation=True, max_length=512, return_offsets_mapping=True)
        offsets = enc.pop('offset_mapping')
        token_labels = []  # Pass 1: section labels (lower priority)
        for start, end in offsets:
            if start == end:
                token_labels.append(-100)
            else:
                token_labels.append(int(char_labels[start]))
        enc['labels'] = token_labels
        return enc
    train_ds = raw_train.map(tokenize_and_label, remove_columns=['text', 'spans'])  # Pass 2: entity labels in explicit priority order (more specific last).
    val_ds = raw_val.map(tokenize_and_label, remove_columns=['text', 'spans'])  # Explicit order prevents non-determinism from dict insertion order.
    test_ds = raw_test.map(tokenize_and_label, remove_columns=['text', 'spans'])
    print('Tokenization done.')
    print(f'  Example token count: {len(train_ds[0]['input_ids'])}')  # catch-all
    dist = {ID2LABEL[l]: train_ds[0]['labels'].count(l) for l in range(NUM_LABELS) if train_ds[0]['labels'].count(l) > 0}
    # Label distribution in first doc (exclude O and -100)
    print(f'  Label dist (first doc): {dist}')  # special token
    return MODEL_NAME, test_ds, tokenizer, train_ds, val_ds


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. Fine-tune
    """)
    return


@app.cell
def _(
    ID2LABEL,
    LABEL2ID,
    MODEL_NAME,
    NUM_LABELS,
    SPAN_CLASS_NAMES,
    np,
    tokenizer,
    train_ds,
    val_ds,
):
    from transformers import (
        AutoModelForTokenClassification,
        DataCollatorForTokenClassification,
        TrainingArguments,
        Trainer,
    )
    from sklearn.metrics import classification_report

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
        ignore_mismatched_sizes=True,  # replaces 33-class PII head
        trust_remote_code=True,
    )

    def compute_metrics(p):
        logits, labels = p
        preds = np.argmax(logits, axis=-1)
        y_true, y_pred = [], []
        for pred_row, label_row in zip(preds, labels):
            for p_id, l_id in zip(pred_row, label_row):
                if l_id == -100:
                    continue
                y_true.append(ID2LABEL[l_id])
                y_pred.append(ID2LABEL[p_id])
        report = classification_report(
            y_true, y_pred,
            labels=[n for n in SPAN_CLASS_NAMES if n != 'O'],
            output_dict=True, zero_division=0,
        )
        macro = report.get('macro avg', {})
        # Return per-class F1 for key labels
        result = {
            'macro_f1':          macro.get('f1-score', 0),
            'macro_precision':   macro.get('precision', 0),
            'macro_recall':      macro.get('recall', 0),
        }
        for lbl in ['sec_dispositivo', 'sec_fundamentacao', 'sec_relatorio',
                    'processo_cnj', 'id_lei', 'id_precedente', 'data']:
            result[f'f1_{lbl}'] = report.get(lbl, {}).get('f1-score', 0)
        return result

    total_steps = (len(train_ds) // 16) * 3
    warmup_steps = max(50, total_steps // 10)

    training_args = TrainingArguments(
        output_dir="/content/decision_segmenter",
        num_train_epochs=3,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=2e-5,
        warmup_steps=warmup_steps,
        weight_decay=0.01,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='macro_f1',
        fp16=True,
        logging_steps=50,
        report_to='none',
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorForTokenClassification(tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    return classification_report, trainer


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. Evaluate on test set
    """)
    return


@app.cell
def _(ID2LABEL, SPAN_CLASS_NAMES, classification_report, np, test_ds, trainer):
    preds_out = trainer.predict(test_ds)
    preds  = np.argmax(preds_out.predictions, axis=-1)
    labels = preds_out.label_ids

    y_true, y_pred = [], []
    for pred_row, label_row in zip(preds, labels):
        for p_id, l_id in zip(pred_row, label_row):
            if l_id == -100:
                continue
            y_true.append(ID2LABEL[l_id])
            y_pred.append(ID2LABEL[p_id])

    print(classification_report(
        y_true, y_pred,
        labels=[n for n in SPAN_CLASS_NAMES if n != 'O'],
        zero_division=0,
    ))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 8. Save label_space.json + model
    """)
    return


@app.cell
def _(LABEL_SPACE, json, tokenizer, trainer):
    import shutil
    from google.colab import files
    MODEL_OUT = '/content/decision_segmenter_best'
    trainer.save_model(MODEL_OUT)
    tokenizer.save_pretrained(MODEL_OUT)
    label_space_path = f'{MODEL_OUT}/label_space.json'
    with open(label_space_path, 'w') as f:
    # Save label_space.json — required for opf eval / deployment
        json.dump(LABEL_SPACE, f, indent=2, ensure_ascii=False)
    print(f'Model + label_space.json saved to {MODEL_OUT}')
    shutil.make_archive('/content/decision_segmenter', 'zip', MODEL_OUT)
    files.download('/content/decision_segmenter.zip')
    print('Downloaded decision_segmenter.zip')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 9. Use with `opf train` (alternative to HuggingFace Trainer)

    The JSONL files produced by `scripts/prepare_privacy_filter_dataset.py` are also compatible with the official `opf` CLI:

    ```bash
    pip install opf
    opf train data/privacy_filter/train.jsonl \
        --validation-dataset data/privacy_filter/validation.jsonl \
        --label-space-json   data/privacy_filter/label_space.json \
        --output-dir         checkpoints/decision_segmenter
    ```

    The `opf` approach uses the model's own fine-tuning infrastructure (gradient checkpointing, mixed precision) without any HuggingFace Trainer setup.
    """)
    return


if __name__ == "__main__":
    app.run()
