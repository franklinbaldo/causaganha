import difflib
import re
import sys


def fix_file(tagged_path, source_path):
    tagged = open(tagged_path, encoding="utf-8").read()
    src = open(source_path, encoding="utf-8").read()

    mapping = []
    stripped_chars = []
    i = 0
    n = len(tagged)
    tag_re = re.compile(r"</?[a-zA-Z_]+>")
    while i < n:
        m = tag_re.match(tagged, i)
        if m:
            i = m.end()
            continue
        mapping.append(i)
        stripped_chars.append(tagged[i])
        i += 1
    stripped = "".join(stripped_chars)

    if stripped == src:
        print("ALREADY MATCHES:", tagged_path)
        return

    sm = difflib.SequenceMatcher(None, stripped, src, autojunk=False)
    ops = sm.get_opcodes()
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            continue
        a = stripped[i1:i2]
        b = src[j1:j2]
        if not (set(a) <= set(" \xa0") and set(b) <= set(" \xa0")):
            print("NON-WHITESPACE DIFF, ABORT:", tag, repr(a), "->", repr(b))
            sys.exit(1)

    new_tagged = tagged
    for tag, i1, i2, j1, j2 in reversed(ops):
        if tag == "equal":
            continue
        replacement = src[j1:j2]
        if i1 == i2:
            # pure insert: no stripped chars consumed, insert right before mapping[i1]
            # (or at end of string if i1 == len(mapping))
            pos = mapping[i1] if i1 < len(mapping) else n
            new_tagged = new_tagged[:pos] + replacement + new_tagged[pos:]
        else:
            # replace/delete: the affected raw range is from the start of the
            # first replaced stripped char to the END of the last replaced
            # stripped char (mapping[i2-1] + 1) -- NOT mapping[i2], which is
            # the start of the *next* stripped char and would also swallow
            # any tag sitting between the two.
            pos = mapping[i1]
            pos_end = mapping[i2 - 1] + 1
            new_tagged = new_tagged[:pos] + replacement + new_tagged[pos_end:]

    stripped2 = re.sub(r"</?[a-zA-Z_]+>", "", new_tagged)
    assert stripped2 == src, "fix failed: text mismatch"

    # tag-count sanity check: this class of bug (eating a tag adjacent to an
    # edit boundary) doesn't change the stripped text, so it must be checked
    # separately.
    before_tags = sorted(tag_re.findall(tagged))
    after_tags = sorted(tag_re.findall(new_tagged))
    assert before_tags == after_tags, f"fix failed: tag set changed {before_tags} != {after_tags}"

    open(tagged_path, "w", encoding="utf-8").write(new_tagged)
    print("FIXED:", tagged_path)


if __name__ == "__main__":
    fix_file(sys.argv[1], sys.argv[2])
