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

If you want more interface around that core, optional `tsk-*` executables extend it without making the core larger. This repository currently includes `tsk-fzf`, `tsk-git`, and `tsk-y`.

## Why

Task managers have a tendency to become hobbies.

`tsk` tries not to.

It keeps only three built-in pieces of task metadata:

```text
+done             completed
+next             part of the current working set
+due:YYYY-MM-DD   deadline
```

Every other `+tag` is just a tag. Projects, areas, clients, contexts, and whatever else you care about do not require new entities or configuration:

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
`mv`), a POSIX awk, and `flock` from util-linux. GNU `date` handles relative dates
such as `tomorrow` and `next monday`.

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
directory. Changes made directly by other tools do not participate in this lock.
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
Renew certificate +work +due:2026-09-30
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

### Exact tags

```sh
tsk l +work
tsk l +work +qilab
tsk l -+home
```

`+work` means the exact tag `+work`; `-+work` excludes it.

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

Completion is stored as the `+done` tag. Nothing is moved to a separate archive.

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

Tag changes deliberately require a task selection on stdin:

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

It checks titles, task IDs, tag syntax, duplicate tags, calendar dates, and
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
tsk y    ->  tsk-y
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
tsk s FILTERS...            cat task file(s) unchanged
tsk e [FILTERS...]          edit one task; latest when omitted
tsk done FILTERS...         complete tasks
tsk open FILTERS...         reopen tasks
tsk due DATE FILTERS...     set deadline; '-' removes it
tsk t CHANGES...            modify tags on tasks from stdin
tsk d FILTERS...            delete tasks
tsk dir                     print task directory
tsk check                   validate task files
tsk h                       help
```

List options:

```text
--all                       include completed tasks
--done                      only completed tasks
```

Filters:

```text
+foo                        exact tag
-+foo                       exclude exact tag
text                        case-insensitive literal text
-text                       exclude literal text
~REGEX                      case-insensitive regex
-~REGEX                     exclude regex
ID                          full or displayed short task ID
```

## Testing

The repository contains black-box tests for the core and extensions. Running the
tests requires Python 3 and Git in addition to the runtime dependencies:

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

## Design philosophy

The useful mental model is intentionally tiny:

```text
Task       = Markdown file
Metadata   = +tags on the first line
Done       = +done
Focus      = +next
Deadline   = +due:YYYY-MM-DD
Selection  = filters and pipes
Editor     = $EDITOR
Extensions = tsk-* executables
```

That is enough.

If you need a project, use a tag. If you need notes, write Markdown. If you need an interactive picker, use `tsk-fzf`. If you need Git, use Git.

And if managing the task manager starts taking longer than doing the task, something has gone wrong.
