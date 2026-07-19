"""Semantic audit against annotation_guideline_v7.md (RFC 0012 §3.2)."""

from __future__ import annotations

import argparse
import re
from collections import defaultdict
from pathlib import Path

from segmenter_dataset.store import SegmenterDatasetStore


def find_anti_patterns(store_dir: Path) -> dict[str, list[dict[str, str]]]:
    store = SegmenterDatasetStore(store_dir)
    findings = defaultdict(list)

    for annotation in store.list_annotations():
        doc = store.read_document(annotation.document_id)
        text = doc.text
        cat_labels = defaultdict(list)
        for label in annotation.labels:
            cat_labels[label.category].append(label)
            span_text = text[label.start : label.end]

            if len(span_text) > 120:
                findings[doc.document_id].append(
                    {
                        "type": "long_anchor",
                        "span_text": span_text[:150] + "..." if len(span_text) > 150 else span_text,
                        "category": label.category,
                        "severity": "high",
                        "reason": f"span length {len(span_text)} > 120",
                    }
                )

            if label.category in ("resultado", "dispositivo_abertura"):
                lower_span = span_text.lower()
                if (
                    "decido" in lower_span
                    or "passo a decidir" in lower_span
                    or "fundamento e decido" in lower_span
                ):
                    findings[doc.document_id].append(
                        {
                            "type": "operative_on_reasoning_or_verb",
                            "span_text": span_text,
                            "category": label.category,
                            "severity": "high",
                            "reason": "tagged on potentially non-operative reasoning word",
                        }
                    )

            if (
                label.category == "capitulo_merito_inicio"
                and ("\n" in span_text or len(span_text.split(". ")) > 1)
                and len(span_text) > 60
            ):
                findings[doc.document_id].append(
                    {
                        "type": "capitulo_merito_on_prose",
                        "span_text": span_text,
                        "category": label.category,
                        "severity": "medium",
                        "reason": f"capitulo_merito looks like prose: {span_text!r}",
                    }
                )

            if label.category == "ref_processual" and doc.grouping.source_process_id:
                doc_proc = re.sub(r"\D", "", doc.grouping.source_process_id)
                span_digits = re.sub(r"\D", "", span_text)
                if (
                    len(span_digits) >= 10
                    and doc_proc not in span_digits
                    and span_digits not in doc_proc
                ):
                    findings[doc.document_id].append(
                        {
                            "type": "ref_processual_mismatch",
                            "span_text": span_text,
                            "category": label.category,
                            "severity": "high",
                            "reason": f"ref_processual digits do not match doc process {doc_proc}",
                        }
                    )

        for cat in ("fundamentacao_legal", "valor_condenacao"):
            if len(cat_labels[cat]) == 1:
                if cat == "valor_condenacao":
                    rs_count = text.count("R$")
                    if rs_count > 2:
                        findings[doc.document_id].append(
                            {
                                "type": "valor_condenacao_collapsed",
                                "span_text": "collapsed",
                                "category": cat,
                                "severity": "high",
                                "reason": f"only 1 {cat} tagged, but 'R$' appears >2 times",
                            }
                        )
                elif cat == "fundamentacao_legal":
                    art_count = text.lower().count("art.") + text.lower().count("artigo")
                    if art_count > 3:
                        findings[doc.document_id].append(
                            {
                                "type": "fundamentacao_legal_collapsed",
                                "span_text": "collapsed",
                                "category": cat,
                                "severity": "high",
                                "reason": f"only 1 {cat} tagged, but 'art.' appears >3 times",
                            }
                        )

        ann_path = store.annotations_dir / doc.document_id / f"{annotation.annotation_id}.xml"
        if ann_path.exists():
            xml_text = ann_path.read_text(encoding="utf-8")
            if "<ref_normativa>" in xml_text and "<fundamentacao_legal>" in xml_text:
                ref_norm_spans = [
                    match.span()
                    for match in re.finditer(r"<ref_normativa>(.*?)</ref_normativa>", xml_text)
                ]

                for match in re.finditer(
                    r"<fundamentacao_legal>(.*?)</fundamentacao_legal>", xml_text
                ):
                    fl_start, fl_end = match.span()
                    for rn_start, rn_end in ref_norm_spans:
                        if max(fl_start, rn_start) < min(fl_end, rn_end):
                            span = xml_text[max(fl_start, rn_start) : min(fl_end, rn_end)]
                            findings[doc.document_id].append(
                                {
                                    "type": "ref_normativa_overlap",
                                    "span_text": span,
                                    "category": "overlap",
                                    "severity": "high",
                                    "reason": "ref_normativa and fundamentacao_legal overlap",
                                }
                            )

        if doc.source.document_type == "acordao":
            disp_abs = [lbl for lbl in annotation.labels if lbl.category == "dispositivo_abertura"]
            voto_inicios = sorted(
                [lbl for lbl in annotation.labels if lbl.category == "voto_inicio"],
                key=lambda lbl: lbl.start,
            )
            voto_fims = sorted(
                [lbl for lbl in annotation.labels if lbl.category == "voto_fim"],
                key=lambda lbl: lbl.start,
            )

            if disp_abs and voto_inicios:
                for disp in disp_abs:
                    for _i, vi in enumerate(voto_inicios):
                        start = vi.start
                        fims_after = [vf.start for vf in voto_fims if vf.start > start]
                        end = fims_after[0] if fims_after else len(text)

                        if start <= disp.start < end:
                            findings[doc.document_id].append(
                                {
                                    "type": "dispositivo_inside_voto",
                                    "span_text": text[disp.start : disp.end],
                                    "category": "dispositivo_abertura",
                                    "severity": "high",
                                    "reason": f"tagged inside voto region ({start}-{end})",
                                }
                            )

    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store", type=Path, default=Path("data/segmenter"))
    args = parser.parse_args()

    findings = find_anti_patterns(args.store)
    print("Semantic Audit Findings:")
    for doc_id, doc_findings in findings.items():
        print(f"\nDocument: {doc_id}")
        for f in doc_findings:
            print(f"  - [{f['severity'].upper()}] {f['type']} on {f['category']}:")
            print(f"    Span: {f['span_text']!r}")
            print(f"    Reason: {f['reason']}")


if __name__ == "__main__":
    main()
