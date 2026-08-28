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
Usage [v0.6.1]:
    tsk l [filters..]
        shows the task list, eventually filtered
        filters are grep patterns applied sequentially; prefix a pattern with '-'
        to exclude it. A filter in the form '#tag' matches an exact tag.

    tsk ll [filters..]
        searches only in task bodies, applying filters sequentially
        you can pipe in the result of another 'tsk l' to narrow the search

    tsk a <title and tags>
        adds a new task; the task body can be piped on stdin, e.g.:
        echo 'develop some web application' | tsk a 'Do something #dev #due:tomorrow'
        relative due dates are normalized only by the 'tsk due' command

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
    A tag is '#value' or '#key:value'. Components may contain letters, numbers,
    underscores '_' and dashes '-'. Some tags have conventional semantics:

        #done             completed task
        #due:YYYY-MM-DD           due date
        #parent:<task-id>         hierarchy (one parent per task)
        #depends:<task-id>        dependency
        #link:<task-id>           generic relation

    Backlinks, children, blockers and derived states are not stored: they are
    calculated from these tags.

env vars:
    - TSK_DEBUG: show debug information [default: unset, cur: unset]
    - TSK_DIR: task directory [default: $HOME/.tsk, cur: $HOME/.tsk]
    - TSK_CATCMD: command used to render a task. Task content is piped to it
      (default: mdcat when available, otherwise cat) [cur: unset]
    - TSK_DONE_TAG: tag used for completed tasks [default: done, cur: done]
```

## References and related projects

- https://taskwarrior.org : an awesome task management tool for the cli
