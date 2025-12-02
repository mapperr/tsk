# tsk

A cli task management tool when you don't need 
all the awesomeness of [taskwarrior](https://taskwarrior.org).

And you want to sync things with git.

## Installation

Clone the repo and drop or link `tsk` into your PATH.

## Usage

```
Usage [v0.1.0]:
    tsk l [filters]
        shows the task list, eventually filtered
        you can pipe in the result of another tsk l to narrow the search
    tsk ll [filters]
        shows the task list, eventually filtered searching in tasks body
        you can pipe in the result of another tsk l to narrow the search

    tsk a <title and tags>
        adds a new task, you can pipe in the task body, e.g.:
        echo 'develop some web application' | tsk a Do something #dev #due:tomorrow

    tsk d [filters]
        deletes tasks
        you can pipe in a list of task filtered from tsk l: this way there is NO CONFIRMATION!

    tsk e [filters]
        opens a task in the $EDITOR
        if no filter is passed, then opens the last created task
        you can pipe in one task filtered from tsk l

    tsk s [filters]
        shows the tasks to stdout
        you can pipe in a list of task filtered from tsk l

    tsk g [git cmds/args]
        executes git commands in the tsk directory, e.g.: tsk g pull
    tsk y [commit msg]
        executes git add, commit -m 'commit msg' (or 'sync'), pull and push in the tsk directory
    tsk h
        shows extended help

tsk files:
    a tsk file contains the task title and task tags in the first line,
    and the task body from the second line on.
    A tsk file is named with the timestamp the task was created and the task id.

tags:
    tasks can be tagged. A 'tag' is a string in the form of #tag or #tag:value
    where tag and value can contain only letters, numbers, undescores '_' and dashes '-', without blank spaces.
    those tags will help search and task categorization or can be used by external integrations.

env vars:
    - TSK_DEBUG: set it to whatever value to show debug informations [default: unset, cur: unset]
    - TSK_DIR: the directory containing your tasks [default: $HOME/.tsk, cur: /home/mapperr/src/git.sr.ht/~mapperr/tasks]
    - TSK_DONE_TAG: the tasks tagged with the TSK_DONE tag are excluded from lists, unless you explicitly include them [default: #done , cur: done]
```

## Examples

List tasks with `tsk l`.

Add a task with `tsk a`.
It opens your editor.

Edit a task with `tsk e task_id`.
Again, it opens your editor.

Remove a task with `tsk r task_id`

Run `tsk` with no args for a help message.
