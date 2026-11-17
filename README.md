# tsk

`tsk` is a tiny task manager for the command line.

Its data model is deliberately boring:

```text
one task = one Markdown file
```

The first line is the task title followed by `+tags`; everything below it is normal Markdown. There is no database, daemon, account, server, or hidden state to keep alive.

```text
Fix split DNS +work +next +due:2026-10-02

NetworkManager is using the wrong resolver after the VPN comes up.
```

`tsk` is intentionally small. The everyday workflow is mostly:

```sh
tsk                              # what needs attention?
tsk a Fix split DNS +work +next  # capture something
tsk l +work                      # find tasks
tsk e DNS                        # edit one
tsk done DNS                     # finish it
```

Optional `tsk-*` executables extend the core. This repository includes `tsk-fzf`,
`tsk-git`, `tsk-y`, and the Python 3 `tsk-issue` extension for issue links and imports.

## Why

Task managers have a tendency to become hobbies.

`tsk` tries not to.

Workflow and dates are stored as tags:

```text
+done             completed
+next             part of the current working set
+inbox            captured, not yet reviewed
+backlog          reviewed, deferred work
+wait[:PERSON]    waiting for someone or something
+due:YYYY-MM-DD   deadline
+completed:YYYY-MM-DD  date of completion
```

Other `+tags` remain user-defined. Projects and owners use optional conventions
such as `+project:ace` and `+owner:anna`; group views work with any tag namespace.
Areas, clients, and contexts do not require new entities or configuration:

```text
Review API mapping +work +issuesyncer +qilab +next
Buy printer paper +home
Upgrade PostgreSQL +work +ace
```

The goal is not to model your work perfectly. The goal is to make capturing, finding, and finishing work cheap.

## Installation

`tsk` is a shell script. Put it somewhere in `PATH`:

```sh
install -m 0755 tsk "$HOME/bin/tsk"
```

Or, if you use [`just`](https://github.com/casey/just), this repository provides:

```sh
just link
```

By default it links the executable `tsk*` files into `$HOME/bin`. A different directory can be supplied:

```sh
just link "$HOME/.local/bin"
```

Tasks live in:

```text
~/.tsk
```

Override that with:

```sh
export TSK_DIR="$HOME/tasks"
```

The editor used by `tsk e` comes from `$EDITOR`, falling back to `vi`. Editor
arguments are supported, for example `EDITOR='code --wait'`. When editing a piped
selection, the editor reads from the terminal if one is available.

`tsk` targets Linux and requires GNU coreutils (including `date`, `cp`, and
`mv`), an awk with regex record separators (such as GNU or BusyBox awk), and
`flock` from util-linux. GNU `date` handles relative dates
such as `tomorrow` and `next monday`.

### Bash completion

Optional completion for Bash 4 or newer is included. Enable it in the current
shell, replacing the path with your checkout:

```bash
source /path/to/tsk/completions/tsk.bash
```

Add that line to `~/.bashrc` to enable it in new shells. No `bash-completion`
package is required. Completion suggests commands, installed `tsk-*` extensions,
existing tags, namespace keys, command options, and displayed task IDs. It follows
the command's task status: for example, `tsk open` suggests completed tasks.

Tags from completed tasks remain available for reuse. Both `+tag` and `-+tag`
are supported, including values after `:` such as `+project:ace`.

## Task files

A task is a Markdown file whose filename is its stable full ID:

```text
20260929130000000-AbC1.tsk.md
```

The first line contains title and tags:

```text
Write migration notes +work +ace +next +due:2026-10-03
```

The body, if present, begins on the following lines:

```markdown
Write migration notes +work +ace +next +due:2026-10-03

Document the differences between the old and new rules packages.

## Check

- environment variables
- deployment steps
- rollback procedure
```

You can inspect the files with any normal Unix tool. `tsk` does not own the data format; it merely makes it convenient.

Metadata updates replace each task file atomically and preserve its permissions
and Markdown body. CLI writers, `tsk e`, and `tsk y` share a lock on the task
directory, as do issue links and imports. Changes made directly by other tools do
not participate in this lock.
Metadata updates require writable regular files and reject symbolic links.

## Daily view

Running `tsk` with no arguments shows only the things likely to deserve attention:

```sh
tsk
```

Example:

```text
OVERDUE
  ! 2026-09-27 [Qa7X] (2d late) Renew certificate +work

TODAY
  = 2026-09-29 [Jm2P] Send analysis +work +qilab

TOMORROW
  > 2026-09-30 [R4fN] Prepare release +work

IN A WEEK
  - 2026-10-02 [xbHi] (3d) Review API mapping +qilab +issuesyncer

NEXT
  [7uYr] Investigate resolver +work +infra
```

The sections are:

- **OVERDUE** — deadlines before today;
- **TODAY** — due today;
- **TOMORROW** — due tomorrow;
- **IN A WEEK** — due from the day after tomorrow through seven days from today;
- **NEXT** — `+next` tasks that were not already shown in a deadline section.
- **WAITING** — `+wait` or `+wait:PERSON` tasks not already shown above.
- **INBOX** — unprocessed `+inbox` tasks not already shown above.

Deadlines outside `TODAY` and `TOMORROW` include a compact relative indication such as `(3d)` or `(2d late)`.

Completed tasks never appear in this view.

## Adding tasks

```sh
tsk a Fix VPN DNS +work +next
```

`+tags` can appear together with the title. Due dates supplied while creating a task are normalized:

```sh
tsk a Renew certificate +work +due:tomorrow
```

The file stores an absolute date:

```text
Renew certificate +work +due:2026-09-30 +inbox
```

Quoting the whole first line works too: `tsk a 'Renew certificate +work +due:tomorrow'`.
Empty titles, multiline titles, and malformed tags are rejected before creation.

A body can be supplied on stdin:

```sh
cat <<'EOF_BODY' | tsk a Investigate outage +work +next
Observed only while connected through the VPN.

Things to check:
- DNS
- routes
- proxy
EOF_BODY
```

## Capture, review, work, and wait

New tasks enter `+inbox` unless an explicit workflow state is supplied. Capture
stays one command; the task remains visible in the daily view until reviewed:

```sh
tsk a Investigate resolver +project:infra
tsk inbox
tsk t xbHi +next             # choose it as current work
tsk t xbHi +wait:marco       # waiting on Marco; removes +next
tsk t xbHi +backlog          # reviewed, deliberately deferred
tsk t xbHi -+inbox           # remove inbox; keep it in the reviewed backlog
```

Adding `+inbox`, `+next`, `+backlog`, `+wait`, or `+wait:PERSON` replaces the other
workflow states. It also reopens a completed task and clears its completion date.
Project, owner, and ordinary tags are retained. Explicit conflicting states on
creation are rejected. Existing files are not migrated: an older open task with
none of these workflow tags belongs to the reviewed backlog, not to the inbox.

```sh
tsk inbox +work
tsk next +project:ace
tsk waiting --sort due
tsk backlog
```

These views accept the same filters, list options, and piped selections as `tsk l`.
`+due` remains a real deadline; inbox, focus, and waiting do not require one.

## Listing and filtering

`tsk l` lists open tasks:

```sh
tsk l
```

Completed tasks are hidden by default.

```sh
tsk l --all       # open and done
tsk l --done      # done only
```

List options can appear before or after filters. `--` ends option parsing.

### Exact tags

```sh
tsk l +work
tsk l +work +qilab
tsk l -+home
```

`+work` means the exact tag `+work`; `-+work` excludes it.

A trailing colon matches a whole namespace. These are equivalent pairs:

```sh
tsk l +owner:               # has any +owner:VALUE tag
tsk l --has owner
tsk l -+owner:              # has no +owner:VALUE tag
tsk l --without owner
```

### Literal text

Normal text filters are case-insensitive literal matches:

```sh
tsk l vpn
tsk l 'API mapping'
tsk l work -legacy
```

Filters are applied sequentially.

### Explicit regular expressions

Regexes are opt-in with `~`:

```sh
tsk l '~vpn|dns'
tsk l -'~old|legacy'
```

Literal matching is the default on purpose: punctuation in a task title should not accidentally become a regular expression.

### Search Markdown notes

`--body` includes the body in literal and regex searches. Tag filters still
inspect only first-line tags, and an exact task ID still selects that task:

```sh
tsk l --body 'ACE-42'
tsk l +work --body '~vpn|resolver'
tsk l --body -legacy
```

### Grouping and ordering

```sh
tsk l +work --group-by project
tsk l +project:ace --group-by owner --sort due
tsk l --sort title
tsk projects +work          # shortcut for --group-by project
tsk team +project:ace       # shortcut for --group-by owner
tsk unassigned              # open tasks without an owner
```

Each group shows a count and the selected task list. Missing values appear under
`(unassigned)`. A task with multiple values is shown in each matching group;
piping the grouped output into a mutation still selects that task only once.

Sort fields are `id` (the default), `title` (case-insensitive), `due`, and
`completed`. Dates sort earliest first with undated tasks last. IDs break ties.
Counts describe task volume, rather than estimated effort or personal capacity.

### Output for scripts

```sh
tsk l +work --ids
tsk l --all --json > tasks.json
tsk l +work --ids | tsk done --dry-run
```

`--ids` prints one full stable ID per line. `--json` prints a JSON array with
`id`, `short_id`, `title`, `tags`, `done`, `due`, `completed`, and `body`. Tag
names omit `+`; absent dates are `null`. The body preserves the text after the
first-line newline, including leading/trailing blank lines. An empty selection
exports `[]` or no IDs and succeeds. Both formats respect filtering and sorting.
Grouping is a text presentation and cannot be combined with either format.

### IDs

Normal output shows a short ID:

```text
[xbHi] Review API mapping +qilab +issuesyncer
```

The full ID remains in the filename, but a unique short ID is accepted anywhere a filter can identify a task:

```sh
tsk e xbHi
tsk done xbHi
```

If a short suffix is not unique, `tsk` shows the full ID instead.

## Tag catalogue

Discover the tags in use and how many open tasks have each one:

```sh
tsk tags
```

The output is sorted alphabetically, with a tab between each tag and its count:

```text
+owner:anna     2
+owner:luca     1
+project:ace    3
+work           4
```

Tags stay case-sensitive, so spelling variants remain visible. Counts represent
tasks using a tag, rather than the number of times it appears in a file.

Tags like `+project:ace` or `+owner:anna` are optional conventions. To list only
values under a particular key, pass that key without `+` or `:`:

```sh
tsk tags project
tsk tags --all project       # include completed tasks
tsk tags --done              # completed tasks only
tsk tags --names             # one +tag per line, without counts
```

A piped selection narrows the catalogue:

```sh
tsk l +work | tsk tags
tsk l +work | tsk tags project
```

An empty archive or selection produces no output and succeeds. Catalogue options
come before the optional key.

## Reviewing a subset

`tsk r` renders the same view as bare `tsk`, but only for a selection:

```sh
tsk r +work
tsk r +qilab +issuesyncer
```

It also composes with pipelines:

```sh
tsk l +work | tsk r
tsk l +work | tsk r +qilab
```

This is useful when the global daily view is too broad but a full flat list is too noisy.

## Showing and editing

`tsk s` outputs the selected Markdown file exactly as stored, using `cat` semantics and adding nothing:

```sh
tsk s xbHi
```

That makes it easy to pipe somewhere else:

```sh
tsk s xbHi | less
tsk s xbHi | mdcat
```

Edit exactly one task with:

```sh
tsk e xbHi
```

or by filtering:

```sh
tsk e 'API mapping'
```

If the selection is ambiguous, the editor is **not** opened. With no filter, `tsk e` opens the latest task:

```sh
tsk e
```

## Completing and reopening

```sh
tsk done xbHi
tsk open xbHi
```

These commands also accept a task list on stdin:

```sh
tsk l +obsolete | tsk done
```

Completion adds `+done` and `+completed:YYYY-MM-DD`, clearing inbox, focus,
backlog, and waiting states. Repeated completion preserves the original date.
Reopening removes the date and returns the task to the inbox. Nothing is moved
to a separate archive. Legacy completed tasks without a date remain undated;
running `done` again does not invent a completion date for them.

### Completion reports

```sh
tsk report
tsk report --group-by owner
tsk report +project:ace --since 'last monday' --until today
tsk report --all-time --group-by project
```

The default period is today and the preceding six calendar days. `--since` and
`--until` are inclusive, accept GNU date expressions, and can also be used with
`tsk l --done`. Reports sort by completion date. `--all-time` clears the date
range and includes undated legacy completions. Reopened tasks are excluded: this
is a report of currently completed work, not a full event history.

## Due dates

Set a deadline using an absolute or GNU `date`-compatible relative expression:

```sh
tsk due 2026-10-05 xbHi
tsk due tomorrow xbHi
tsk due 'next monday' xbHi
```

The stored tag is always normalized to `YYYY-MM-DD`.

Remove the deadline with:

```sh
tsk due - xbHi
```

Pipelines work here too:

```sh
tsk l +release | tsk due friday
```

## Changing tags

Update one task by its exact full or displayed short ID:

```sh
tsk t xbHi +next -+wait
tsk t xbHi +project:ace +owner:anna
```

The ID must identify exactly one task; titles and partial IDs are rejected. An
explicit ID selects that task even when stdin is redirected. Completed tasks
can be updated too.

Omit the ID to update a task selection on stdin:

```sh
tsk l vpn | tsk t +next
tsk l +old | tsk t -+old
tsk l +backend | tsk t +work -+someday
```

The syntax is intentionally strict:

```text
+foo     add +foo
-+foo    remove +foo
```

There is no legacy `-foo` removal syntax.

All requested tag changes are validated before any task is updated. If a write
fails during a bulk operation, the command stops with a nonzero exit status;
earlier successful updates are retained.

## Preview bulk changes

Put `--dry-run` immediately after a mutation command. It validates the request
and prints the action, count, and selected task list without changing task files:

```sh
tsk done --dry-run +project:ace
tsk open --dry-run xbHi
tsk due --dry-run friday +project:ace
tsk t --dry-run xbHi +owner:anna
tsk l +work --ids | tsk t --dry-run +next
tsk l +discard | tsk d --dry-run
```

Removing `--dry-run` applies the same selection rules. As with other bulk
operations, writes are atomic per file; an I/O failure stops the command and
retains earlier successful updates.

## Deleting tasks

```sh
tsk d xbHi
```

When used interactively, deletion asks for confirmation. A piped selection can be deleted in bulk:

```sh
tsk l +discard | tsk d
```

## Task directory

Print the effective task directory with:

```sh
tsk dir
```

This is especially useful for extensions and shell scripts:

```sh
cd "$(tsk dir)"
```

## Integrity check

`check` is intentionally kept out of the everyday workflow, but is useful after manual file editing or in tests:

```sh
tsk check
```

A healthy archive prints:

```text
ok: no problems found
```

It checks titles, task IDs, tag syntax, duplicate tags, deadline/completion dates, and
unresolved Git conflict markers anywhere in task files. An empty archive is valid.

## Pipes are part of the interface

`tsk l` output can be fed back into commands that operate on selections:

```sh
tsk l +work | tsk r
tsk l vpn | tsk done
tsk l +work | tsk t +next
tsk l +home | tsk due tomorrow
```

This is not an accidental implementation detail. It is one of the main interfaces of `tsk`.

Build a list with `l`; do something with it.

## Extensions

The core deliberately knows very little.

If `tsk` receives an unknown command, it looks for an executable named `tsk-COMMAND` in `PATH`:

```text
tsk fzf  ->  tsk-fzf
tsk git  ->  tsk-git
tsk g    ->  tsk-git
tsk y    ->  tsk-y
tsk issue -> tsk-issue
```

This is how optional features stay optional.

### `tsk-fzf`

`tsk-fzf` is a small interactive selector built on [`fzf`](https://github.com/junegunn/fzf).

```sh
tsk fzf
tsk fzf +work
tsk fzf +work -+done
tsk fzf -q resolver
```

`+tag` and `-+tag` positional arguments are automatically passed to `tsk l` as pre-filters. Use `-f` for any other `tsk` filter:

```sh
tsk fzf -f vpn
tsk fzf -f '~vpn|dns'
```

Other positional arguments become the initial fuzzy query.

The interface intentionally has very few actions:

```text
Enter    print selected task(s), in the same format as `tsk l`
Tab      multi-select
Ctrl-e   edit current task
Ctrl-a   add a task, using the current query as a suggestion
Ctrl-d   mark selected task(s) done
Alt-p    show/hide the preview
```

The preview starts **hidden**. When enabled it displays the raw Markdown through `tsk s`.

The reduced binding set is intentional: if an operation is uncommon, exit fzf and use the normal CLI rather than turning the selector into another task-management UI to learn.

Environment variables:

```text
TSK_FZF_FZF       fzf executable (default: fzf)
TSK_FZF_HISTORY   fzf history file (default: ~/.fzfhistory-tsk)
```

### `tsk-git`

A tiny wrapper that runs Git in the current task directory:

```sh
tsk git status
tsk git diff
tsk git log --oneline
```

`tsk g` is a shorter alias, with the same arguments and exit status:

```sh
tsk g status
tsk g diff
```

It is essentially:

```sh
git -C "$(tsk dir)" ...
```

### `tsk-y`

`tsk-y` is a convenience sync script for a Git-backed task directory:

```sh
tsk y
tsk y update tasks
```

The task directory must be the root of its own Git repository, with an upstream
configured. This prevents staging unrelated files from a containing repository.

`tsk-y` validates the archive, stages changes, commits if needed, then pulls with
an explicit merge policy and pushes. Pull and push also run when there is nothing
new to commit. The merged archive is validated again before pushing.

Unresolved conflicts and unfinished merges, rebases, cherry-picks, or reverts stop
the sync before staging. Resolve and finish the Git operation with Git before
running `tsk y` again. It is intentionally external because Git synchronization
policy is not part of the task-manager core.

### Issue links, browser, and imports

Install `tsk-issue` alongside `tsk` using `just link`, or copy both executables to
`PATH`. This extension requires Python 3 and uses the same task-directory lock.

```sh
tsk issue set xbHi ACE-42 https://jira.example.com/browse/ACE-42
tsk issue set --dry-run xbHi ACE-42 https://jira.example.com/browse/ACE-42
tsk browse xbHi
tsk browse --print xbHi
```

Linking requires an exact ID, adds/replaces `+issue:KEY`, and records a primary
Markdown link as `Issue: [KEY](<URL>)` in the notes. Replacing it preserves other
notes and tags. `tsk browse` opens that link with `xdg-open`; `BROWSER` can specify
another program with arguments. `--print` prints the URL without opening it.
Links use HTTP(S) URLs.

Import a selected JSON export, or restore a `tsk l --all --json` export:

```sh
tsk import tasks.json --dry-run
tsk import tasks.json
tsk import jira-issues.json --only-project ACE --only-open --owner anna
tsk import gitlab-issues.json --source gitlab --tag work
tsk import redmine-issues.json --base-url https://redmine.example.com --closed-status 5
cat issues.json | tsk import -
```

Supported inputs are a JSON array, an object containing `issues` or `tasks`, or a
single issue. `--source auto` detects tsk exports and common issue response fields
from [Jira](https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-search/),
[GitLab](https://docs.gitlab.com/api/issues/), and
[Redmine](https://www.redmine.org/projects/redmine/wiki/Rest_Issues).
`--source` can select a format explicitly. Supply `--base-url` when the data lacks
a browser URL, particularly for Redmine. Jira rich-text descriptions are flattened
to readable notes. Redmine closed status IDs can be supplied with repeated
`--closed-status`; an available `closed_on` date also identifies a completion.

Provider project/assignee labels are normalized to ASCII tag values. `--project`
and `--owner` override them; repeated `--tag` adds tags. `--only-project` filters
the resulting project tag and `--only-open` excludes completed issues. Existing
issue URLs and task IDs are skipped, preserving local edits. Duplicate records
in one input are skipped too. Imports add files without updating remote services.
The complete input is validated before writing, and `--dry-run` changes no files.
An I/O error can retain earlier successfully imported tasks.

A provider-independent import can use this shape:

```json
[
  {
    "title": "Review API mapping",
    "key": "ACE-42",
    "url": "https://issues.example.com/ACE-42",
    "project": "ace",
    "owner": "anna",
    "tags": ["work"],
    "body": "Markdown notes",
    "due": "2026-12-01",
    "done": false
  }
]
```

`key` and `url` are optional together. Tags omit `+`. Closed imports may include
an ISO `completed` date; missing completion dates remain unknown. Open imports
enter the inbox unless they carry a workflow state. Restoring a tsk JSON export
preserves full IDs, tag order, and the body. Import never overwrites an existing ID.

## Environment

The core understands only two user-facing environment variables:

| Variable | Meaning | Default |
| --- | --- | --- |
| `TSK_DIR` | task directory | `$HOME/.tsk` |
| `EDITOR` | editor used by `tsk e` | `vi` |

That is the whole configuration surface of the core.

## Command reference

```text
tsk                         daily view
tsk r [FILTERS...]          review a filtered/piped selection
tsk a TITLE [TAGS...]       add task
tsk l [OPTIONS] [FILTERS]   list tasks
tsk inbox|next|backlog      workflow views
tsk waiting|unassigned     waiting tasks or tasks without an owner
tsk projects|team          group tasks by project or owner
tsk report [OPTIONS]       completions from the last seven days
tsk tags [OPTIONS] [KEY]    list tags and task counts; optionally KEY: tags
tsk s FILTERS...            cat task file(s) unchanged
tsk e [FILTERS...]          edit one task; latest when omitted
tsk done FILTERS...         complete tasks
tsk open FILTERS...         reopen tasks
tsk due DATE FILTERS...     set deadline; '-' removes it
tsk t [ID] CHANGES...       modify tags on one ID or tasks from stdin
tsk d FILTERS...            delete tasks
tsk dir                     print task directory
tsk check                   validate task files
tsk g [ARGS...]             alias for tsk git
tsk issue set ID KEY URL   associate an issue
tsk browse [--print] ID    open or print the associated issue URL
tsk import FILE [OPTIONS] import JSON tasks/issues; '-' reads stdin
tsk h                       help
```

List options:

```text
--all                       include completed tasks
--done                      only completed tasks
--group-by KEY              group by a tag namespace (text output)
--sort FIELD                id, title, due, or completed
--body                      search Markdown notes as well as the first line
--has KEY                   require a namespace such as owner
--without KEY               exclude a namespace
--ids                       one full stable ID per line
--json                      structured task data and Markdown bodies
--since DATE                completions on or after DATE
--until DATE                completions on or before DATE
--all-time                  clear the completion date range
```

Tag catalogue options:

```text
--all                       count open and completed tasks
--done                      count completed tasks only
--names                     print tag names without counts
```

Filters:

```text
+foo                        exact tag
-+foo                       exclude exact tag
+key:                       require any tag under key
-+key:                      exclude any tag under key
text                        case-insensitive literal text
-text                       exclude literal text
~REGEX                      case-insensitive regex
-~REGEX                     exclude regex
ID                          full or displayed short task ID
```

## Testing

The repository contains black-box tests for the core and extensions. Running the
tests requires Python 3, Git, and Bash 4 or newer in addition to the runtime
dependencies:

```sh
just test
```

or directly:

```sh
./tests/test.sh
```

The tests exercise the CLI, including failed writes, concurrent updates, editor
terminal handling, and Git synchronization against temporary local repositories.
They leave the user's task archive untouched. CI runs them before mirroring.
Completion tests also exercise Tab insertion in an interactive Bash terminal.

## Design philosophy

The useful mental model is intentionally tiny:

```text
Task       = Markdown file
Metadata   = +tags on the first line
Done       = +done
Focus      = +next
Deadline   = +due:YYYY-MM-DD
Workflow   = +inbox, +next, +backlog, +wait[:PERSON], +done
Completed  = +completed:YYYY-MM-DD
Selection  = filters and pipes
Editor     = $EDITOR
Extensions = tsk-* executables
```

That is enough.

If you need a project, use a tag. If you need notes, write Markdown. If you need an interactive picker, use `tsk-fzf`. If you need Git, use Git.

And if managing the task manager starts taking longer than doing the task, something has gone wrong.
