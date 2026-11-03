import json, collections, sys
d = json.load(open(sys.argv[1]))
idx = {f'{r["layer"]}.{r["relation"]}.{r["column"]}': r for r in d}
def roots(key, seen):
    if key in seen: return set()
    seen.add(key)
    r = idx.get(key)
    if r is None: return {("source-blank", key)}
    if r["state"] != "undescribed": return set()
    if r["how"] == "carry-upstream-blank":
        out = set()
        for l in r["leaves"] or []: out |= roots(l, seen)
        return out
    return {(r["how"], key)}
need = set()
for r in d:
    if r["layer"] in ("analytics", "consumption") and r["state"] == "undescribed":
        need |= roots(f'{r["layer"]}.{r["relation"]}.{r["column"]}', set())
print(sys.argv[1].rsplit("/",1)[1], "roots:", len(need), dict(collections.Counter(k.split(".")[0] for _, k in need)),
      "by name top:", collections.Counter(k.rsplit(".",1)[1] for _, k in need).most_common(4))
