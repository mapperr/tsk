# tsk

A cli task management tool.

`tsk` only concepts are *tasks* and *tags*.

Tasks are markdown files which have title and tags in the first line.
The rest of the file is the task body.

Thas's it.

## Installation

Clone the repo and copy or link `tsk` into your PATH.

## Usage

```
Usage [v0.9.0]:
    tsk l [filters..]
        shows the task list, eventually filtered
        filters are applied sequentially; prefix a filter with '-' to exclude it.
        '+tag' matches an exact tag; '-+tag' excludes it.
        '@pattern' selects a project/subtree (root plus all descendants);
        '-@pattern' excludes that subtree.

    tsk ll [filters..]
        searches task bodies, applying filters sequentially; '+tag' and '-+tag'
        still act as exact metadata tag filters. You can pipe in the result of
        another 'tsk l' to narrow the search

    tsk a <title and tags>
        adds a new task; the task body can be piped on stdin, e.g.:
        echo 'develop some web application' | tsk a Do something +dev +due:tomorrow
        relative due dates are normalized when the task is created

    tsk d [--force] [filters..]
        deletes tasks. Piped selections are not confirmed.
        deletion is refused when other tasks reference the selected tasks,
        unless --force is used.

    tsk e [filters..]
        opens exactly one task in $EDITOR
        if no filter is passed, opens the last created task
        you can pipe in one task filtered from 'tsk l'

    tsk s [filters..]
    tsk ss [filters..]
        shows tasks to stdout. 'ss' forces plain cat output.
        you can pipe in a list filtered from 'tsk l'

    tsk t <tag changes>...
        changes tags on the task list piped on stdin
        syntax: '+tag' to add, '-tag' to remove

    tsk done [filters..]       (alias: c)
        marks selected tasks as done
    tsk open [filters..]       (alias: u)
        removes the done tag from selected tasks
    tsk due <date|-> [filters..]
        sets a normalized due date on selected tasks; '-' removes it
        date accepts GNU date expressions such as 'tomorrow' or 'next monday'

    tsk link <parent|depends|link> <target filters..>
        adds a relation from tasks piped on stdin to exactly one target task
        'related' can be used as an alias for relation type 'link'
    tsk unlink <parent|depends|link> [target filters..]
        removes a relation from tasks piped on stdin
        for parent, omitting the target removes the current parent

    tsk i [filters..]
        shows one task together with parents, children, dependencies,
        blockers and related tasks
    tsk tree [filters..]
        shows the parent/child hierarchy; without filters starts from roots
    tsk r [filters..]
        prints an overview of open/done, due, blocked and root tasks and tags
        for the selected tasks; accepts the same filters and piped selections as 'l'
    tsk agenda [filters..]
        shows overdue, due-today, blocked/waiting and +next tasks
    tsk portfolio [filters..]  (alias: p)
        shows +project roots with open, blocked and overdue task counts
    tsk check
        checks task metadata and relation integrity

    tsk g [git cmds/args]
        executes git commands in the tsk directory, e.g.: tsk g pull
    tsk y [commit msg]
        git add/commit, then pull --rebase and push in the tsk directory

    tsk h
        shows extended help

tsk files:
    A task is one Markdown file. The first line contains the task title followed
    by tags; the body starts on the second line. Files are named with the task
    creation timestamp and a short random suffix.

tags:
    A tag is '+value' or '+key:value'. Components may contain letters, numbers,
    underscores '_' and dashes '-'. Some tags have conventional semantics:

        +done             completed task
        +due:YYYY-MM-DD           due date
        +parent:<task-id>         hierarchy (one parent per task)
        +depends:<task-id>        dependency
        +link:<task-id>           generic relation
        +project                  project root
        +next                     actionable next task
        +waiting                  waiting on something external

    Backlinks, children, blockers and derived states are not stored: they are
    calculated from these tags. '+' is the only supported tag sigil.

filters:
    '+tag' is an exact tag filter. '-+tag' excludes that exact tag.
    '@pattern' finds matching subtree roots and selects each root plus all of its
    descendants; +project tasks are preferred as roots, falling back to any matching
    task if no project matches. '-@pattern' excludes the resulting subtree.
    Other filters remain grep patterns and '-pattern' negates them. In 'l' and
    commands based on its selection they match the rendered task line; in 'll' they
    match only the task body. '+tag' and '@pattern' remain metadata/structure filters
    in 'll'. Filters are applied sequentially.

env vars:
    - TSK_DEBUG: show debug information [default: unset, cur: unset]
    - TSK_DIR: task directory [default: $HOME/.tsk, cur: $HOME/.tsk]
    - TSK_CATCMD: command used to render a task. Task content is piped to it
      (default: mdcat when available, otherwise cat) [cur: unset]
    - TSK_DONE_TAG: tag used for completed tasks [default: done, cur: done]
```

## References and related projects

- https://taskwarrior.org : an awesome task management tool for the cli
