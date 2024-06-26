import os
import shutil
from pathlib import Path

import typer

os.environ["PYTHONIOENCODING"] = "utf-8"

app = typer.Typer()

HERE = Path(__file__).parent


@app.command()
def release(tag: str):
    print(f"WARNING: This operation will create version {tag=} and push to github")
    typer.confirm("Do you want to continue?", abort=True)
    Path("piecash2/VERSION").write_text(tag)
    os.system("gitchangelog > HISTORY.md")
    os.startfile("HISTORY.md")
    typer.confirm("Did you update the changelog?", abort=True)
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


@app.command()
def fmt():
    """fmt:              ## Format code using black & isort."""
    os.system("isort piecash2/")
    os.system("black -l 140 piecash2/")
    os.system("black -l 140 tests/")


@app.command()
def docs():
    """fmt:              ## Format code using black & isort."""
    os.system("mkdocs build")
    os.startfile(Path(__file__).parent / "site" / "index.html")


@app.command()
def clean():
    """clean:            ## Clean up unused files."""
    patterns = [
        "**/*.pyc",
        "**/__pycache__",
        "**/Thumbs.db",
        "**/*~",
        ".cache",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "build",
        "dist",
        "*.egg-info",
        "htmlcov",
        "docs/_build",
    ]

    for fp in patterns:
        for f in HERE.glob(fp):
            if f.is_file():
                f.unlink()
            else:
                shutil.rmtree(f)


@app.command()
def test():
    """test:             ## Run tests and generate coverage report."""
    os.system("pytest -v --cov-config .coveragerc --cov=piecash2 -l --tb=short --maxfail=1 tests/")
    os.system("coverage xml")
    os.system("coverage html")
    os.startfile(HERE / "htmlcov" / "index.html")


@app.command()
def schema():
    """schema:           ## Generate the schema from the sqlite database using sqlacodegen."""
    import piecash2.schema.generation.schema_generation as schema_generation
    import piecash2.schema.generated as generated

    schema_generation.path_schemas = Path(generated.__file__).parent

    print(f"Generating schemas in {schema_generation.path_schemas}")
    for book in (HERE / "data").glob("*.gnucash"):
        schema_generation.generate_schema(book, schema_generation.get_schema_name(book))


if __name__ == "__main__":
    app()
