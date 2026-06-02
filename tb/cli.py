import typer

from tb.commands import config_cmd, ota

app = typer.Typer(no_args_is_help=True)
app.add_typer(config_cmd.app, name="config")
app.add_typer(ota.app, name="ota")


@app.callback()
def callback(
    ctx: typer.Context,
    profile: str = typer.Option("default", "-p", "--profile", help="Config profile."),
):
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile


def main() -> None:
    app()
