# tsk

A cli task management tool when you don't need 
all the awesomeness of [taskwarrior](https://taskwarrior.org).

And you want to sync things with git.

## Installation

Clone the repo and drop or link `tsk` into your PATH.

## Basic usage

List tasks with `tsk l`.

Add a task with `tsk a`.
It opens your editor.

Edit a task with `tsk e task_id`.
Again, it opens your editor.

Remove a task with `tsk r task_id`

Run `tsk` with no args for a help message.

## Sync

With `tsk g git_args` you can run git commands into the task dir.

Soo, run `tsk g init` and you have a git repo.

If you add a remote you can sync it with `tsk y`. 
It commits all your eventual pending changes and do a pull/push.

The default task dir is `$HOME/.tsk`.

