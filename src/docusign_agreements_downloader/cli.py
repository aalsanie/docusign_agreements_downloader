from __future__ import annotations

import json
from pathlib import Path
import sys
import typer

from .config import Settings
from .service import AgreementDownloadService

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command()
def download(
        from_date: str = typer.Option(..., help="ISO-8601 start (required). Example: 2026-01-01T00:00:00Z"),
        to_date: str | None = typer.Option(None, help="ISO-8601 end (optional). Example: 2026-01-31T23:59:59Z"),
        status: str = typer.Option("completed", help="Envelope status filter (e.g., completed, sent, voided)"),
        out: Path = typer.Option(Path("./out"), help="Output directory"),
        page_size: int = typer.Option(100, min=1, max=1000, help="Page size for listing envelopes"),
) -> None:
    """Download DocuSign agreements (envelopes) + documents to filesystem."""
    try:
        settings = Settings()
    except Exception as e:
        typer.echo(f"Configuration error: {e}", err=True)
        raise typer.Exit(code=2)

    svc = AgreementDownloadService(settings)
    result = svc.download(out_dir=out, from_date=from_date, to_date=to_date, status=status, page_size=page_size)

    summary = {
        "status": result.status,
        "out_dir": str(result.out_dir),
        "exported": len(result.exported),
        "failures": len(result.failures),
        "started_at": result.started_at.isoformat(),
        "finished_at": result.finished_at.isoformat(),
    }
    typer.echo(json.dumps(summary, indent=2))

    if result.failures:
        typer.echo("\nFailures:", err=True)
        for f in result.failures[:50]:
            typer.echo(f"- {f}", err=True)
        raise typer.Exit(code=1 if result.status != "ok" else 0)


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
