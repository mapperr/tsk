#!/bin/sh
set -u
exec </dev/null

ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
TSK=${TSK_BIN:-$ROOT/tsk}

pass=0
fail=0
work=''

cleanup() {
    [ -z "$work" ] || rm -rf "$work"
}
trap cleanup 0 1 2 3 15

new_env() {
    cleanup
    work=$(mktemp -d "${TMPDIR:-/tmp}/tsk-test.XXXXXX") || exit 1
    export TSK_DIR="$work/tasks"
    mkdir -p "$TSK_DIR"
}

task() {
    id=$1
    shift
    printf '%s\n' "$*" >"$TSK_DIR/$id.tsk.md"
}

ok() {
    pass=$((pass + 1))
    printf 'ok %d - %s\n' "$pass" "$1"
}

not_ok() {
    fail=$((fail + 1))
    printf 'not ok - %s\n' "$1" >&2
    [ "$#" -lt 2 ] || printf '  %s\n' "$2" >&2
}

assert_eq() {
    name=$1 expected=$2 actual=$3
    if [ "$expected" = "$actual" ]; then ok "$name"; else not_ok "$name" "expected: [$expected] actual: [$actual]"; fi
}

assert_contains() {
    name=$1 haystack=$2 needle=$3
    case "$haystack" in *"$needle"*) ok "$name" ;; *) not_ok "$name" "missing [$needle] in [$haystack]" ;; esac
}

assert_status() {
    name=$1 expected=$2 actual=$3
    if [ "$expected" -eq "$actual" ]; then ok "$name"; else not_ok "$name" "expected status $expected, got $actual"; fi
}

# list: open by default; done only on request; exact/literal/regex filters.
new_env
task 20260929090000000-A001 'Alpha VPN +work +next'
task 20260929090100000-B002 'Beta DNS +home +done'
task 20260929090200000-C003 'Gamma vpn docs +work'
out=$($TSK l)
assert_contains 'list shows open task' "$out" '[A001] Alpha VPN'
case "$out" in *'[B002]'*) not_ok 'list hides done task' ;; *) ok 'list hides done task' ;; esac
out=$($TSK l --done)
assert_contains 'list --done shows done task' "$out" '[B002] Beta DNS'
out=$($TSK l +work)
assert_contains 'exact tag filter' "$out" '[A001] Alpha VPN'
out=$($TSK l vpn)
assert_contains 'literal filter is case-insensitive' "$out" '[C003] Gamma vpn docs'
out=$($TSK l '~Alpha|Gamma')
assert_contains 'explicit regex filter' "$out" '[A001] Alpha VPN'

# piped mutation and strict -+tag removal syntax.
out=$($TSK l +work | $TSK t +focus 2>&1)
assert_contains 'piped tag add reports success' "$out" 'tags updated'
out=$($TSK l +focus)
assert_contains 'piped tag add changes tasks' "$out" '+focus'
$TSK l A001 | $TSK t -+focus >/dev/null 2>&1
out=$($TSK l A001)
case "$out" in *'+focus'*) not_ok 'remove tag with -+tag' ;; *) ok 'remove tag with -+tag' ;; esac
set +e
$TSK l A001 | $TSK t -work >/dev/null 2>&1
rc=$?
set -e
assert_status 'old -tag removal syntax is rejected' 1 "$rc"

# done/open/due.
$TSK done A001 >/dev/null 2>&1
out=$($TSK l --done A001)
assert_contains 'done marks task completed' "$out" '+done'
$TSK open A001 >/dev/null 2>&1
out=$($TSK l A001)
case "$out" in *'+done'*) not_ok 'open removes done tag' ;; *) ok 'open removes done tag' ;; esac
$TSK due tomorrow A001 >/dev/null 2>&1
tomorrow=$(date -d tomorrow +%Y-%m-%d)
out=$($TSK l A001)
assert_contains 'due normalizes date' "$out" "+due:$tomorrow"
$TSK due - A001 >/dev/null 2>&1
out=$($TSK l A001)
case "$out" in *'+due:'*) not_ok 'due - removes deadline' ;; *) ok 'due - removes deadline' ;; esac
first=$(sed -n '1p' "$TSK_DIR/20260929090000000-A001.tsk.md")
case "$first" in *' +'|*' + '*) not_ok 'due removal leaves no dangling tag' ;; *) ok 'due removal leaves no dangling tag' ;; esac


# add streams stdin into the Markdown body.
new_env
printf 'line one\nline two\n' | $TSK a 'Body task' +work >/dev/null 2>&1
created=$(find "$TSK_DIR" -name '*.tsk.md' -type f | head -n 1)
body=$(tail -n +3 "$created")
assert_eq 'add preserves piped body' "$(printf 'line one\nline two')" "$body"

# show is a raw cat.
new_env
cat >"$TSK_DIR/20260929100000000-SHOW.tsk.md" <<'EOF_TASK'
Raw markdown +work

# Heading

body  
EOF_TASK
$TSK s SHOW >"$work/out"
cmp -s "$TSK_DIR/20260929100000000-SHOW.tsk.md" "$work/out" && ok 'show cats file unchanged' || not_ok 'show cats file unchanged'

# edit: ambiguous selection must not invoke editor; exact short id must.
new_env
task 20260929110000000-E001 'Same title one +work'
task 20260929110100000-E002 'Same title two +work'
cat >"$work/editor" <<'EOF_EDITOR'
#!/bin/sh
printf '%s\n' "$1" >>"$EDITOR_LOG"
EOF_EDITOR
chmod +x "$work/editor"
export EDITOR="$work/editor" EDITOR_LOG="$work/editor.log"
set +e
$TSK e 'Same title' >/dev/null 2>&1
rc=$?
set -e
assert_status 'edit rejects ambiguous selection' 1 "$rc"
[ ! -e "$EDITOR_LOG" ] && ok 'ambiguous edit does not invoke editor' || not_ok 'ambiguous edit does not invoke editor'
$TSK e E001 >/dev/null 2>&1
assert_contains 'edit accepts unique short id' "$(cat "$EDITOR_LOG")" '20260929110000000-E001.tsk.md'

# daily/review windows and stdin narrowing.
new_env
today=$(date +%Y-%m-%d)
tomorrow=$(date -d tomorrow +%Y-%m-%d)
in3=$(date -d '+3 days' +%Y-%m-%d)
in8=$(date -d '+8 days' +%Y-%m-%d)
yesterday=$(date -d yesterday +%Y-%m-%d)
task 20260929120000000-D001 "Late +work +due:$yesterday"
task 20260929120100000-D002 "Today +work +due:$today"
task 20260929120200000-D003 "Tomorrow +home +due:$tomorrow"
task 20260929120300000-D004 "Soon +work +due:$in3"
task 20260929120400000-D005 "Later next +work +next +due:$in8"
task 20260929120500000-D006 'Plain next +home +next'
out=$($TSK)
assert_contains 'daily has overdue section' "$out" 'OVERDUE'
assert_contains 'daily has tomorrow section' "$out" 'TOMORROW'
assert_contains 'daily has week section' "$out" 'IN A WEEK'
assert_contains 'daily shows relative days' "$out" '(3d)'
out=$($TSK r +work)
assert_contains 'review accepts filters' "$out" 'Soon'
case "$out" in *'Plain next'*) not_ok 'review filter narrows selection' ;; *) ok 'review filter narrows selection' ;; esac
out=$($TSK l +home | $TSK r)
assert_contains 'review accepts piped selection' "$out" 'Plain next'
case "$out" in *'Soon'*) not_ok 'piped review stays within selection' ;; *) ok 'piped review stays within selection' ;; esac

# dir and check.
assert_eq 'dir prints TSK_DIR' "$TSK_DIR" "$($TSK dir)"
new_env
task 20260929130000000-CHEK 'Valid +work +due:2026-10-01'
assert_eq 'check accepts valid archive' 'ok: no problems found' "$($TSK check)"
task 20260929130100000-BAD1 'Bad +due:2026-99-99'
set +e
out=$($TSK check 2>&1)
rc=$?
set -e
assert_status 'check rejects invalid due date' 1 "$rc"
assert_contains 'check explains invalid due date' "$out" 'invalid due date'

# external command dispatch stays available.
new_env
cat >"$work/tsk-hello" <<'EOF_EXT'
#!/bin/sh
printf 'hello %s\n' "$*"
EOF_EXT
chmod +x "$work/tsk-hello"
PATH="$work:$PATH" out=$($TSK hello world)
assert_eq 'external tsk-* command dispatch' 'hello world' "$out"

printf '\n%d passed, %d failed\n' "$pass" "$fail"
[ "$fail" -eq 0 ]
