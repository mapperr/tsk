# tsk

> Plain-text task management for people who think a database is an awfully dramatic way to remember “fix DNS”.

`tsk` is a small command-line task manager built around a deliberately boring idea:

```text
one task = one Markdown file
```

Everything else grows from that. Tags describe metadata, task IDs create relationships, Git provides history and synchronization, and normal Unix pipes glue commands together.

```sh
tsk a Fix the login bug +work +next
tsk agenda
tsk tree @ace
tsk portfolio --owners
```

No daemon. No account. No cloud service. No hidden state. No sprint ceremony unless you bring your own.

## Features

* one Markdown file per task;
* shell-friendly `+tags`;
* exact tag, regex, negative, and project/subtree filters;
* Markdown bodies editable with `$EDITOR`;
* due dates with human-friendly CLI input;
* parent/child task hierarchies;
* dependencies, blockers, backlinks, and generic links;
* project trees and project portfolio views;
* `agenda` for the small set of tasks that actually need attention;
* team ownership with `+owner:name`;
* personal and team workload views;
* integrity checking for broken links and cycles;
* Git-based history and team synchronization;
* stdin/stdout composition;
* external commands such as `tsk-fzf` through a tiny extension mechanism;
* no persistent index or database to repair at 2 AM.

The database is a directory. The API is a pipe. The audit log can be Git.

---

## Installation

`tsk` is a single shell script.

```sh
git clone https://git.sr.ht/~mapperr/tsk
cd tsk
install -m 0755 tsk "$HOME/.local/bin/tsk"
```

Make sure `~/.local/bin` is in `PATH`:

```sh
export PATH="$HOME/.local/bin:$PATH"
```

Then:

```sh
tsk h
```

By default tasks live in:

```text
~/.tsk
```

Use another directory with:

```sh
export TSK_DIR="$HOME/tasks"
```

### Requirements

`tsk` uses a POSIX-style `/bin/sh`, but targets a Linux/GNU-ish userspace. In particular, date handling uses GNU `date` features such as `date -d`.

It expects the usual command-line toolbox: `awk`, `grep`, `sed`, `date`, `mktemp`, `sort`, `cut`, `tr`, `dd`, and friends.

Optional but useful:

* **Git** for history, synchronization, and team use;
* **mdcat** for rendered Markdown output;
* **fzf** for an interactive frontend;
* **ripgrep**, **bat**, and **Graphviz** because plain text enjoys good company.

---

## The data model

A task is stored as a file such as:

```text
20260831152700123-AbC1.tsk.md
```

The filename, minus `.tsk.md`, is the task's stable ID.

The first line contains the title and metadata:

```text
Implement OAuth refresh +work +next +owner:michele +due:2026-09-04
```

Everything below the first line is ordinary Markdown:

```markdown
Implement OAuth refresh +work +next +owner:michele +due:2026-09-04

Rotate the refresh token after a successful refresh.

## Notes

- keep the old token valid during the grace period
- add integration tests
- document failure cases
```

There is no sidecar metadata file and no database row hiding somewhere else.

### Tags

`tsk` uses `+` as the only tag sigil:

```text
+work
+linux
+client-acme
+owner:michele
+due:2026-09-04
```

`+` is intentionally used instead of `#`: shells already have opinions about `#`, and they are not negotiable.

Tags can be completely free-form, but some have semantic meaning:

| Tag               | Meaning                       |
| ----------------- | ----------------------------- |
| `+done`           | completed task                |
| `+due:YYYY-MM-DD` | due date                      |
| `+parent:<id>`    | parent task                   |
| `+depends:<id>`   | dependency                    |
| `+link:<id>`      | generic relationship          |
| `+project`        | project root                  |
| `+owner:<name>`   | team owner                    |
| `+next`           | actionable next task          |
| `+waiting`        | waiting on something external |

A task can have zero or one parent and zero or one owner.

### Derived state

Some information is deliberately **not** stored twice.

If task A contains:

```text
+depends:B
```

then `tsk` can derive both:

```text
A depends on B
B blocks A
```

Likewise, children, backlinks, blocked state, project membership, and overdue state are calculated dynamically.

Store one fact. Derive the reverse view. Avoid synchronized lies.

---

## Quick start

Create a task:

```sh
tsk a Buy coffee +personal +next
```

List tasks:

```sh
tsk l
```

Filter them:

```sh
tsk l +personal
tsk l +next -+done
```

Show a task:

```sh
tsk s coffee
```

Edit it:

```sh
tsk e coffee
```

Complete it:

```sh
tsk done coffee
```

Or let the pipe do the talking:

```sh
tsk l coffee | tsk done
```

You are now managing tasks without creating a workspace, board, sprint, epic, or field named `Priority 2`.

---

## Filtering

Filters are a core part of `tsk`. They are applied **sequentially**, so combinations behave like a pipeline of selections.

### Exact tag filters

```sh
tsk l +work
```

matches the exact tag `+work`.

Exclude it with:

```sh
tsk l -+work
```

Exact means exact: `+work` does not match `+work-old`.

### Text and regex filters

Other filters are case-insensitive grep patterns over the rendered task line:

```sh
tsk l oauth
tsk l 'oauth|oidc'
tsk l backend -legacy
```

A leading `-` negates a normal filter:

```sh
tsk l work -obsolete
```

### Project and subtree filters

`@pattern` selects a matching root plus all descendants:

```sh
tsk l @ace
tsk tree @ace
tsk agenda @ace
tsk report @ace
```

Matching `+project` tasks are preferred as subtree roots. If there is no matching project, a normal task can become the root.

Exclude an entire subtree with:

```sh
tsk l -@legacy
```

Combine filters freely:

```sh
tsk l @ace +next -+waiting
tsk agenda @ace +owner:michele
tsk report @ace -+done
```

### Exact task IDs

Existing IDs can be used directly:

```sh
tsk i 20260831152700123-AbC1
```

An existing ID is treated as an ID, not as an accidental regex that happens to occur inside somebody else's `+parent:` or `+depends:` tag.

### Search inside task bodies

`tsk ll` searches the body rather than the first-line record:

```sh
tsk ll postgres
tsk ll 'timeout|retry'
```

Metadata and subtree filters still work:

```sh
tsk ll @ace +work postgres
```

Meaning: search for `postgres` in bodies, but only inside ACE tasks tagged `+work`.

---

## Unix pipelines

The output of `tsk l` is designed to be fed back into `tsk`.

```sh
tsk l +next | tsk done
```

Bulk tag changes:

```sh
tsk l @ace +backend | tsk t +review
tsk l +review | tsk t -review
```

Bulk assignment:

```sh
tsk l @ace +backend | tsk assign lorenzo
```

Bulk due date:

```sh
tsk l 'release docs' | tsk due 'next monday'
```

Narrow an existing selection:

```sh
tsk l @ace | tsk report +owner:michele
```

Task IDs received from stdin are validated against real task files before they are used.

---

## Task bodies and editing

A body is just Markdown.

Create one from stdin:

```sh
cat <<'TASK_BODY' | tsk a Investigate login timeout +work +next
Reproduce through the VPN.

## Check

- DNS
- proxy timeout
- OAuth refresh
TASK_BODY
```

Show a task:

```sh
tsk s login
```

`tsk s` uses `mdcat` when available and otherwise falls back to `cat`.

Force plain output:

```sh
tsk ss login
```

Edit one task in `$EDITOR`:

```sh
tsk e login
```

With no filter, `tsk e` opens the most recently created task:

```sh
tsk e
```

---

## State and due dates

### Complete and reopen

```sh
tsk done oauth
tsk open oauth
```

Short aliases:

```sh
tsk c oauth
tsk u oauth
```

Completion is represented by the semantic done tag; tasks are not moved to a special archive directory.

### Due dates

```sh
tsk due 2026-09-04 oauth
tsk due tomorrow oauth
tsk due 'next monday' oauth
```

Relative values are normalized before storage, so the task contains an absolute tag:

```text
+due:2026-09-07
```

Remove a due date with:

```sh
tsk due - oauth
```

Humans can say “next Monday”. Files should not wake up on Tuesday with a different interpretation.

---

## Projects and hierarchy

A project is simply a task tagged `+project`:

```sh
tsk a ACE certification +project +work
```

Create a child task:

```sh
tsk a Implement certification API +work +next
tsk l 'Implement certification API' | tsk link parent 'ACE certification'
```

Create another level:

```sh
tsk a Integration tests +work
tsk l 'Integration tests' | tsk link parent 'Implement certification API'
```

Then:

```sh
tsk tree @ace
```

can produce:

```text
[ ] [P1] ACE certification
  [ ] [A1] Implement certification API
    [ ] [T1] Integration tests
```

Project membership is structural: descendants belong to the project through `+parent:`. You do not need to copy a project tag onto every task.

Remove a parent:

```sh
tsk l 'Integration tests' | tsk unlink parent
```

Parent cycles are rejected.

---

## Dependencies and links

Hierarchy answers **“what is this part of?”**.

Dependencies answer **“what must happen first?”**.

Generic links answer **“what else is related?”**.

### Dependency

```sh
tsk l deploy | tsk link depends 'integration tests'
```

If `integration tests` is not done, `deploy` is automatically considered blocked.

Remove the relation:

```sh
tsk l deploy | tsk unlink depends 'integration tests'
```

Dependency cycles are rejected.

### Generic relation

```sh
tsk l docs | tsk link related api
```

`related` is an alias for relation type `link`.

```sh
tsk l docs | tsk unlink link api
```

### Inspect one task in context

```sh
tsk i deploy
```

`info` shows the task plus relevant context such as owner, state, parent, children, dependencies, blockers, and related tasks.

---

## Panoramic views

A list answers “what exists?”. The other views answer more useful questions.

### `tree`: how is the work structured?

```sh
tsk tree
tsk tree @ace
tsk tree +work
```

`tree` renders the parent/child hierarchy.

### `report`: what is the state of this selection?

```sh
tsk report
tsk r @ace
tsk r @ace +work -+done
```

A report summarizes:

* total, open, and done tasks;
* due and overdue tasks;
* blocked tasks and blockers;
* roots and subtree counts;
* tag frequencies.

The filters define the report universe.

### `agenda`: what deserves attention now?

```sh
tsk agenda
tsk agenda @ace
tsk agenda +owner:michele
```

The agenda focuses on:

1. overdue tasks;
2. tasks due today;
3. blocked or `+waiting` tasks;
4. actionable `+next` tasks.

A blocked task tagged `+next` is shown under blocked work, not twice.

### `portfolio`: how are the projects doing?

```sh
tsk portfolio
```

Example:

```text
PROJECTS  3

  OPEN  BLOCKED  OVERDUE  PROJECT
     6        1        1  [ ] [P1] ACE
     3        0        0  [ ] [P2] tsk
     8        2        0  [ ] [P3] Issue Syncer
```

Counts include each selected project's whole descendant tree.

Filters work here too:

```sh
tsk portfolio +work
tsk portfolio @ace
```

The heavier views use a temporary metadata snapshot instead of repeatedly reparsing the whole archive, so `tree`, `report`, `agenda`, and portfolio views remain quick as the task collection grows.

---

## Team mode

Team mode keeps exactly the same storage model. The only new persistent concept is ownership:

```text
+owner:michele
```

Set your local identity:

```sh
export TSK_USER=michele
```

### Assign work

```sh
tsk assign lorenzo oauth
```

or:

```sh
tsk l @ace +backend | tsk assign lorenzo
```

Assign to yourself:

```sh
tsk assign me oauth
```

Assignment replaces any existing owner. One task, at most one owner.

### Claim work

`claim` uses `TSK_USER` and refuses tasks already owned by someone else.

A safe pattern is:

```sh
tsk unassigned +next | tsk claim
```

If ownership must change, do it explicitly:

```sh
tsk assign michele oauth
```

No silent task stealing. Civilization survives another day.

### Release work

```sh
tsk unassign oauth
```

Alias:

```sh
tsk release oauth
```

### My agenda

```sh
tsk mine
```

uses `TSK_USER` and shows your agenda.

```sh
tsk mine @ace
tsk mine +work
```

### Unassigned work

```sh
tsk unassigned
tsk unassigned @ace
```

Project-root tasks are ignored because a project is normally a container/result rather than somebody's work item.

### Owner portfolio

```sh
tsk portfolio --owners
```

Example:

```text
OWNERS  3

  OPEN  NEXT  BLOCKED  OVERDUE  OWNER
     8     3        1        0  lorenzo
     5     2        0        1  michele
     2     1        0        0  (unassigned)
```

Filter it by project or metadata:

```sh
tsk portfolio --owners @ace
```

### Ownership policies

Require every non-project task to have an owner during `tsk check`:

```sh
export TSK_REQUIRE_OWNER=1
```

Automatically assign newly created non-project tasks to yourself:

```sh
export TSK_USER=michele
export TSK_AUTO_ASSIGN=1
```

Now:

```sh
tsk a Implement endpoint +next
```

gets:

```text
+owner:michele
```

Project roots are intentionally not auto-assigned.

### Recommended team vocabulary

A small vocabulary is usually enough:

```text
+project          project root
+owner:name       responsibility
+next             actionable now
+waiting          waiting outside the tracked dependency graph
+depends:ID       blocked by another tracked task
+due:DATE         real deadline
+done             completed
```

If your workflow eventually needs seventeen states, `tsk` will not physically stop you. It may judge you quietly.

---

## Git synchronization

A task directory can be a normal Git repository.

```sh
cd "$TSK_DIR"
git init
git add .
git commit -m 'initial tasks'
```

Run Git inside `TSK_DIR` through:

```sh
tsk g status
tsk g log --oneline
tsk g diff
```

Synchronize with:

```sh
tsk sync
```

Historical short alias:

```sh
tsk y
```

Optional commit message:

```sh
tsk sync 'update ACE tasks'
```

The workflow is:

```text
stage local changes
        ↓
commit when needed
        ↓
pull --rebase
        ↓
push
```

One-file-per-task works nicely with Git: two people editing different tasks normally touch different files.

If two people edit the same task incompatibly, Git can produce a conflict. `tsk` leaves that conflict for explicit manual resolution rather than inventing a policy about whose deadline or owner wins.

Git history also becomes a useful audit trail:

```sh
tsk g log --stat
tsk g log -p -- path/to/task.tsk.md
```

---

## Integrity checking

```sh
tsk check
```

checks the archive for problems including:

* invalid task IDs;
* empty titles;
* malformed or duplicate tags;
* multiple parents;
* multiple due dates or invalid dates;
* multiple or invalid owners;
* broken relations;
* self-relations;
* parent cycles;
* dependency cycles;
* missing owners when `TSK_REQUIRE_OWNER=1`.

Healthy output:

```text
ok: no problems found
```

For a shared repository, `tsk check` is a good candidate for CI or a Git hook:

```sh
#!/bin/sh
exec tsk check
```

Plain text gets freedom. `tsk check` gets the clipboard and safety goggles.

---

## fzf and extensions

`tsk` has a deliberately tiny external-command mechanism.

If you run:

```sh
tsk foo
```

and an executable called:

```text
tsk-foo
```

exists in `PATH`, `tsk` runs it.

This keeps optional interfaces outside the core.

### `tsk-fzf`

Install a `tsk-fzf` executable in `PATH` and use:

```sh
tsk fzf
tsk fzf @ace
tsk fzf @ace +next
```

An fzf frontend is a natural place for fuzzy selection, preview, multi-select, edit/show actions, tagging, due dates, and quick state changes.

Core `tsk` remains a script. `fzf` remains frighteningly good at selecting things. Everyone stays in their lane.

### Other tools

Because tasks are files, the rest of Unix is still available:

```sh
rg 'postgres|tenant' "$TSK_DIR"
git -C "$TSK_DIR" grep OAuth
```

`bat` works well for previews. Graphviz is a natural target for custom dependency graph exporters. Shell aliases are excellent saved views.

Text is already a pretty good integration format.

---

## Environment variables

| Variable            | Purpose                                      | Default                          |
| ------------------- | -------------------------------------------- | -------------------------------- |
| `TSK_DIR`           | task directory                               | `$HOME/.tsk`                     |
| `EDITOR`            | editor for `tsk e`                           | `vi`                             |
| `TSK_CATCMD`        | task renderer for `tsk s`                    | `mdcat` if available, else `cat` |
| `TSK_DONE_TAG`      | completion tag name                          | `done`                           |
| `TSK_USER`          | local team identity                          | unset                            |
| `TSK_REQUIRE_OWNER` | make missing owners a `check` error when `1` | `0`                              |
| `TSK_AUTO_ASSIGN`   | auto-assign new non-project tasks when `1`   | `0`                              |
| `TSK_DEBUG`         | diagnostic output when set                   | unset                            |

Typical personal setup:

```sh
export TSK_DIR="$HOME/.tsk"
export EDITOR=vis
```

Typical team setup:

```sh
export TSK_DIR="$HOME/src/team-tasks"
export TSK_USER=michele
export TSK_REQUIRE_OWNER=1
```

Optional auto-assignment:

```sh
export TSK_AUTO_ASSIGN=1
```

---

## Command reference

### Tasks

```text
tsk l [filters...]                 list tasks
tsk ll [filters...]                search task bodies
tsk a <title and tags>             add a task
tsk s [filters...]                 show tasks
tsk ss [filters...]                show tasks with plain cat output
tsk e [filters...]                 edit exactly one task
tsk i [filters...]                 inspect one task and its relations
tsk d [--force] [filters...]       delete tasks
```

Deletion is refused while other tasks reference the selected task unless `--force` is used. Interactive, non-piped deletion asks for confirmation.

### Tags and state

```text
tsk t <+tag|-tag>...               modify tags on piped tasks
tsk done [filters...]              mark done (alias: c)
tsk open [filters...]              reopen (alias: u)
tsk due <date|-> [filters...]      set/remove due date
```

### Team

```text
tsk assign <owner|me> [filters...] assign/transfer ownership
tsk claim [filters...]             claim as TSK_USER; refuses other owners
tsk unassign [filters...]          remove owner (alias: release)
tsk mine [filters...]              agenda for TSK_USER
tsk unassigned [filters...]        list unowned non-project tasks
```

### Relations

Source tasks for `link`/`unlink` are supplied through stdin:

```text
tsk link parent <target filters...>
tsk link depends <target filters...>
tsk link link <target filters...>
tsk link related <target filters...>   # alias for link

tsk unlink parent [target filters...]
tsk unlink depends <target filters...>
tsk unlink link <target filters...>
```

### Views

```text
tsk tree [filters...]              hierarchy
tsk report [filters...]            overview (alias: r)
tsk agenda [filters...]            overdue/today/blocked/next
tsk portfolio [filters...]         project portfolio (alias: p)
tsk portfolio --owners [filters...] owner workload
tsk check                          integrity check
```

### Git and escape hatches

```text
tsk g <git args...>                run Git inside TSK_DIR
tsk sync [commit message]          commit, pull --rebase, push
tsk y [commit message]             alias for sync
tsk run <command...>               run an arbitrary command
tsk <name> ...                     run external tsk-<name> from PATH
```

---

## Useful workflows

### Keep a small working set

Your archive may contain hundreds of tasks. Your `+next` set should not.

```sh
tsk l +next -+done
tsk agenda
```

Use `+waiting` when something is externally stalled, and `+depends:` when the blocker is another tracked task.

### Work inside a project

```sh
tsk tree @ace
tsk agenda @ace
tsk report @ace
```

The `@` filter makes project context cheap enough to use constantly.

### Personal team dashboard

```sh
tsk mine
tsk mine @ace
```

### Team dashboard

```sh
tsk portfolio
tsk portfolio --owners
tsk unassigned
```

### Safe shared-repository routine

```sh
tsk check && tsk sync 'update tasks'
```

### Shell aliases are encouraged

```sh
alias ta='tsk agenda'
alias tm='tsk mine'
alias tp='tsk portfolio'
alias tpo='tsk portfolio --owners'
alias tn='tsk l +next -+done'
```

No points are awarded for typing the same filter twelve times per day.

---

## Design notes

### Why one file per task?

Because it gives you readable storage, easy scripting, cheap backups, useful Git history, and fewer merge conflicts than one giant task file.

### Why is a project also a task?

Because a project can already have a title, Markdown notes, a due date, links, children, history, and tags. Introducing a separate project entity would mostly introduce a separate place to keep synchronized.

### Why no stored `blocked` tag?

Because blocked state is a consequence of dependencies. If the dependency becomes done, the task should stop being blocked automatically.

### Why no database?

A database would make some queries easier while making the storage less transparent. For the intended scale—personal use and small technical teams with hundreds or a few thousand tasks—the snapshot-based views are fast enough without giving up plain files.

### Is this Jira?

No.

If you need complex permissions, SLA escalation, comments, attachments, notifications, approval workflows, dozens of custom fields, and a quarterly committee to decide whether yellow means “at risk” or “slightly concerned”, use a system designed for that.

`tsk` is for people who want to type:

```sh
tsk mine @ace
```

see the work, and get back to doing it.

---

## Philosophy in one screen

```text
Task                  = Markdown file
Metadata              = +tags on the first line
Project               = task tagged +project
Project membership    = +parent relation
Dependency            = +depends relation
Ownership             = +owner:name
Actionable work       = +next
External waiting      = +waiting
Completion            = +done
Deadline              = +due:YYYY-MM-DD
Search                = filters + ll
Automation            = pipes
Interactive UI        = fzf, if desired
Synchronization       = Git
Integrity             = tsk check
```

Small model. Useful consequences.

Now go finish a task.
