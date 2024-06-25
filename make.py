import os
from pathlib import Path

import typer

app = typer.Typer()


@app.command()
def release(tag: str):
    print(f"WARNING: This operation will create version {tag=} and push to github")
    typer.confirm("Do you want to continue?", abort=True)
    Path("piecash2/VERSION").write_text(tag)
    os.system("gitchangelog > HISTORY.md")
    os.system("git add piecash2/VERSION HISTORY.md")
    os.system(f'git commit -m "release: version {tag}')
    print(f"creating git tag : {tag}")
    os.system(f"git tag {tag}")
    os.system("git push -u origin HEAD --tags")
    print("Github Actions will detect the new tag and release the new version.")


@app.command()
def lint():
    """lint:             ## Run pep8, black, mypy linters."""
    os.system("flake8 piecash2/")
    os.system("black -l 140 --check piecash2/")
    os.system("black -l 140 --check tests/")
    os.system("mypy --ignore-missing-imports piecash2/")


if __name__ == "__main__":
    app()
