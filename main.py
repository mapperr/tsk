from typing import List, Optional
from typing_extensions import Annotated
import typer

app = typer.Typer()


@app.command()
def l(
    search_pattern: Annotated[
        Optional[str],
        typer.Argument(
            help="an include pattern as argument," " just for comfort"
        ),
    ] = None,
    search_patterns: Annotated[
        Optional[List[str]],
        typer.Option(
            "-i",
            help="include regex pattern,"
            " search for matches in all the tasks text,"
            " can be passed multiple times",
        ),
    ] = [],
    tags_exclude_patterns: Annotated[
        Optional[List[str]],
        typer.Option(
            "-x",
            help="exclude regex pattern,"
            " search for matches only in tasks tags,"
            " takes priority over the include patterns,"
            " can be passed multiple times",
        ),
    ] = [],
):
    """
    lists tasks and greps them up
    """

    if search_patterns is not None and search_pattern is not None:
        search_patterns.append(search_pattern)

    print(f"searching for patterns: {search_patterns}")
    print(f"excluding tags patterns: {tags_exclude_patterns}")


@app.command()
def p(
    task_id: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    prints a task
    """
    print(f"showing task: {task_id}")


@app.command()
def c():
    """
    creates a new task
    """
    print(f"creating new task")


@app.command()
def e(
    task_id: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    edit a task
    """
    print(f"editing task: {task_id}")


@app.command()
def r(
    task_id: Annotated[Optional[str], typer.Argument()] = None,
):
    """
    removes a task
    """
    print(f"removing task: {task_id}")


@app.command()
def y():
    """
    sync git repo
    """
    print(f"syncing git repo")


if __name__ == "__main__":
    app()
