"""
NSG Tactical CLI — Phase 30, Task 30.1

Lightweight administration and monitoring tool for field operators.
Allows for quick status checks, feed management, and alert retrieval via terminal.
"""

import sys
import click
import requests
import json
from typing import Optional

BASE_URL = "http://localhost:8000/api/v1"

class TacticalClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}

    def get_status(self):
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            return resp.json()
        except Exception as e:
            return {"status": "OFFLINE", "error": str(e)}

    def list_feeds(self):
        try:
            resp = requests.get(f"{BASE_URL}/feeds", headers=self.headers, timeout=5)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

@click.group()
def cli():
    """NSG VisionAI Tactical Administration Tool"""
    pass

@cli.command()
def status():
    """Check local node health and active missions."""
    client = TacticalClient()
    status = client.get_status()
    
    click.secho("\n--- 🛡️ NSG VISIONAI NODE STATUS ---", fg="cyan", bold=True)
    if status.get("status") == "healthy":
        click.echo(f"STATUS: ", nl=False)
        click.secho("ONLINE", fg="green", bold=True)
        click.echo(f"VERSION: {status.get('version', 'N/A')}")
        click.echo(f"APP: {status.get('app_name', 'N/A')}")
    else:
        click.echo(f"STATUS: ", nl=False)
        click.secho("OFFLINE / DEGRADED", fg="red", bold=True)
    click.echo("--------------------------------\n")

@cli.command()
@click.option("--token", help="Admin JWT token")
def feeds(token):
    """List all registered video assets."""
    client = TacticalClient(token)
    data = client.list_feeds()
    
    if "error" in data:
        click.secho(f"Error: {data['error']}", fg="red")
        return

    click.secho("\n--- ACTIVE VIDEO ASSETS ---", fg="cyan", bold=True)
    feeds_list = data.get("feeds", [])
    for f in feeds_list:
        status_color = "green" if f['status'] == "ACTIVE" else "yellow"
        click.echo(f"[{f['id'][:8]}] ", nl=False)
        click.secho(f"{f['name']:<20}", fg="white", bold=True, nl=False)
        click.echo(f" TYPE: {f['feed_type']:<15} STATUS: ", nl=False)
        click.secho(f"{f['status']}", fg=status_color)
    
    if not feeds_list:
        click.echo("No feeds registered.")
    click.echo("")

if __name__ == "__main__":
    cli()
