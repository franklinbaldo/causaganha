# /// script
# dependencies = ["datasets", "ibis-framework", "seqeval", "structlog", "transformers"]
# ///

# ARCHIVED (RFC 0001 section 3.5): legacy 3-label BIO (O/B-DISPOSITIVO/
# I-DISPOSITIVO) segmenter, superseded by the v7 26-class anchor-span
# ontology trained in notebooks/train_segmenter_colab.ipynb. Kept here as
# documentation of a prior approach, not a supported training path.

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
    # 🔏 CausaGanha — Privacy Filter: Dispositivo Span Detection

    Fine-tunes a Portuguese BERT model to detect the *dispositivo* section
    in Brazilian judicial decisions as a token-classification (NER) task.

    **No embeddings needed — runs on a free T4 in ~10 min.**

    **Steps:**
    1. Install dependencies
    2. Download `textos.parquet` from Internet Archive
    3. Generate JSONL dataset via `prepare_privacy_filter_dataset.py`
    4. Convert spans → BIO token labels
    5. Fine-tune `neuralmind/bert-base-portuguese-cased`
    6. Evaluate & save model
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 🔧 Install Dependencies
    """)
    return


@app.cell
def _():
    # packages added via marimo's package management: transformers datasets seqeval ibis-framework[duckdb] structlog !pip install -q transformers datasets seqeval ibis-framework[duckdb] structlog
    import os
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    print('✅ Dependencies installed')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 📥 Clone Repo & Download Data
    """)
    return


@app.cell
def _(subprocess):
    import os, urllib.request

    REPO_URL = 'https://github.com/franklinbaldo/causaganha.git'
    BRANCH = 'main'
    REPO_DIR = '/content/causaganha'

    if not os.path.exists(REPO_DIR):
        #! git clone --branch {BRANCH} --depth 1 {REPO_URL} {REPO_DIR}
        subprocess.call(['git', 'clone', '--branch', str(BRANCH), '--depth', '1', str(REPO_URL), str(REPO_DIR)])
    else:
        #! git -C {REPO_DIR} pull
        subprocess.call(['git', '-C', str(REPO_DIR), 'pull'])
    os.chdir(REPO_DIR)

    # Download textos.parquet from Internet Archive
    PARQUET_DIR = f'{REPO_DIR}/data/test_parquets'
    os.makedirs(PARQUET_DIR, exist_ok=True)
    TEXTOS_URL = 'https://archive.org/download/causaganha-test-parquets/textos.parquet'
    TEXTOS_PATH = f'{PARQUET_DIR}/textos.parquet'

    if not os.path.exists(TEXTOS_PATH):
        print('⬇️  Downloading textos.parquet from Internet Archive...')
        urllib.request.urlretrieve(TEXTOS_URL, TEXTOS_PATH)
        print(f'✅ Downloaded ({os.path.getsize(TEXTOS_PATH):,} bytes)')
    else:
        print(f'⏭️  Already exists: {TEXTOS_PATH}')
    return (REPO_DIR,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. 🏷️ Generate Dispositivo Span Dataset

    Runs `prepare_privacy_filter_dataset.py` — pure regex, no GPU.
    Outputs `data/privacy_filter/{train,validation,test}.jsonl`.
    """)
    return


@app.cell
def _(REPO_DIR, subprocess):
    import os
    import sys
    sys.path.insert(0, f'{REPO_DIR}/src')

    # Install the package so causaganha (KeywordClassifier) is importable by the
    # subprocess below (the script only adds scripts/ to sys.path, not src/).
    #! pip install -q -e {REPO_DIR} --no-deps
    subprocess.call(['pip', 'install', '-q', '-e', str(REPO_DIR), '--no-deps'])

    #! python {REPO_DIR}/scripts/prepare_privacy_filter_dataset.py
    subprocess.call(['python', f'{REPO_DIR}/scripts/prepare_privacy_filter_dataset.py'])

    for split in ['train', 'validation', 'test']:
        path = f'{REPO_DIR}/data/privacy_filter/{split}.jsonl'
        if os.path.exists(path):
            lines = sum(1 for _ in open(path))
            print(f'  ✅ {split}.jsonl — {lines} examples')
        else:
            print(f'  ❌ {split}.jsonl MISSING')
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. 🔄 Convert Spans → BIO Token Labels

    Converts character-level `{"text": ..., "spans": {"sec_dispositivo": [[start, end]]}}` to token-level BIO NER format for BERT fine-tuning.
    """)
    return


@app.cell
def _(REPO_DIR):
    import json
    from transformers import AutoTokenizer
    from datasets import Dataset, DatasetDict

    MODEL_NAME = 'neuralmind/bert-base-portuguese-cased'
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    LABEL2ID = {'O': 0, 'B-DISPOSITIVO': 1, 'I-DISPOSITIVO': 2}
    ID2LABEL = {v: k for k, v in LABEL2ID.items()}

    def load_jsonl(path):
        with open(path) as f:
            return [json.loads(l) for l in f]

    def char_spans_to_bio(example):
        text = example['text']
        spans = example.get('spans', {}).get('sec_dispositivo', [])

        # Build a character-level label array
        char_labels = ['O'] * len(text)
        for start, end in spans:
            for i in range(start, min(end, len(text))):
                char_labels[i] = 'B-DISPOSITIVO' if i == start else 'I-DISPOSITIVO'

        # Tokenize and align labels to sub-word tokens
        enc = tokenizer(text, truncation=True, max_length=512,
                        return_offsets_mapping=True)
        token_labels = []
        for start, end in enc['offset_mapping']:
            if start == end:  # special token
                token_labels.append(-100)
            else:
                # Use the label of the first character of this token
                token_labels.append(LABEL2ID[char_labels[start]])

        enc['labels'] = token_labels
        enc.pop('offset_mapping')
        return enc

    splits = {}
    for split in ['train', 'validation', 'test']:
        path = f'{REPO_DIR}/data/privacy_filter/{split}.jsonl'
        raw = load_jsonl(path)
        ds = Dataset.from_list(raw)
        splits[split] = ds.map(char_spans_to_bio, remove_columns=ds.column_names)
        print(f'  {split}: {len(splits[split])} examples tokenized')

    dataset = DatasetDict(splits)
    print('\n✅ Dataset ready:', dataset)
    return ID2LABEL, LABEL2ID, MODEL_NAME, dataset, tokenizer


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. 🏋️ Fine-tune BERTimbau
    """)
    return


@app.cell
def _(ID2LABEL, LABEL2ID, MODEL_NAME, dataset, tokenizer):
    from transformers import (
        AutoModelForTokenClassification,
        TrainingArguments,
        Trainer,
        DataCollatorForTokenClassification,
    )
    import numpy as np
    from seqeval.metrics import classification_report as seq_report

    model = AutoModelForTokenClassification.from_pretrained(
        MODEL_NAME,
        num_labels=len(LABEL2ID),
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )

    def compute_metrics(p):
        preds, labels = p
        preds = np.argmax(preds, axis=2)
        true_seqs, pred_seqs = [], []
        for pred_row, label_row in zip(preds, labels):
            true_seq, pred_seq = [], []
            for p_id, l_id in zip(pred_row, label_row):
                if l_id == -100:
                    continue
                true_seq.append(ID2LABEL[l_id])
                pred_seq.append(ID2LABEL[p_id])
            true_seqs.append(true_seq)
            pred_seqs.append(pred_seq)
        report = seq_report(true_seqs, pred_seqs, output_dict=True, zero_division=0)
        return {
            'precision': report['DISPOSITIVO']['precision'],
            'recall': report['DISPOSITIVO']['recall'],
            'f1': report['DISPOSITIVO']['f1-score'],
        }

    args = TrainingArguments(
        output_dir='/content/privacy-filter-dispositivo',
        num_train_epochs=5,
        per_device_train_batch_size=16,
        per_device_eval_batch_size=32,
        learning_rate=3e-5,
        warmup_ratio=0.1,
        weight_decay=0.01,
        eval_strategy='epoch',
        save_strategy='epoch',
        load_best_model_at_end=True,
        metric_for_best_model='f1',
        logging_steps=20,
        fp16=True,
        report_to='none',
    )

    collator = DataCollatorForTokenClassification(tokenizer)
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=dataset['train'],
        eval_dataset=dataset['validation'],
        tokenizer=tokenizer,
        data_collator=collator,
        compute_metrics=compute_metrics,
    )

    print('🏋️  Training...')
    trainer.train()
    print('✅ Training complete')
    return (trainer,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. ✅ Evaluate on Test Set
    """)
    return


@app.cell
def _(dataset, trainer):
    results = trainer.evaluate(dataset['test'])
    print('\n📊 Test set results:')
    print(f"  Precision : {results['eval_precision']:.4f}")
    print(f"  Recall    : {results['eval_recall']:.4f}")
    print(f"  F1        : {results['eval_f1']:.4f}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. 📦 Save & Download Model
    """)
    return


@app.cell
def _(tokenizer, trainer):
    import shutil
    from google.colab import files

    SAVE_DIR = '/content/privacy-filter-dispositivo-final'
    trainer.save_model(SAVE_DIR)
    tokenizer.save_pretrained(SAVE_DIR)
    print(f'✅ Model saved to {SAVE_DIR}')

    # Zip and download
    zip_path = '/content/privacy_filter_dispositivo.zip'
    shutil.make_archive('/content/privacy_filter_dispositivo', 'zip', SAVE_DIR)
    files.download(zip_path)
    print('📦 Downloaded privacy_filter_dispositivo.zip')

    # Show how to use it
    print('''
    To use locally:
      from transformers import pipeline
      ner = pipeline('token-classification', model=SAVE_DIR, aggregation_strategy='simple')
      ner("DISPOSITIVO: Julgo procedente o pedido.")
    ''')
    return


if __name__ == "__main__":
    app.run()
