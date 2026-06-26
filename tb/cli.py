import typer

from tb.commands import attributes, config_cmd, device, ota, telemetry

app = typer.Typer(no_args_is_help=True)
app.add_typer(config_cmd.app, name="config")
app.add_typer(ota.app, name="ota")
app.add_typer(telemetry.app, name="telemetry")
app.add_typer(attributes.app, name="attributes")
app.add_typer(device.app, name="device")


@app.callback()
def callback(
    ctx: typer.Context,
    profile: str = typer.Option("default", "-p", "--profile", help="Config profile."),
):
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile


def main() -> None:
    app()
