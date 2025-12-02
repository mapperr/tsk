# tsk

A cli task management tool when you don't need 
all the awesomeness of [taskwarrior](https://taskwarrior.org).

And you want to sync things with git.

## Installation

Clone the repo and drop or link `tsk` into your PATH.

## Usage

```

tsk ls [query] [exclude_tags_regex]
    lists tasks and grep them up, eventually ecluding some tags
tsk l [query]
    lists tasks and grep them up, excluding task with the 'done' tag
tsk show | s task_id
    shows a task
tsk add | a
    adds a new task
tsk edit | e task_id
    open EDITOR to edit a task, even if it not exists
tsk rm | r task_id
    removes a task
tsk mv | m task_id to_task_id
    moves a task to another id, shifting ids of other tasks
tsk compact | gc
    recompact task ids, removing holes
tsk sync | y
    syncs: commit changes and pull/push with git
tsk git | g [git_args]
    runs 'git git_args' in the task directory
tsk clean
    purge your tasks, use with caution

Options:

    TSK_DIR  - set this env var to change tsk storage directory
```

## Examples

List tasks with `tsk l`.

Add a task with `tsk a`.
It opens your editor.

Edit a task with `tsk e task_id`.
Again, it opens your editor.

Remove a task with `tsk r task_id`

Run `tsk` with no args for a help message.
