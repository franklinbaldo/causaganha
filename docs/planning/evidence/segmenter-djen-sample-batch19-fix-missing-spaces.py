import difflib
import sys
from pathlib import Path

sys.path.insert(0, "/home/user/causaganha/src")
from segmenter_dataset.store import _text_element_to_labels  # noqa: E402
from xml.etree import ElementTree as ET  # noqa: E402


def build_stripped_to_tagged_map(tagged: str) -> list[int]:
    mapping = []
    in_tag = False
    for i, ch in enumerate(tagged):
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if in_tag:
            continue
        mapping.append(i)
    return mapping


def main(tagged_path: str, source_path: str, out_path: str) -> None:
    tagged = Path(tagged_path).read_text(encoding="utf-8")
    stripped = tagged.strip("\n\r\t ")
    root = ET.fromstring(f"<text>{stripped}</text>")
    reconstructed, _labels = _text_element_to_labels(root)
    source = Path(source_path).read_text(encoding="utf-8")

    if reconstructed == source:
        print("already identical, no fix needed")
        return

    mapping = build_stripped_to_tagged_map(stripped)

    sm = difflib.SequenceMatcher(None, reconstructed, source)
    # Each edit: (start_tagged_idx, end_tagged_idx_exclusive, replacement_text)
    edits: list[tuple[int, int, str]] = []
    problems = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            continue
        removed = reconstructed[i1:i2]
        added = source[j1:j2]
        if removed.strip() != "" or added.strip() != "":
            problems.append((tag, i1, i2, j1, j2, removed, added))
            continue
        if i1 == i2:
            # pure insertion
            start_tagged = mapping[i1] if i1 < len(mapping) else len(stripped)
            end_tagged = start_tagged
        else:
            start_tagged = mapping[i1]
            end_tagged = mapping[i2 - 1] + 1
            if end_tagged - start_tagged != i2 - i1:
                problems.append(("non-contiguous-removal", tag, i1, i2, j1, j2, removed, added))
                continue
        edits.append((start_tagged, end_tagged, added))

    if problems:
        print("UNRESOLVED (non-whitespace or non-contiguous) diffs:", problems)
        return

    edits.sort(key=lambda x: x[0], reverse=True)
    out = list(stripped)
    for start, end, text in edits:
        out[start:end] = list(text)
    fixed_stripped = "".join(out)

    root2 = ET.fromstring(f"<text>{fixed_stripped}</text>")
    reconstructed2, _ = _text_element_to_labels(root2)
    if reconstructed2 != source:
        print("STILL MISMATCHED after fix!")
        sm2 = difflib.SequenceMatcher(None, reconstructed2, source)
        for op in sm2.get_opcodes():
            if op[0] != "equal":
                print(op, repr(reconstructed2[op[1] : op[2]]), repr(source[op[3] : op[4]]))
        return

    Path(out_path).write_text(fixed_stripped, encoding="utf-8")
    print("FIXED and verified byte-identical. Wrote", out_path)


if __name__ == "__main__":
    main(*sys.argv[1:4])
