import sys


def fix_nbsp(tagged: str, source: str) -> str:
    out = list(tagged)
    src_idx = 0
    in_tag = False
    mismatches = []
    for i, ch in enumerate(tagged):
        if ch == "<":
            in_tag = True
            continue
        if ch == ">":
            in_tag = False
            continue
        if in_tag:
            continue
        # ch is text content, aligned with source[src_idx]
        if src_idx >= len(source):
            mismatches.append((i, ch, None))
            continue
        src_ch = source[src_idx]
        if ch != src_ch:
            if ch == " " and src_ch == "\xa0":
                out[i] = "\xa0"
            else:
                mismatches.append((i, ch, src_ch))
        src_idx += 1
    return "".join(out), mismatches, src_idx


if __name__ == "__main__":
    tagged_path, source_path, out_path = sys.argv[1:4]
    tagged = open(tagged_path, encoding="utf-8").read()
    source = open(source_path, encoding="utf-8").read()
    fixed, mismatches, consumed = fix_nbsp(tagged, source)
    print("consumed", consumed, "of", len(source))
    print("mismatches (non-NBSP):", mismatches[:10], "total", len(mismatches))
    open(out_path, "w", encoding="utf-8").write(fixed)
