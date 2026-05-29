"""Embedding-based false positive filter for silver span labels.

For each label a centroid is precomputed from confirmed-FP context windows.
During dataset preparation, candidate spans are rejected when their context
embedding has cosine similarity > threshold to the label's FP centroid.

This complements rule-based heuristics: instead of ever-growing negative
lookaheads, we maintain a catalog of confirmed FP examples and let the
embedding model generalise to unseen FPs.

Usage::

    filt = FPCentroidFilter()
    filt.fit_from_catalog()        # embeds hardcoded FP catalog
    # or load precomputed centroids:
    filt.load("data/privacy_filter/fp_centroids.pkl")

    if not filt.is_fp("id_precedente", text, span_start, span_end):
        ...  # accept span
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np


# ---------------------------------------------------------------------------
# Confirmed false-positive context windows
# Each string is 80-120 chars around the span that was wrongly labeled.
# Collected from audit of TJRO 2025 data (January 2025 sample).
# ---------------------------------------------------------------------------

FP_CATALOG: dict[str, list[str]] = {
    # id_precedente: short abbreviations (RO, RE, MS) matching state/address/OAB,
    # not court-case citation identifiers.
    "id_precedente": [
        # "RO" as city/state abbreviation in signature block
        "trânsito em julgado, arquive-se. Cacoal/RO, 08/01/2025 Juiz de Direito",
        "Porto Velho/RO, 8 de janeiro de 2025. Marisa de Almeida Juiz(a) de Direito",
        "Intimem-se. Vilhena-RO, 03/01/2025 Vinicius de Almeida Ferreira Juiz de Direito",
        "Jaru - RO, quarta-feira, 8 de janeiro de 2025. Leonardo Leite",
        "Sao Francisco do Guapore/RO, datado eletronicamente. Juiz de Direito",
        "Pimenta Bueno/RO, 14 de janeiro de 2025. Juiz de Direito",
        "Machadinho d'Oeste/RO, 8 de janeiro de 2025. Juiz de Direito Substituto",
        "manifestacao, arquive-se. Pimenta Bueno/RO, 14 de janeiro de 2025",
        "diretrizes Judiciais. Intimem-se. Vilhena-RO, 03/01/2025",
        "arquive-se. Registre-se. Intimem-se. Porto Velho/RO, 8 de janeiro de 2025",
        # "RO" in email/URL context
        "CEP 76801-235, Porto Velho, cpefamilia@tjro.jus.br Processo n.",
        "Setor 2, CEP 76890-000, Jaru, cacjaru@tjro.jus.br Telefone: (69)",
        "resultados no sitio eletronico http://pje.tjro.jus.br/pg/ConsultaPu",
        # "RO" in OAB registration number
        "BRENDA RODRIGUES DOS SANTOS - RO8648, CAMILA BORTULUZZI HENRICHSEN",
        "ARYANE KELLY SILVA SAMPAIO, OAB no RO8625 Requerido(a) ENERGISA",
        "SAMIA PRADO DOS SANTOS, OAB no RO3604 SENTENCA M. I.",
        # "RO" in street address
        "AVENIDA 7 DE SETEMBRO 5661 JARDIM TROPICAL - RO 5661 76800-000",
        "SICOOB CENTRO, RUA MANOEL FRANCO 1 RO, Ariquemes",
        # "ro" inside Portuguese words (dobro, retro, outro...)
        "ressarcimento dos danos materiais em dobro. Intimado, o embargado",
        "dano material deve ser restituido em dobro, pois foram cobrados",
        "o que faz jus a receber a devolucao, em dobro, das quantias",
    ],
    # parte_reu / parte_autor: lawyer name captured from "ADVOGADO DO X:" context.
    # The span text (a name) is identical to a TP, but the context reveals it's
    # the lawyer, not the party.
    "parte_reu": [
        "ADVOGADO DO REQUERIDO: DENNER DE BARROS E MASCARENHAS BARBOSA, OAB no RO7828",
        "ADVOGADO DO REQUERIDO: PROCURADORIA GERAL DO ESTADO DE RONDONIA SENTENCA",
        "ADVOGADO DO REU: CASSIO ROBERTO ALMEIDA DE BARROS, OAB no DF26296",
        "ADVOGADOS DO REU: RENATO CHAGAS CORREA DA SILVA, OAB no DF45892",
        "ADVOGADO DO REQUERIDO: SAMIA PRADO DOS SANTOS, OAB no RO3604 SENTENCA",
        "ADVOGADO DO EMBARGADO: PROCURADORIA GERAL DO MUNICIPIO DE ARIQUEMES SENTENCA",
        "ADVOGADO DO REQUERIDO: PROCURADORIA FEDERAL EM RONDONIA - PF/RO SENTENCA",
    ],
    "parte_autor": [
        "ADVOGADO DO AUTOR: PEDRO HENRIQUE GOMES DE OLIVEIRA, OAB no RO12345",
        "ADVOGADO DO REQUERENTE: DEFENSORIA PUBLICA DO ESTADO DE RONDONIA",
        "ADVOGADOS DO EXEQUENTE: MANOEL FERNANDES DA SILVA, OAB no RO9876",
    ],
}

# Cosine similarity threshold per label: spans above threshold are rejected.
# Lower = more permissive (keeps more), higher = stricter (rejects more).
# parte_reu/parte_autor set to 0.97 (effectively disabled) because their TP
# and FP contexts are structurally too similar for a small multilingual model
# to separate — use the rule-based ADVOGADO check in _segment() instead.
_THRESHOLDS: dict[str, float] = {
    "id_precedente": 0.78,
    "parte_reu": 0.97,
    "parte_autor": 0.97,
}

_CONTEXT_CHARS = 100  # chars of context before/after span to embed


class FPCentroidFilter:
    """Cosine-similarity FP filter using precomputed per-label FP centroids."""

    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2") -> None:
        """Initialise with a sentence-transformers model name."""
        self._model_name = model_name
        self._model = None  # lazy-loaded on first use
        self._centroids: dict[str, np.ndarray] = {}
        self._thresholds: dict[str, float] = dict(_THRESHOLDS)

    def fit_from_catalog(self) -> None:
        """Embed and centroid all FP examples in FP_CATALOG."""
        model = self._get_model()
        for label, examples in FP_CATALOG.items():
            embs = model.encode(examples, normalize_embeddings=True, show_progress_bar=False)
            centroid: np.ndarray = embs.mean(axis=0)
            norm = float(np.linalg.norm(centroid))
            if norm > 0:
                centroid = centroid / norm
            self._centroids[label] = centroid

    def save(self, path: Path | str) -> None:
        """Persist centroids + thresholds to a pickle file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as f:
            pickle.dump(
                {
                    "centroids": self._centroids,
                    "thresholds": self._thresholds,
                    "model_name": self._model_name,
                },
                f,
            )

    def load(self, path: Path | str) -> None:
        """Restore centroids + thresholds from a pickle file."""
        with Path(path).open("rb") as f:
            data = pickle.load(f)  # noqa: S301
        self._centroids = data["centroids"]
        self._thresholds = data.get("thresholds", _THRESHOLDS)
        self._model_name = data.get("model_name", self._model_name)

    def is_fp(self, label: str, text: str, span_start: int, span_end: int) -> bool:
        """Return True if this span+context is too similar to the FP centroid."""
        if label not in self._centroids:
            return False
        context = text[max(0, span_start - _CONTEXT_CHARS) : span_end + _CONTEXT_CHARS]
        emb: np.ndarray = self._get_model().encode([context], normalize_embeddings=True)[0]
        sim = float(np.dot(emb, self._centroids[label]))
        return sim > self._thresholds[label]

    def bulk_is_fp(
        self,
        label: str,
        text: str,
        spans: list[tuple[int, int]],
    ) -> list[bool]:
        """Batch FP check -- embeds all context windows in one model call."""
        if label not in self._centroids or not spans:
            return [False] * len(spans)
        contexts = [text[max(0, s - _CONTEXT_CHARS) : e + _CONTEXT_CHARS] for s, e in spans]
        embs: np.ndarray = self._get_model().encode(
            contexts, normalize_embeddings=True, show_progress_bar=False
        )
        centroid = self._centroids[label]
        sims: np.ndarray = embs @ centroid
        thr = self._thresholds.get(label, 0.80)
        return [float(s) > thr for s in sims]

    def _get_model(self):  # type: ignore[return]
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415

            self._model = SentenceTransformer(self._model_name)
        return self._model
