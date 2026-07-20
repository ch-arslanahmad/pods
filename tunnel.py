import json
import subprocess
import time
import urllib.request
from pathlib import Path

import click

NGROK_API = "http://localhost:4040/api/tunnels"
NGROK_CONFIG = Path.home() / ".config" / "ngrok" / "ngrok.yml"



def get_ngrok_token() -> str | None:
    """Return ngrok authtoken string or None."""
    if not NGROK_CONFIG.exists():
        return None
    content = NGROK_CONFIG.read_text()
    if "authtoken:" not in content:
        return None
    token = content.split("authtoken:")[1].strip().split("\n")[0].strip()
    return token if len(token) > 10 else None


def get_tunnel_url() -> str | None:
    """Get public URL from ngrok API if running."""
    try:
        resp = urllib.request.urlopen(NGROK_API, timeout=2)
        tunnels = json.loads(resp.read())
        for tunnel in tunnels.get("tunnels", []):
            return tunnel["public_url"]
    except Exception:
        pass
    return None


def ngrok_installed() -> bool:
    return subprocess.run("which ngrok", shell=True, capture_output=True).returncode == 0


def has_oauth() -> bool:
    """Check if ngrok config has OAuth in traffic policy."""
    if not NGROK_CONFIG.exists():
        return False
    content = NGROK_CONFIG.read_text()
    return "type: oauth" in content


def register(cli):
    """Register tunnel commands with the CLI."""

    @cli.group()
    def tunnel():
        """Manage tunnel for remote access."""
        pass

    @tunnel.command()
    def setup():
        """Setup ngrok tunnel with Google OAuth (one-time)."""
        if not ngrok_installed():
            click.secho("ngrok not installed. Install: https://ngrok.com/download", fg="red")
            return

        # authtoken
        token = get_ngrok_token()
        if not token:
            t = click.prompt("Enter ngrok auth token (from https://dashboard.ngrok.com/get-started/your-authtoken)")
            if t:
                subprocess.run(f"ngrok config add-authtoken {t}", shell=True, check=True)
                click.secho("Auth token saved.", fg="green")
            else:
                return
        else:
            click.secho("Auth token already configured.", fg="green")

        # email for OAuth
        email = click.prompt("Enter your Google email for OAuth allow-list")

        # domain
        domain = click.prompt("Enter your ngrok domain", default="glacier-mantra-siren.ngrok-free.dev")

        # write v3 config with traffic policy
        config = f'''version: "3"
agent:
    authtoken: {get_ngrok_token()}
endpoints:
  - name: pods
    url: https://{domain}
    upstream:
      url: 8000
    traffic_policy:
      on_http_request:
        - actions:
            - type: oauth
              config:
                provider: google
        - expressions:
            - "!(actions.ngrok.oauth.identity.email == '{email}')"
          actions:
            - type: deny
'''
        NGROK_CONFIG.write_text(config)
        click.secho(f"Config written to {NGROK_CONFIG}", fg="green")
        click.secho("\nSetup complete! Run 'pod tunnel start' to start.", fg="green")

    @tunnel.command()
    def start():
        """Start ngrok tunnel."""
        if not ngrok_installed():
            click.secho("ngrok not installed. Install: https://ngrok.com/download", fg="red")
            return

        if not get_ngrok_token():
            click.secho("Not configured. Run: pod tunnel setup", fg="red")
            return

        url = get_tunnel_url()
        if url:
            click.secho(f"Tunnel already running: {url}", fg="yellow")
            return

        subprocess.Popen(
            ["ngrok", "start", "pods"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        time.sleep(4)
        url = get_tunnel_url()
        if url:
            click.secho(f"Tunnel started: {url}", fg="green")
            if has_oauth():
                click.echo("OAuth enabled (Google login required)")
        else:
            click.secho("Tunnel started but couldn't get URL. Check: curl http://localhost:4040", fg="yellow")

    @tunnel.command()
    def stop():
        """Stop ngrok tunnel."""
        subprocess.run("pkill -9 -f ngrok", shell=True, capture_output=True)
        click.echo("Tunnel stopped.")

    @tunnel.command()
    def status():
        """Show tunnel status."""
        url = get_tunnel_url()
        if url:
            click.secho(f"Tunnel running: {url}", fg="green")
            if has_oauth():
                click.echo("OAuth enabled (Google login required)")
        else:
            click.secho("No tunnel running.", fg="red")
