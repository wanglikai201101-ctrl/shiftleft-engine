#!/usr/bin/env bash
#
# probe-kb-envelopes-from-sources.sh
#
# Phase 1 of the Step 1.5 envelope probe plan. Runs BEFORE test generation.
#
# Discovers API endpoints from ROUTE FILES (not test files) and cross-references
# KB documentation to produce a real <ENV>-envelope-index.json, so the very first
# pass of assertion generation uses real data structures instead of guessing
# $.data from an API doc.
#
# Usage:
#   bash probe-kb-envelopes-from-sources.sh <ROUTES_DIR> <KB_DOCS_DIR> <OUTPUT_DIR> [ENV]
#
#   ROUTES_DIR  - backend source tree containing route definitions
#   KB_DOCS_DIR - KB documentation tree (searched for matching API docs)
#   OUTPUT_DIR  - where to write <ENV>-envelope-index.json
#   ENV         - environment name (default: dev)
#
# Output: $OUTPUT_DIR/$ENV-envelope-index.json
#   {
#     "version": 1,
#     "known_envelopes": {
#       "GET /api/users": {
#         "list_path": "$.data.items",      # detected list path (from KB doc) or "" for object
#         "item_id_path": "",
#         "item_name_path": "",
#         "verified": false,                # pre-probe: derived from route+KB, NOT live-tested
#         "pre_probe": true,                # distinguishes from mcp-ready/live-probe entries
#         "source": "pre-probe: route=... | kb=...",
#         "probed_at": "<ISO date>"
#       }
#     },
#     "fallback_rules": { ... },
#     "probedAt": "<ISO date>"
#   }
#
# The pre_probe flag is the contract with the gen-tests-api consumer (Step 2d.5):
# a pre_probe entry MAY be used as the JSONPath basis for assertions (so the first
# pass uses the real list path like $.items / $.data.items instead of guessing
# $.data), but it MUST be marked _meta.path_unverified until regression's live
# envelope-validation confirms it and flips verified:true.
#
# Exit codes:
#   0 = success (index written; endpoints may be empty when no routes found)
#   2 = usage / input error
#
# Logging: every log line goes to stderr, prefixed with "ENVELOPE: ". The final
# output path is printed to stdout (single line) so callers can read it back.

set -euo pipefail

log() { echo "ENVELOPE: $*" >&2; }

ROUTES_DIR="${1:-}"
KB_DOCS_DIR="${2:-}"
OUTPUT_DIR="${3:-}"
ENV="${4:-dev}"

# ---- input validation -------------------------------------------------------
if [ -z "$ROUTES_DIR" ] || [ -z "$KB_DOCS_DIR" ] || [ -z "$OUTPUT_DIR" ]; then
  log "Usage: probe-kb-envelopes-from-sources.sh <ROUTES_DIR> <KB_DOCS_DIR> <OUTPUT_DIR> [ENV]"
  exit 2
fi
if [ ! -d "$ROUTES_DIR" ]; then
  log "ERROR: ROUTES_DIR not a directory: $ROUTES_DIR"
  exit 2
fi
if [ ! -d "$KB_DOCS_DIR" ]; then
  log "ERROR: KB_DOCS_DIR not a directory: $KB_DOCS_DIR"
  exit 2
fi

ROUTES_DIR="${ROUTES_DIR%/}"
KB_DOCS_DIR="${KB_DOCS_DIR%/}"
mkdir -p "$OUTPUT_DIR"

# ---- temp workspace ---------------------------------------------------------
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT
ROUTES_TSV="$TMP_DIR/routes.tsv"
ENRICHED_TSV="$TMP_DIR/enriched.tsv"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# normalize_path: strip query/fragment, collapse slashes, ensure leading slash,
# drop trailing slash (keep root "/").
normalize_path() {
  local p="$1"
  p="${p%%\?*}"
  p="${p%%#*}"
  while [[ "$p" == *"//"* ]]; do
    p="${p//\/\//\/}"
  done
  if [[ "$p" != /* ]]; then p="/$p"; fi
  if [ "$p" != "/" ]; then p="${p%/}"; fi
  printf '%s' "$p"
}

# source_label: "route:<relative-path-from-ROUTES_DIR>"
source_label() {
  local routes_dir="$1" f="$2"
  local rel="${f#"$routes_dir"/}"
  printf 'route:%s' "$rel"
}

# path_to_slug: "/api/v1/users" -> "api-v1-users", "/sandbox/{id}/run" -> "sandbox-{id}-run"
path_to_slug() {
  local p="$1"
  p="${p#/}"
  p="${p%/}"
  p="${p//\//-}"
  p="$(printf '%s' "$p" | sed -E 's/[^A-Za-z0-9._{}:-]+/_/g')"
  printf '%s' "$p"
}

# ---------------------------------------------------------------------------
# discover_routes: scan route files for HTTP method + path patterns.
# Emits TSV to $out:  METHOD<TAB>PATH<TAB>SOURCE  (deduped, normalized).
# ---------------------------------------------------------------------------
discover_routes() {
  local routes_dir="$1"
  local out="$2"
  local tmp_specific="$TMP_DIR/routes_specific.tsv"
  local tmp_generic="$TMP_DIR/routes_generic.tsv"
  : > "$out"
  : > "$tmp_specific"
  : > "$tmp_generic"

  log "Route discovery: scanning $routes_dir"

  # Prune vendored / generated trees so binary and third-party files never leak
  # into route extraction.
  local prune
  prune='( -path */node_modules/* -o -path */.git/* -o -path */.svn/* -o -path */venv/* -o -path */.venv/* -o -path */__pycache__/* -o -path */vendor/* -o -path */dist/* -o -path */build/* )'

  # Specific patterns: Express/Fastify, Laravel, Flask, Django.
  # (embedded perl: \x27 = single quote, \x22 = double quote)
  find "$routes_dir" $prune -prune -o -type f -print0 2>/dev/null \
    | xargs -0 perl -ne '
      my $f = $ARGV;
      # Express / Fastify: router.get(...) / app.post(...) / server.get(...)
      while (/\b(?:router|app|server|fastify|bp|blueprint|route|r|api)\s*\.\s*(get|post|put|patch|delete|head|options)\s*\(\s*[\x27\x22](\/[^\x27\x22]*)[\x27\x22]/ig) {
        print "$1\t$2\t$f\n";
      }
      # Laravel: Route::get(...) / Route::post(...)
      while (/Route::(get|post|put|patch|delete|head|options|any|match)\s*\(\s*[\x27\x22](\/[^\x27\x22]*)[\x27\x22]/ig) {
        my $m = uc($1);
        $m = "GET" if $m eq "ANY" || $m eq "MATCH";
        print "$m\t$2\t$f\n";
      }
      # Flask: @app.route("/api/...", methods=["GET"])
      while (/@(?:app|bp|blueprint)\s*\.\s*route\s*\(\s*[\x27\x22](\/[^\x27\x22]*)[\x27\x22]([^)]*)/ig) {
        my ($p, $rest) = ($1, $2);
        my $m = "GET";
        if ($rest =~ /methods\s*=\s*\[\s*[\x27\x22]([A-Za-z]+)[\x27\x22][^\]]*\]/i) { $m = uc($1); }
        print "$m\t$p\t$f\n";
      }
      # Django: path("api/users", ...) — no leading slash; only keep paths with a "/".
      # NOTE: capture $1 into a local first — "$1 =~ m{/}" would reset $1 to empty
      # on a successful match, since a regex match re-binds the capture variables.
      while (/\bpath\s*\(\s*[\x27\x22]([^\x27\x22]*)[\x27\x22]/ig) {
        my $p = $1;
        print "GET\t$p\t$f\n" if $p =~ m{/};
      }
    ' > "$tmp_specific" 2>/dev/null || true

  # Simple fallback: any quoted string containing /api/ (method unknown -> GET).
  find "$routes_dir" $prune -prune -o -type f -print0 2>/dev/null \
    | xargs -0 perl -ne '
      my $f = $ARGV;
      while (/[\x27\x22](\/api\/[^\x27\x22]*)[\x27\x22]/g) {
        print "GET\t$1\t$f\n";
      }
    ' > "$tmp_generic" 2>/dev/null || true

  # Merge + dedupe (bash 3.2 compatible — no associative arrays). Specific
  # matches win; the generic fallback only fills paths not already seen, so a
  # POST /api/users is never shadowed by a fallback GET /api/users.
  #
  # Fields are split with `cut`, not `IFS=$'\t' read`, because `read` collapses
  # consecutive IFS-whitespace (a tab IS whitespace) and would silently drop
  # empty fields (e.g. a route line with an empty captured path).
  local seen_keys="$TMP_DIR/seen_keys.txt"
  local seen_paths="$TMP_DIR/seen_paths.txt"
  : > "$seen_keys"
  : > "$seen_paths"
  local line m p f key

  while IFS= read -r line; do
    m="$(printf '%s' "$line" | cut -f1)"
    p="$(printf '%s' "$line" | cut -f2)"
    f="$(printf '%s' "$line" | cut -f3)"
    [ -z "$m" ] && continue
    m="$(printf '%s' "$m" | tr '[:lower:]' '[:upper:]')"
    p="$(normalize_path "$p")"
    [ -z "$p" ] && continue
    [ "$p" = "/" ] && continue
    key="$m $p"
    if ! grep -Fxq "$key" "$seen_keys"; then
      printf '%s\n' "$key" >> "$seen_keys"
      printf '%s\n' "$p" >> "$seen_paths"
      printf '%s\t%s\t%s\n' "$m" "$p" "$(source_label "$routes_dir" "$f")" >> "$out"
    fi
  done < "$tmp_specific"

  while IFS= read -r line; do
    p="$(printf '%s' "$line" | cut -f2)"
    f="$(printf '%s' "$line" | cut -f3)"
    p="$(normalize_path "$p")"
    [ -z "$p" ] && continue
    [ "$p" = "/" ] && continue
    if ! grep -Fxq "$p" "$seen_paths"; then
      printf '%s\n' "$p" >> "$seen_paths"
      printf '%s\t%s\t%s\n' "GET" "$p" "$(source_label "$routes_dir" "$f")" >> "$out"
    fi
  done < "$tmp_generic"

  local count
  count="$(wc -l < "$out" | awk '{print $1}')"
  log "Route discovery complete: $count endpoints"
}

# ---------------------------------------------------------------------------
# find_kb_doc: locate a KB doc matching (method, path).
# Tries filename candidates (GET-customers.md style), then a content grep for
# "<METHOD> /path". Prints the matching doc path (empty when no match).
# ---------------------------------------------------------------------------
find_kb_doc() {
  local method="$1" path="$2"
  local stripped slug c hit needle frag
  local candidates=()

  # Filename candidates: progressively strip /api and /api/v1 prefixes, e.g.
  # /api/v1/users -> GET-users.md (plus GET-v1-users.md, GET-api-v1-users.md).
  for stripped in "$path" "${path#/api}" "${path#/api/v1}" "${path#/v1}"; do
    slug="$(path_to_slug "$stripped")"
    [ -n "$slug" ] || continue
    candidates+=("${method}-${slug}.md" "${method}-${slug}.markdown")
  done
  for c in "${candidates[@]}"; do
    hit="$(find "$KB_DOCS_DIR" -type f -iname "$c" 2>/dev/null | head -n1 || true)"
    if [ -n "$hit" ]; then
      printf '%s' "$hit"
      return 0
    fi
  done

  # Content fallback: doc prose carries "<METHOD> /path" (fixed-string grep).
  frag="${path#/api}"
  frag="${frag#/v1}"
  for needle in "${method} ${path}" "${method} ${frag}" "${method} ${path#/}"; do
    [ -n "$needle" ] || continue
    hit="$(grep -rilF --include='*.md' --include='*.markdown' "$needle" "$KB_DOCS_DIR" 2>/dev/null | head -n1 || true)"
    if [ -n "$hit" ]; then
      printf '%s' "$hit"
      return 0
    fi
  done

  printf ''
}

# ---------------------------------------------------------------------------
# extract_response_section: print the portion of a KB doc describing the
# response — from the first "响应结构" / "响应" heading to the next major
# non-response heading. Empty when the doc has no response section.
# ---------------------------------------------------------------------------
extract_response_section() {
  local doc="$1"
  awk '
    BEGIN { on = 0 }
    /^#{1,3}[ \t]*响应结构/ { on = 1; print; next }
    /^#{1,3}[ \t]*响应/ && !on { on = 1; print; next }
    on && /^##[ \t]+/ && $0 !~ /响应/ { on = 0 }
    on { print }
  ' "$doc"
}

# ---------------------------------------------------------------------------
# extract_response_fields: parse the Chinese response-structure table — a
# markdown table under "## 响应结构" whose header row contains 字段 and 类型 —
# and write "FIELD<TAB>TYPE" lines for each data row to $out. The table is
# 字段/类型/流向/说明 style, e.g.:
#     | 字段 | 类型 | 流向 | 说明 |
#     |------|------|------|------|
#     | id | string | → POST /{id}/run | Agent UUID |
#     | items | array | → 前端列表 | 列表数据 |
# Emits an empty file when no such table exists. bash 3.2 compatible (the
# parsing lives in an awk one-liner; no bash associative arrays).
# ---------------------------------------------------------------------------
extract_response_fields() {
  local doc="$1" out="$2"
  awk '
    function clean(s) {
      gsub(/^[ \t]+|[ \t]+$/, "", s)
      gsub(/`/, "", s)
      return s
    }
    BEGIN { on = 0; hdr = 0; fc = 0; tc = 0 }
    /^#{1,3}[ \t]*响应结构/ { on = 1; next }
    /^#{1,3}[ \t]*响应/ && !on { on = 1; next }
    on && /^#+[ \t]+/ && $0 !~ /响应/ { on = 0; hdr = 0; next }
    !on { next }
    !hdr && /^\|/ {
      if ($0 ~ /字段/ && $0 ~ /类型/) {
        n = split($0, c, /\|/)
        fc = 0; tc = 0
        for (i = 1; i <= n; i++) {
          s = clean(c[i])
          if (s == "字段" || s == "字段名") fc = i
          if (s == "类型") tc = i
        }
        if (fc > 0 && tc > 0) hdr = 1
      }
      next
    }
    hdr && /^\|/ {
      n = split($0, c, /\|/)
      if (fc > n || tc > n) next
      f = clean(c[fc]); t = clean(c[tc])
      if (f == "" || t == "") next
      if (f ~ /^[-:|]+$/) next          # separator row
      if (t ~ /^[-:|]+$/) next          # separator-ish type column
      print f "\t" t
    }
  ' "$doc" > "$out"
}

# ---------------------------------------------------------------------------
# detect_list_from_table: from a response-table FIELD<TAB>TYPE file, infer the
# list JSONPath. Emits "$.items", "$.data.items", any "$.X...", or empty.
# Priority:
#   A. wrapper object (data/result/results/records/...) whose sub-field
#      (data.items / data.rows / data.list) is an array  ->  $.data.items
#   B. any dotted list field                                ->  $.data.items
#   C. bare list field                                      ->  $.items
# ---------------------------------------------------------------------------
detect_list_from_table() {
  local pairs="$1"
  awk -F'\t' '
    function is_list(t) {
      t = tolower(t)
      return (t ~ /array/ || t ~ /\[\]/ || t ~ /list/ || t ~ /列表/ || t ~ /数组/)
    }
    function is_obj(t) {
      t = tolower(t)
      if (t ~ /\[\]/ || t ~ /array/ || t ~ /list/) return 0
      return (t ~ /object/ || t ~ /^dict/ || t ~ /^map/ || t ~ /对象/ || t ~ /包裹/ || t ~ /结构/)
    }
    {
      fields[++n] = $1
      types[$1] = $2
    }
    END {
      # A. wrapper object whose sub-field is a list: data(object) + data.items(array)
      wc = split("data,result,results,records,payload,list,items,rows", wrappers, ",")
      for (wi = 1; wi <= wc; wi++) {
        w = wrappers[wi]
        if ((w in types) && is_obj(types[w])) {
          for (i = 1; i <= n; i++) {
            f = fields[i]
            if (f ~ ("^" w "\\.[A-Za-z0-9_]+$") && is_list(types[f])) {
              print "$." f
              exit
            }
          }
        }
      }
      # B. any dotted list field: data.items -> $.data.items
      for (i = 1; i <= n; i++) {
        f = fields[i]
        if (f ~ /\./ && is_list(types[f])) { print "$." f; exit }
      }
      # C. bare list field: items -> $.items
      for (i = 1; i <= n; i++) {
        f = fields[i]
        if (f !~ /\./ && is_list(types[f])) { print "$." f; exit }
      }
    }
  ' "$pairs"
}

# ---------------------------------------------------------------------------
# extract_top_level_keys: from a response-table FIELD<TAB>TYPE file, emit the
# comma-separated names of top-level (non-dotted, non-list) fields. For a
# single-object response this is the full field list — the consumer can assert
# individual top-level keys instead of a list path.
# ---------------------------------------------------------------------------
extract_top_level_keys() {
  local pairs="$1"
  awk -F'\t' '
    function is_list(t) {
      t = tolower(t)
      return (t ~ /array/ || t ~ /\[\]/ || t ~ /list/ || t ~ /列表/ || t ~ /数组/)
    }
    $1 !~ /\./ && $1 ~ /^[A-Za-z_][A-Za-z0-9_-]*$/ && !is_list($2) {
      if (keys != "") keys = keys ","
      keys = keys $1
    }
    END { print keys }
  ' "$pairs"
}

# ---------------------------------------------------------------------------
# detect_list_path: from a KB doc, detect the response list structure.
# Prints: "$" (root array), "$.items", "$.data.items", any "$.X...items",
# or empty when the doc carries no list structure.
#
# Priority (existing JSONPath/JSON-block rules stay first — they are more
# precise than table parsing):
#   1-3. Explicit JSONPath mentions: $.data.items, $.items, $.X.items
#   4.   Root-array ```json example (first char '[')
#   5.   JSON example in the response section with a top-level array field,
#        e.g. "data": [  ->  $.data
#   6.   Chinese response-structure table (字段/类型) with an array/list field
# ---------------------------------------------------------------------------
detect_list_path() {
  local doc="$1" pairs="${2:-}"
  local lp block

  # 1. Wrapped list: $.data.items (also tolerate $.data[0].items / $.data[*].items)
  lp="$(grep -oE '\$\.data(\[[*0-9]+\])?\.items' "$doc" 2>/dev/null | sed -E 's/\[[*0-9]+\]//' | head -n1 || true)"
  [ -n "$lp" ] && { printf '%s' "$lp"; return 0; }

  # 2. Bare list: $.items (also matches $.items[0].field — the list is still $.items).
  #    NOTE: must come AFTER $.data.items so a wrapped list wins the more specific form.
  lp="$(grep -oE '\$\.items' "$doc" 2>/dev/null | head -n1 || true)"
  [ -n "$lp" ] && { printf '%s' "$lp"; return 0; }

  # 3. Any nested list path ending in .items, e.g. $.result.items
  lp="$(grep -oE '\$(\.[A-Za-z0-9_]+)+\.items' "$doc" 2>/dev/null | head -n1 || true)"
  [ -n "$lp" ] && { printf '%s' "$lp"; return 0; }

  # 4. Root-array JSON example: a fenced ```json block whose first char is '['
  block="$(sed -n '/```json/,/```/p' "$doc" 2>/dev/null | sed '1d;$d' | tr -d '[:space:]' || true)"
  if [ -n "$block" ] && [ "${block:0:1}" = "[" ]; then
    printf '%s' '$'
    return 0
  fi

  # 5. Response-section JSON example with a top-level array field: "data": [ -> $.data
  block="$(extract_response_section "$doc" | sed -n '/```json/,/```/p' | sed '1d;$d' || true)"
  if [ -n "$block" ]; then
    lp="$(printf '%s\n' "$block" \
      | grep -oE '"([A-Za-z_][A-Za-z0-9_]*)"[[:space:]]*:[[:space:]]*\[' \
      | head -n1 \
      | sed -E 's/^"([A-Za-z_][A-Za-z0-9_]*)"[[:space:]]*:[[:space:]]*\[$/\1/' || true)"
    if [ -n "$lp" ]; then
      printf '$.%s' "$lp"
      return 0
    fi
  fi

  # 6. Chinese response table: array/list field in the 字段/类型 table.
  if [ -n "$pairs" ] && [ -s "$pairs" ]; then
    lp="$(detect_list_from_table "$pairs")"
    [ -n "$lp" ] && { printf '%s' "$lp"; return 0; }
  fi

  printf ''
}

# ---------------------------------------------------------------------------
# cross_ref_kb: for one (method, path), find the KB doc and its list structure.
# Emits TSV to stdout:  KBDOC<TAB>LISTPATH<TAB>TOPLEVELKEYS  (empty fields when
# no match). TOPLEVELKEYS is a comma-separated list of top-level response
# fields parsed from the Chinese response table.
# ---------------------------------------------------------------------------
cross_ref_kb() {
  local method="$1" path="$2"
  local doc listpath topkeys pairs
  doc="$(find_kb_doc "$method" "$path")"
  if [ -n "$doc" ]; then
    pairs="$TMP_DIR/response_pairs.tsv"
    extract_response_fields "$doc" "$pairs"
    listpath="$(detect_list_path "$doc" "$pairs")"
    topkeys="$(extract_top_level_keys "$pairs")"
    printf '%s\t%s\t%s\n' "$doc" "$listpath" "$topkeys"
  else
    printf '\t\t\n'
  fi
}

# ---------------------------------------------------------------------------
# build_envelope_index: cross-reference every discovered route against the KB,
# assemble the envelope index JSON, and write it to OUTPUT_DIR.
# ---------------------------------------------------------------------------
build_envelope_index() {
  local out="$ENRICHED_TSV"
  : > "$out"
  local count=0
  local line m p s kr kbdoc listpath

  while IFS= read -r line; do
    m="$(printf '%s' "$line" | cut -f1)"
    p="$(printf '%s' "$line" | cut -f2)"
    s="$(printf '%s' "$line" | cut -f3)"
    [ -z "$m" ] && continue
    kr="$(cross_ref_kb "$m" "$p")"
    kbdoc="${kr%%$'\t'*}"
    rest="${kr#*$'\t'}"
    listpath="${rest%%$'\t'*}"
    topkeys="${rest#*$'\t'}"
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$m" "$p" "$s" "$kbdoc" "$listpath" "$topkeys" >> "$out"
    count=$((count+1))
  done < "$ROUTES_TSV"
  log "KB cross-reference: $count endpoints"

  local outfile="$OUTPUT_DIR/$ENV-envelope-index.json"
  python3 - "$outfile" "$ENRICHED_TSV" << 'PYEOF'
import sys, json, datetime

outfile, tsv = sys.argv[1], sys.argv[2]
known = {}
with open(tsv, "r", encoding="utf-8") as fh:
    for line in fh:
        line = line.rstrip("\n")
        if not line:
            continue
        parts = line.split("\t")
        method = parts[0]
        path = parts[1]
        source = parts[2]
        kbdoc = parts[3] if len(parts) > 3 else ""
        listpath = parts[4] if len(parts) > 4 else ""
        topkeys = parts[5] if len(parts) > 5 else ""

        # Conservative default: single object (no KB evidence of a list).
        list_path = ""
        item_id_path = ""
        item_name_path = ""

        if listpath == "$":
            list_path = "$"
        elif listpath.startswith("$."):
            list_path = listpath
        elif listpath == "":
            # No KB list evidence. A bare array response (list_path "$")
            # is rarer than a wrapped list; default to "" (object) — the
            # consumer falls back to API doc, and regression's live probe
            # fills the true list path later.
            list_path = ""

        entry = {
            "list_path": list_path,
            "item_id_path": item_id_path,
            "item_name_path": item_name_path,
            "verified": False,          # pre-probe: derived from route+KB, NOT live-tested
            "pre_probe": True,          # distinguishes from mcp-ready/live-probe entries
            "source": f"pre-probe: route={source} | kb={kbdoc or 'none'}",
            "probed_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        if kbdoc:
            entry["kb_doc"] = kbdoc
        if topkeys:
            # Top-level response keys parsed from the Chinese response table —
            # the consumer uses these to assert single-object fields when
            # list_path is empty (pre-probe basis, still path_unverified).
            entry["top_level_keys"] = [k for k in topkeys.split(",") if k]
        known[f"{method} {path}"] = entry

doc = {
    "version": 1,
    "note": "接口 → 响应 envelope 对照表（Step 1.5 前置探针产出）。list_path 从 route 文件 + KB doc 推导，verified:false（未实测）；实测由 regression envelope-validation 复核后回写。",
    "known_envelopes": known,
    "fallback_rules": {
        "pre_probe": "pre_probe:true 且 list_path 非空 → 可作为断言 jsonpath 依据，但注入时标记 _meta.path_unverified；经 regression 实测通过后 verified:true + pre_probe 移除。",
        "default_wrap_guess": "禁止默认写 $.data。列表接口必须实测/查表确定包裹字段（items/data/results/records/...）。"
    },
    "probedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
}
with open(outfile, "w", encoding="utf-8") as f:
    json.dump(doc, f, ensure_ascii=False, indent=2)
    f.write("\n")
PYEOF

  echo "$outfile"
  log "Envelope index written: $outfile ($count endpoints)"
}

# ---- main -------------------------------------------------------------------
discover_routes "$ROUTES_DIR" "$ROUTES_TSV"
build_envelope_index
exit 0
