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
Usage [v0.3.0]:
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

    tsk t <tags changes>...
        changes tags to the list of tasks piped in
        it works on the task list you pipe in from tsk l
        the tag change syntax is '-tag' to remove a tag and '+tag' to add it

    tsk g [git cmds/args]
        executes git commands in the tsk directory, e.g.: tsk g pull
    tsk y [commit msg]
        executes git add, commit -m 'commit msg' (or 'sync'), pull and push in the tsk directory
    tsk h
        shows extended help

tsk files:
    a tsk file contains the task title and task tags in the first line, with tags following the title,
    and the task body from the second line on.
    A tsk file is named with the timestamp the task was created and the task id.

tags:
    tasks can be tagged. A 'tag' is a string in the form of #value or #key:value
    where key and value can contain only letters, numbers, undescores '_' and dashes '-', without blank spaces.
    those tags will help searching, task categorization, reports or can be used by external integrations.

env vars:
    - TSK_DEBUG: set it to whatever value to show debug informations [default: unset, cur: unset]
    - TSK_DIR: the directory containing your tasks [default: $HOME/.tsk, cur: $HOME/.tsk]
    - TSK_CATCMD: command to print tasks to stdout. tasks content is pipe-in the command
      (if unset, mdcat is used, falling back to cat) [default: unset, cur: ]
```

## References and related projects

- https://taskwarrior.org : an awesome task management tool for the cli
