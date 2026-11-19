"""Modular tunnel management for remote MCP access (Ngrok, Tailscale).

Supports free and paid tiers:
- ngrok: Free tier uses free static domain or dynamic tunnels
- tailscale: Free Funnel (*.ts.net) per ADR 0003, needs to be enabled

Pods handles OAuth 2.1 internally; tunnels serve purely as transparent HTTPS pipes.
"""

import json
import shutil
import subprocess
import time
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path

import click
import logging

NGROK_API = "http://localhost:4040/api/tunnels"
NGROK_CONFIG = Path.home() / ".config" / "ngrok" / "ngrok.yml"


class TunnelProvider(ABC):
    """Abstract base class for tunnel providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the tunnel provider."""

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if the tunnel binary is installed."""

    @abstractmethod
    def get_url(self) -> str | None:
        """Retrieve the active public HTTPS URL, or None if not running."""

    @abstractmethod
    def start(self, port: int = 8000) -> str | None:
        """Start the tunnel pointing to local port, returning the public URL."""

    def _clear_state(self) -> None:
        """Remove the persisted tunnel_state.json file if it exists.
        This ensures `pod tunnel status` reflects the real runtime state
        after a stop operation.
        """
        from pathlib import Path
        import logging
        state_path = Path.home() / ".config" / "pods" / "tunnel_state.json"
        try:
            if state_path.is_file():
                state_path.unlink()
        except Exception as exc:
            logging.debug(f"Failed to clear tunnel state file: {exc}")


class NgrokTunnel(TunnelProvider):
    """Ngrok tunnel provider (free or paid, without external OAuth)."""

    DEFAULT_DOMAIN = "glacier-mantra-siren.ngrok-free.dev"

    @property
    def name(self) -> str:
        return "ngrok"

    @property
    def binary(self) -> str:
        found = shutil.which("ngrok")
        if found:
            return found
        local_path = Path.home() / ".local/bin/ngrok"
        if local_path.exists():
            return str(local_path)
        return "ngrok"

    def is_installed(self) -> bool:
        if self.get_url() is not None:
            return True
        return shutil.which("ngrok") is not None or (Path.home() / ".local/bin/ngrok").exists()

    def get_token(self) -> str | None:
        if not NGROK_CONFIG.exists():
            return None
        content = NGROK_CONFIG.read_text(encoding="utf-8")
        if "authtoken:" not in content:
            return None
        token = content.split("authtoken:")[1].strip().split("\n")[0].strip()
        return token if len(token) > 10 else None

    def get_url(self) -> str | None:
        try:
            req = urllib.request.Request(NGROK_API)
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for t in data.get("tunnels", []):
                    return t.get("public_url")
        except (urllib.error.URLError, json.JSONDecodeError, KeyError, TimeoutError):
            return None
        return None

    def setup(self) -> None:
        """Authenticate ngrok via official CLI."""
        token = click.prompt("Enter ngrok auth token (from dashboard.ngrok.com)")
        if token:
            res = subprocess.run(
                [self.binary, "config", "add-authtoken", token.strip()], check=False
            )
            if res.returncode == 0:
                click.secho(
                    "Auth token configured via 'ngrok config add-authtoken'.",
                    fg="green",
                )
            else:
                click.secho("Failed to configure auth token with ngrok CLI.", fg="red")

    def start(self, port: int = 8000) -> str | None:
        if not self.is_installed():
            click.secho(
                "ngrok is not installed. Install: https://ngrok.com/download", fg="red"
            )
            return None

        current = self.get_url()
        if current:
            click.secho(f"ngrok tunnel already running: {current}", fg="yellow")
            return current

        cmd = [self.binary, "http", f"--url={self.DEFAULT_DOMAIN}", str(port)]

        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        # Wait for ngrok API to become responsive
        for _ in range(10):
            time.sleep(0.5)
            url = self.get_url()
            if url:
                return url
        return None

    def stop(self) -> None:
        subprocess.run(
            "pkill -9 -f ngrok",
            shell=True,
            capture_output=True,
            check=False,
        )


class TailscaleTunnel(TunnelProvider):
    """Tailscale Funnel provider (free, permanent *.ts.net domain, ADR 0003)."""

    @property
    def name(self) -> str:
        return "tailscale"

    @property
    def binary(self) -> str:
        found = shutil.which("tailscale")
        if found:
            return found
        for p in [
            "/usr/bin/tailscale",
            "/usr/local/bin/tailscale",
            str(Path.home() / ".local/bin/tailscale"),
        ]:
            if Path(p).exists():
                return p
        return "tailscale"

    def is_installed(self) -> bool:
        if self.get_url() is not None:
            return True
        return shutil.which("tailscale") is not None or Path(self.binary).exists()

    def is_logged_in(self) -> bool:
        """Check if tailscaled is running and authenticated."""
        if not self.is_installed():
            return False
        res = subprocess.run(
            [self.binary, "status", "--json"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return False
        try:
            data = json.loads(res.stdout)
            return data.get("BackendState") == "Running"
        except (json.JSONDecodeError, KeyError):
            return False

    def get_url(self) -> str | None:
        try:
            # Check if serve / funnel is actively serving endpoints
            serve_res = subprocess.run(
                [self.binary, "serve", "status", "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            if serve_res.returncode == 0 and serve_res.stdout.strip():
                serve_data = json.loads(serve_res.stdout)
                if not serve_data or not (
                    serve_data.get("Web") or serve_data.get("TCP")
                ):
                    return None

                status_res = subprocess.run(
                    [self.binary, "status", "--json"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if status_res.returncode == 0:
                    data = json.loads(status_res.stdout)
                    dns = data.get("Self", {}).get("DNSName", "").rstrip(".")
                    if dns:
                        return f"https://{dns}"
        except (json.JSONDecodeError, KeyError, subprocess.SubprocessError):
            return None
        return None

    def start(self, port: int = 8000) -> str | None:
        if not self.is_installed():
            click.secho(
                "tailscale is not installed. Install at: https://tailscale.com/docs/install",
                fg="red",
            )
            return None

        if not self.is_logged_in():
            click.secho(
                "Tailscale is not logged in or running. Run 'tailscale up' first.",
                fg="red",
            )
            return None

        # Stream output directly so Tailscale authorization prompts and links are visible
        subprocess.run(
            [self.binary, "funnel", "--bg", "--yes", str(port)],
            check=False,
        )
        return self.get_url()

    def setup(self) -> None:
        """Verify Tailscale login and Funnel configuration."""
        if not self.is_installed():
            click.secho(
                "Tailscale is not installed. Install at: https://tailscale.com/docs/install",
                fg="red",
            )
            return
        if not self.is_logged_in():
            click.secho(
                "Tailscale is not logged in. Run: sudo tailscale up", fg="yellow"
            )
            return
        click.secho("Tailscale is installed and logged in.", fg="green")
        subprocess.run(
            [self.binary, "funnel", "--bg", "--yes", "8000"],
            check=False,
        )
        url = self.get_url()
        if url:
            click.secho(f"Tailscale Funnel ready: {url}", fg="green")

    def stop(self) -> None:
        # 'tailscale serve --terminate' doesn't exist (invalid flag, silently
        # swallowed before) — 'serve reset' clears the persisted serve/funnel
        # config that tailscaled re-applies on every boot.
        res = subprocess.run(
            [self.binary, "serve", "reset"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            click.secho(
                f"Failed to reset tailscale serve config: {res.stderr.strip()}",
                fg="red",
            )


# Registry of available providers
PROVIDERS: dict[str, TunnelProvider] = {
    "ngrok": NgrokTunnel(),
    "tailscale": TailscaleTunnel(),
}


def get_tunnel_url() -> str | None:
    """Return the active tunnel URL across any provider (ngrok, tailscale)."""
    for provider in PROVIDERS.values():
        url = provider.get_url()
        if url:
            return url
    return None


def ngrok_installed() -> bool:
    return PROVIDERS["ngrok"].is_installed()


def has_oauth() -> bool:
    """Return False: tunnel-level OAuth is disabled; pods handles OAuth 2.1 directly."""
    return False


def register(cli):
    """Register tunnel commands with the CLI."""

    @cli.group(invoke_without_command=True)
    @click.pass_context
    def tunnel(ctx):
        """Manage tunnels for remote access (ngrok, tailscale)."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @tunnel.command(
        help="Setup provider config: 'pod tunnel setup [ngrok|tailscale]' (default: ngrok)."
    )
    @click.argument(
        "provider",
        type=click.Choice(["ngrok", "tailscale"]),
        required=False,
        default="ngrok",
    )
    def setup(provider: str) -> None:
        selected = PROVIDERS.get(provider)
        if hasattr(selected, "setup"):
            selected.setup()

    @tunnel.command(
        help="Start tunnel: 'pod tunnel start [ngrok|tailscale]' (default: ngrok)."
    )
    @click.argument(
        "provider",
        type=click.Choice(["ngrok", "tailscale"]),
        required=False,
        default="ngrok",
    )
    @click.option(
        "--port",
        type=int,
        default=8000,
        help="Local server port to expose (default: 8000).",
    )
    def start(provider: str, port: int) -> None:
        selected = PROVIDERS.get(provider)
        if not selected:
            click.secho(f"Unknown provider: {provider}", fg="red")
            return

        click.echo(f"Starting {provider} tunnel on port {port}...")
        url = selected.start(port=port)
        if url:
            click.secho(f"\nTunnel started: {url}", fg="green")
            click.echo(f"Connector URL: {url}/mcp\n")
        else:
            click.secho(
                "Failed to start tunnel. Check logs or run './pod tunnel status'.",
                fg="red",
            )

    @tunnel.command(
        help="Stop tunnel: 'pod tunnel stop [ngrok|tailscale|all]' (default: all)."
    )
    @click.argument(
        "provider",
        type=click.Choice(["ngrok", "tailscale", "all"]),
        required=False,
        default="all",
    )
    def stop(provider: str) -> None:
        """Stop running tunnel(s)."""
        targets = PROVIDERS.values() if provider == "all" else [PROVIDERS.get(provider)]
        stopped, failed = [], []
        for p in targets:
            if not p:
                continue
            p.stop()
            # Verify: get_url() reflects real runtime state, not a claim
            (failed if p.get_url() else stopped).append(p.name)
        if stopped:
            click.echo(f"Stopped: {', '.join(stopped)}.")
        if failed:
            click.secho(
                f"Still running: {', '.join(failed)}. Check provider logs.",
                fg="red",
            )

    @tunnel.command(name="list")
    def list_cmd() -> None:
        """List all supported tunnel providers and their current status."""
        click.echo("Tunnel Providers:")
        for name, p in PROVIDERS.items():
            url = p.get_url()
            installed = p.is_installed() or (url is not None)
            if installed:
                if isinstance(p, TailscaleTunnel):
                    status_detail = (
                        "installed (logged in)"
                        if p.is_logged_in()
                        else "installed (needs login)"
                    )
                elif isinstance(p, NgrokTunnel):
                    status_detail = (
                        "installed (configured)"
                        if p.get_token()
                        else "installed (no token)"
                    )
                else:
                    status_detail = "installed"
                inst_str = click.style(status_detail, fg="green")
            else:
                inst_str = click.style("not installed", fg="bright_black")
            if url:
                state_str = click.style(f"running ({url})", fg="green")
            else:
                state_str = click.style("stopped", fg="yellow")
            click.echo(f"  {name:<12} [{inst_str}] : {state_str}")

    @tunnel.command()
    def status() -> None:
        """Show status of active tunnels across all providers."""
        found = False
        for name, p in PROVIDERS.items():
            url = p.get_url()
            if url:
                click.secho(f"Tunnel [{name}]: {url}", fg="green")
                click.echo(f"Connector URL:  {url}/mcp")
                click.echo("OAuth:          Managed by pods (OAuth 2.1)\n")
                found = True

        if not found:
            click.secho("No tunnel running.", fg="red")

    def _attach_provider_group(name: str, prov: TunnelProvider) -> None:
        @tunnel.group(
            name=name,
            invoke_without_command=True,
            help=f"Manage {name} tunnel (start, stop, status, setup).",
        )
        @click.pass_context
        def prov_group(ctx):
            if ctx.invoked_subcommand is None:
                url = prov.get_url()
                if url:
                    click.secho(f"{name} tunnel is running: {url}", fg="green")
                    click.echo(f"Connector URL: {url}/mcp")
                else:
                    installed = prov.is_installed()
                    inst_str = (
                        click.style("installed", fg="green")
                        if installed
                        else click.style("not installed", fg="red")
                    )
                    click.echo(f"{name} [{inst_str}] is stopped.")
                    click.echo(f"Run 'pod tunnel {name} start' to start.\n")
                    click.echo(ctx.get_help())

        @prov_group.command(name="start", help=f"Start {name} tunnel.")
        @click.option(
            "--port",
            type=int,
            default=8000,
            help="Local server port to expose (default: 8000).",
        )
        def p_start(port: int) -> None:
            click.echo(f"Starting {name} tunnel on port {port}...")
            url = prov.start(port=port)
            if url:
                click.secho(f"\nTunnel started: {url}", fg="green")
                click.echo(f"Connector URL: {url}/mcp\n")
            else:
                click.secho(f"Failed to start {name} tunnel.", fg="red")

        @prov_group.command(name="stop", help=f"Stop {name} tunnel.")
        def p_stop() -> None:
            prov.stop()
            click.echo(f"{name} tunnel stopped.")

        @prov_group.command(name="status", help=f"Show {name} tunnel status.")
        def p_status() -> None:
            url = prov.get_url()
            if url:
                click.secho(f"Tunnel [{name}]: {url}", fg="green")
                click.echo(f"Connector URL:  {url}/mcp\n")
            else:
                click.secho(f"{name} tunnel is not running.", fg="yellow")

        @prov_group.command(name="setup", help=f"Setup {name} configuration.")
        def p_setup() -> None:
            if hasattr(prov, "setup"):
                prov.setup()

    _attach_provider_group("ngrok", PROVIDERS["ngrok"])
    _attach_provider_group("tailscale", PROVIDERS["tailscale"])
