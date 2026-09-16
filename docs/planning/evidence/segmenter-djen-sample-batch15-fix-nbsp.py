"""Ad-hoc NBSP-restoration tool for djen_sample Technique 1 annotations
whose subagent transcription silently normalized non-breaking spaces
(U+00A0) to regular spaces during tagging -- a verbatim-fidelity mismatch
that batch4/13 fixed with a single manual substring patch, but which this
round (batch15) hit pervasively (12 and 33 occurrences in a single
document, not one isolated instance). Diffs the reconstructed
(tags-stripped) tagged text against the source character-by-character,
refuses to touch anything if a non-NBSP-related difference is found, then
reinserts the correct bytes into the tagged XML at the mapped positions
and re-verifies byte-identical reconstruction before the caller writes
the fix. Not a production script -- scratch tool for this round's
candidate ingestion, kept as evidence for reuse by a future batch that
hits the same pervasive-NBSP shape.
"""

from __future__ import annotations

import re
import difflib
from pathlib import Path

TAG_RE = re.compile(r"</?[a-zA-Z_][a-zA-Z0-9_]*(?:\s+[^>]*)?>")

def strip_tags_with_map(tagged: str):
    """Return (stripped_text, map) where map[i] = index in `tagged` of the
    character that produced stripped_text[i]."""
    out_chars = []
    out_map = []
    i = 0
    n = len(tagged)
    while i < n:
        m = TAG_RE.match(tagged, i)
        if m:
            i = m.end()
            continue
        out_chars.append(tagged[i])
        out_map.append(i)
        i += 1
    return "".join(out_chars), out_map

def fix_document(doc_id: str) -> bool:
    src_path = Path(f"/tmp/claude-0/-home-user-causaganha/cf063d62-1c40-5ace-a8a9-1dd0e1e71690/scratchpad/batch15_docs/{doc_id}.txt")
    tagged_path = Path(f"/tmp/claude-0/-home-user-causaganha/cf063d62-1c40-5ace-a8a9-1dd0e1e71690/scratchpad/batch15_tagged/{doc_id}.txt")
    src = src_path.read_text(encoding="utf-8")
    tagged = tagged_path.read_text(encoding="utf-8")
    reconstructed, pos_map = strip_tags_with_map(tagged)

    sm = difflib.SequenceMatcher(None, src, reconstructed, autojunk=False)
    opcodes = sm.get_opcodes()

    # Verify every non-equal opcode is a pure NBSP issue before touching anything.
    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "equal":
            continue
        src_chunk = src[i1:i2]
        recon_chunk = reconstructed[j1:j2]
        if tag == "replace":
            ok = src_chunk.replace("\xa0", " ") == recon_chunk and set(src_chunk) <= {"\xa0", " "}
        elif tag == "delete":
            ok = "\xa0" in src_chunk and set(src_chunk) <= {"\xa0", " ", "\n"}
        elif tag == "insert":
            ok = False
        else:
            ok = False
        if not ok:
            print(f"{doc_id}: UNEXPECTED non-NBSP diff, aborting auto-fix:", tag, repr(src_chunk), repr(recon_chunk))
            return False

    # Apply fixes to the tagged string, from the end backwards so earlier
    # offsets in pos_map stay valid.
    tagged_chars = list(tagged)
    for tag, i1, i2, j1, j2 in reversed(opcodes):
        if tag == "equal":
            continue
        src_chunk = src[i1:i2]
        if tag == "replace":
            # j2-j1 characters in tagged (mapped via pos_map[j1:j2]) get replaced
            # 1:1 with src_chunk (same length by construction).
            assert (j2 - j1) == len(src_chunk)
            for k in range(j2 - j1):
                tpos = pos_map[j1 + k]
                tagged_chars[tpos] = src_chunk[k]
        elif tag == "delete":
            # src has extra NBSP(s) not present in reconstructed at all.
            # Insert them right before the tagged-position of reconstructed[j1]
            # (or at end of tagged text if j1 == len(reconstructed)).
            insert_at = pos_map[j1] if j1 < len(pos_map) else len(tagged_chars)
            tagged_chars[insert_at:insert_at] = list(src_chunk)

    fixed_tagged = "".join(tagged_chars)
    # Verify the fix actually resolves fidelity.
    fixed_reconstructed, _ = strip_tags_with_map(fixed_tagged)
    if fixed_reconstructed != src:
        print(f"{doc_id}: FIX DID NOT RESOLVE fidelity, aborting write")
        return False

    tagged_path.write_text(fixed_tagged, encoding="utf-8")
    print(f"{doc_id}: fixed and verified byte-identical to source ({len(src)} chars)")
    return True

for doc_id in ["285693071", "301247724"]:
    fix_document(doc_id)
