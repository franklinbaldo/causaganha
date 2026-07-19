# Kaggle + Colab CLI: real GPU runs from this machine

This documents how to actually dispatch a real GPU run (training, inference,
any script needing CUDA) from this dev machine, without a local GPU. Written
after using it for real to validate `scripts/run_segmenter_training.py`
against a real `opf train` (see PR #845 — this is exactly how that bug,
`opf train`'s missing `--seed` flag, was caught).

## Where the CLIs live

Both CLIs are installed and authenticated inside **WSL** (`Debian` distro),
not in the native Windows/git-bash shell. Reach them with:

```bash
wsl -d Debian -- bash -lc "kaggle <command>"
wsl -d Debian -- bash -lc "colab <command>"
```

The `-lc` (login shell) matters — a plain `wsl -- kaggle ...` won't source
`~/.profile`/`~/.bashrc`, and `kaggle`/`colab` (installed via `pip install
--user`, living in `~/.local/bin`) won't be on `PATH` without it.

Check auth status:

```bash
wsl -d Debian -- bash -lc "kaggle config view"          # shows username + auth_method
wsl -d Debian -- bash -lc "kaggle kernels list --mine"   # confirms the token actually works
wsl -d Debian -- bash -lc "colab version; colab sessions"
```

## Kaggle: kernels (the reusable pattern)

Kaggle kernels are the right tool for anything that needs to **run to
completion unattended** (a multi-epoch training loop, a batch job) — as
opposed to Colab's session model, better suited to quick interactive checks
(see below).

### 1. Write the kernel script + metadata

A kernel needs two files in one folder: the script itself, and
`kernel-metadata.json`. Generate the template once with:

```bash
wsl -d Debian -- bash -lc "cd <folder> && kaggle kernels init -p ."
```

then fill it in:

```json
{
  "id": "franklinbaldo/<kernel-slug>",
  "title": "<title>",
  "code_file": "<script>.py",
  "language": "python",
  "kernel_type": "script",
  "is_private": "true",
  "enable_gpu": "true",
  "enable_internet": "true",
  "dataset_sources": [],
  "kernel_sources": []
}
```

Keep `is_private: true` unless there's a specific reason to publish. Kaggle's
default GPU image already ships `torch` + CUDA; you only need to `pip
install` whatever this repo needs on top (e.g. `opf`).

**The script doesn't need a separate uploaded dataset** if the code being
tested is already on GitHub: just have the script `git clone` the relevant
branch/commit at the top (kernels have internet access with
`enable_internet: true`), then `pip install -e .` the checkout. This is what
the PR #845 validation kernel does — see
`scripts/run_segmenter_training.py`'s own docstring for the exact pattern,
or reconstruct it from this doc's example below.

### 2. Push and poll

```bash
wsl -d Debian -- bash -lc "cd <folder> && kaggle kernels push -p ."
wsl -d Debian -- bash -lc "kaggle kernels status franklinbaldo/<kernel-slug>"
```

`push` creates a new **version** of the kernel each time (version 1, 2, 3…)
and starts it running immediately — there's no separate "run" step. Status
is one of `RUNNING`, `COMPLETE`, `ERROR`. A GPU kernel with a small workload
(smoke test scale, not a real multi-epoch run) typically finishes in
30–90 seconds; poll every couple of minutes rather than tightly.

### 3. Pull the log

```bash
wsl -d Debian -- bash -lc "mkdir -p <outdir> && cd <outdir> && kaggle kernels output franklinbaldo/<kernel-slug> -p ."
```

**Gotcha:** `kernels output` downloads *everything* left in `/kaggle/working`
as output artifacts — if your script `git clone`s the whole repo there (as
the example below does) and doesn't clean up, this download pulls the
**entire repository tree** (hundreds of files) alongside the one log file
you actually want. It still works, just budget a minute or two and don't
read the download command's own stdout (it's a "file downloaded" line per
file) — go straight to reading the log:

```bash
wsl -d Debian -- bash -lc "cat <outdir>/<kernel-slug>.log"
```

The log is a **JSON-lines-ish array** (one `{"stream_name":...,"data":...}`
object per output chunk, comma-separated, not one-object-per-line) — `cat`
and read it directly rather than trying to `jq` each line individually.

To avoid the giant download next time, have the script `shutil.rmtree()` the
cloned repo (keeping only what you actually need to inspect) right before
it exits.

## Colab CLI: session commands (quicker, interactive)

```bash
wsl -d Debian -- bash -lc "colab sessions"                 # list active sessions
wsl -d Debian -- bash -lc "colab new"                       # start a new session
wsl -d Debian -- bash -lc "colab exec <session> 'python3 -c \"import torch; print(torch.cuda.is_available())\"'"
wsl -d Debian -- bash -lc "colab upload <session> <local> <remote>"
wsl -d Debian -- bash -lc "colab run <script.py>"           # fresh VM, run, release
wsl -d Debian -- bash -lc "colab stop <session>"
```

Auth is OAuth2, stored at `~/.config/colab-cli/token.json` (refreshed
automatically; re-run `colab new` if it's ever expired/missing). Prefer this
over Kaggle for a single quick check (`does this import work with a real
GPU?`) — `colab run` is a one-shot fresh-VM script run with no kernel
bookkeeping. Prefer Kaggle for anything that needs to run unattended for a
while, since a kernel keeps running and can be polled/pulled after you've
moved on to other work.

## Worked example: the PR #845 validation kernel

The kernel that found (and later confirmed the fix for) the `opf train
--seed` bug built a small synthetic-but-schema-valid dataset release
in-process (reusing `tests/segmenter_dataset/conftest.py`'s fixture
helpers — real corpus release-building is blocked by RFC 0012's gates until
some of the 61 real ingested documents get adjudicated), exported it via
`segmenter_dataset.opf_export.export_release_for_training`, then invoked
`scripts/run_segmenter_training.py`'s actual CLI. This is the reusable shape
for "does this trainer/eval script actually work against real `opf` +
GPU" — swap in a real release export once real val/test data exists.
