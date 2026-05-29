# /// script
# dependencies = ["-", "classify"]
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
    # 🧠 CausaGanha — ML Document Classifier Training

    Trains two sklearn ensembles (document type + procedural class) on top of
    [EmbeddingGemma-300M](https://huggingface.co/google/embeddinggemma-300m) embeddings.

    **Steps:**
    1. Clone the repo & install deps
    2. Download parquet data from Internet Archive
    3. Preview data
    4. Compute embeddings
    5. Train classifiers
    6. Evaluate with invariant winner metrics (PR #717)
    7. Download trained models
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. 🔧 Setup: Clone Repo & Install Dependencies
    """)
    return


@app.cell
def _():
    # --- Config ---
    REPO_URL = "https://github.com/franklinbaldo/causaganha.git"
    BRANCH = "feat/embedder-smart-truncate-and-privacy-dataset-v2"
    REPO_DIR = "/content/causaganha"
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
    return (os,)


@app.cell
def _(subprocess):
    # Install uv
    #! curl -LsSf https://astral.sh/uv/install.sh | sh
    subprocess.call(['curl', '-LsSf', 'https://astral.sh/uv/install.sh', '|', 'sh'])
    import os
    os.environ["PATH"] = f"/root/.local/bin:{os.environ['PATH']}"
    #! uv --version
    subprocess.call(['uv', '--version'])
    return (os,)


@app.cell
def _():
    # Install core deps + classify group (sentence-transformers, sklearn, joblib)
    # packages added via marimo's package management: .[embeddings] classify !uv pip install --system -e ".[embeddings]" --group classify
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. 📂 Download Data from Internet Archive

    Downloads the parquet files directly from the CausaGanha dataset on Internet Archive.
    No manual upload needed.

    Source: https://archive.org/details/causaganha-test-parquets
    """)
    return


@app.cell
def _(REPO_DIR):
    import os, urllib.request

    PARQUET_DIR = f"{REPO_DIR}/data/test_parquets"
    os.makedirs(PARQUET_DIR, exist_ok=True)

    FILES = {
        "textos.parquet": "https://archive.org/download/causaganha-test-parquets/textos.parquet",
        "classificacoes_documentos.parquet": "https://archive.org/download/causaganha-test-parquets/classificacoes_documentos.parquet",
    }

    for fname, url in FILES.items():
        dest = os.path.join(PARQUET_DIR, fname)
        if os.path.exists(dest):
            print(f"  ⏭️  Already exists: {fname}")
            continue
        print(f"  ⬇️  Downloading {fname} ...")
        urllib.request.urlretrieve(url, dest)
        size = os.path.getsize(dest)
        print(f"  ✅ {fname} ({size:,} bytes)")

    print("\nAll files ready:")
    for fname in FILES:
        path = os.path.join(PARQUET_DIR, fname)
        status = "✅" if os.path.exists(path) else "❌ MISSING"
        print(f"  {status} {path}")
    return PARQUET_DIR, os


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. 🔍 Quick Data Preview
    """)
    return


@app.cell
def _(PARQUET_DIR):
    import ibis
    from pathlib import Path

    parquet_dir = Path(PARQUET_DIR)
    classif_t = ibis.read_parquet(parquet_dir / "classificacoes_documentos.parquet")
    textos_t  = ibis.read_parquet(parquet_dir / "textos.parquet")

    print(f"classificacoes_documentos: {classif_t.count().execute():,} rows")
    print(f"textos:                    {textos_t.count().execute():,} rows")
    print("\nclassificacoes_documentos schema:"); print(classif_t.schema())
    print("\ntextos schema:"); print(textos_t.schema())
    return classif_t, textos_t


@app.cell
def _(classif_t, textos_t):
    merged_t = (
        classif_t.join(textos_t, classif_t.id == textos_t.id)
        .select(
            classif_t.id,
            classif_t.document_type,
            classif_t.procedural_class,
            textos_t.texto,
        )
        .filter(textos_t.texto.notnull())
    )
    merged_df = merged_t.execute()
    print(f"Total merged samples: {len(merged_df):,}")
    print("\n📊 document_type distribution:")
    print(merged_df["document_type"].value_counts().head(20))
    print("\n📊 procedural_class distribution:")
    print(merged_df["procedural_class"].value_counts().head(20))
    return (merged_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. 🚀 Compute Embeddings (ApiEmbedder — OpenRouter/Jina/Gemini)
    """)
    return


@app.cell
def _(REPO_DIR):
    import sys
    sys.path.insert(0, f"{REPO_DIR}/src")

    import structlog
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(20))
    return


@app.cell
def _(os):
    # --- Configure API Keys ---
    try:
        from google.colab import userdata
        for key in ['OPENROUTER_API_KEY', 'JINA_API_KEY', 'GEMINI_API_KEY']:
            val = userdata.get(key) if hasattr(userdata, 'get') else None
            if val:
                os.environ[key] = val
    except Exception:
        pass
    if not os.environ.get('OPENROUTER_API_KEY'):
        from getpass import getpass
    # Prompt securely if keys are missing from Secrets
        key = getpass('Please enter your OpenRouter API Key (press Enter to skip): ').strip()
        if key:
            os.environ['OPENROUTER_API_KEY'] = key
    if not os.environ.get('JINA_API_KEY') and (not os.environ.get('OPENROUTER_API_KEY')):
        key = getpass('Please enter your Jina API Key (optional if OpenRouter is set): ').strip()
        if key:
            os.environ['JINA_API_KEY'] = key
    print('✅ API Keys configured: ', f'OPENROUTER_API_KEY={('set' if os.environ.get('OPENROUTER_API_KEY') else 'not set')}, ', f'JINA_API_KEY={('set' if os.environ.get('JINA_API_KEY') else 'not set')}')
    return


@app.cell
def _(merged_df, os):
    from causaganha.analysis.api_embedder import ApiEmbedder
    import numpy as np

    # Default to 'openrouter' with 'nvidia/llama-nemotron-embed-vl-1b-v2:free' (2048-dim, FREE!)
    # if OPENROUTER_API_KEY is available, otherwise Jina or Gemini.
    provider = "openrouter" if os.environ.get("OPENROUTER_API_KEY") else "jina"
    model = "nvidia/llama-nemotron-embed-vl-1b-v2:free" if provider == "openrouter" else None

    print(f"🚀 Instantiating ApiEmbedder with provider={provider}, model={model}")
    embedder = ApiEmbedder(provider=provider, model=model)

    texts = merged_df["texto"].tolist()
    print(f"Computing embeddings for {len(texts):,} texts using {provider}...")

    # ApiEmbedder handles internal batching and rate limits automatically!
    embeddings = embedder.embed(texts, is_query=False, normalize=True)
    print(f"✅ Embeddings computed successfully! Shape: {embeddings.shape}")
    return (embeddings,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. 🏋️ Train Classifiers
    """)
    return


@app.cell
def _(embeddings, merged_df):
    from causaganha.analysis.ml_document_classifier import (
        DEFAULT_DOC_TYPE_PATH,
        DEFAULT_PROC_CLASS_PATH,
        MLDocumentEnsemble,
    )

    print("🏋️  Training document_type ensemble...")
    doc_type_ensemble = MLDocumentEnsemble(
        target_col="document_type", ensemble_path=DEFAULT_DOC_TYPE_PATH
    )
    doc_type_ensemble.train(merged_df, embeddings)
    doc_type_ensemble.save()
    print(f"   ✅ Saved to {DEFAULT_DOC_TYPE_PATH}")

    print("🏋️  Training procedural_class ensemble...")
    proc_class_ensemble = MLDocumentEnsemble(
        target_col="procedural_class", ensemble_path=DEFAULT_PROC_CLASS_PATH
    )
    proc_class_ensemble.train(merged_df, embeddings)
    proc_class_ensemble.save()
    print(f"   ✅ Saved to {DEFAULT_PROC_CLASS_PATH}")
    return DEFAULT_DOC_TYPE_PATH, DEFAULT_PROC_CLASS_PATH, MLDocumentEnsemble


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 6. ✅ Evaluate — Invariant Winner Metrics (PR #717)

    Uses the gate + conditional decomposition from PR #717:
    - **Gate**: is this a ratable merits decision? (vs interlocutória/despacho)
    - **Conditional**: given ratable, which polo won? (A / P / draw)

    Falls back to `classification_report` if the parquet lacks `outcome`/`recorrente_polo` columns.
    """)
    return


@app.cell
def _(
    DEFAULT_DOC_TYPE_PATH,
    DEFAULT_PROC_CLASS_PATH,
    MLDocumentEnsemble,
    embeddings,
    merged_df,
):
    from causaganha.analysis.benchmark_metrics import evaluate_invariant
    from sklearn.metrics import classification_report
    loaded_doc_type = MLDocumentEnsemble.load(DEFAULT_DOC_TYPE_PATH)
    loaded_proc_class = MLDocumentEnsemble.load(DEFAULT_PROC_CLASS_PATH)
    sample_emb = embeddings[0]
    pred_doc = loaded_doc_type.predict(sample_emb)
    pred_proc = loaded_proc_class.predict(sample_emb)
    # Quick sanity check
    print('🧪 Sample prediction:')
    print(f'   True  doc_type: {merged_df.iloc[0]['document_type']}')
    print(f'   Pred  doc_type: {pred_doc}')
    print(f'   True  proc_cls: {merged_df.iloc[0]['procedural_class']}')
    print(f'   Pred  proc_cls: {pred_proc}')
    if 'outcome' in merged_df.columns and 'recorrente_polo' in merged_df.columns:
        gold_pairs = list(zip(merged_df['outcome'], merged_df['recorrente_polo'].where(merged_df['recorrente_polo'].notna(), None)))
        preds_outcome = [loaded_doc_type.predict(embeddings[i]) for i in range(len(embeddings))]
        pred_pairs = [(p, None) for p in preds_outcome]
    # --- Invariant winner evaluation (PR #717) ---
        report = evaluate_invariant(gold_pairs, pred_pairs)
        print('\n📊 Invariant Winner Evaluation (gate + conditional):')
        g = report.gate
        print(f'  Gate  — acc={g.accuracy:.3f}  P={g.precision:.3f}  R={g.recall:.3f}  F1={g.f1:.3f}  ratable={g.support_ratable}/{g.total}')
        c = report.conditional
        print(f'  Cond  — acc={c.accuracy:.3f}  n_scored={c.n_scored}')
        for polo, m in c.per_polo.items():
            print(f'    {polo}: P={m['precision']:.2f}  R={m['recall']:.2f}  F1={m['f1']:.2f}  n={m['support']}')
    else:
        print('\nℹ️  No outcome/recorrente_polo columns — using classification_report fallback.')
        preds_doc = [loaded_doc_type.predict(embeddings[i]) for i in range(len(embeddings))]
        print('\n📊 In-sample evaluation (document_type):')
        print(classification_report(merged_df['document_type'], preds_doc, zero_division=0))
        preds_proc = [loaded_proc_class.predict(embeddings[i]) for i in range(len(embeddings))]
        print('\n📊 In-sample evaluation (procedural_class):')
        print(classification_report(merged_df['procedural_class'], preds_proc, zero_division=0))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 7. 📦 Download Trained Models
    """)
    return


@app.cell
def _(DEFAULT_DOC_TYPE_PATH, DEFAULT_PROC_CLASS_PATH, os):
    import shutil
    from google.colab import files
    print('Model files:')
    for p in [DEFAULT_DOC_TYPE_PATH, DEFAULT_PROC_CLASS_PATH]:
        exists = os.path.exists(p)
        size_1 = os.path.getsize(p) if exists else 0
        print(f'  {('✅' if exists else '❌')} {p} ({size_1:,} bytes)')
    shutil.make_archive('/content/causaganha_models', 'zip', os.path.dirname(DEFAULT_DOC_TYPE_PATH))
    files.download('/content/causaganha_models.zip')
    print('\n📦 Downloaded causaganha_models.zip')
    return


if __name__ == "__main__":
    app.run()
