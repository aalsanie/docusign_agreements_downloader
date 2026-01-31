from pathlib import Path

from docusign_agreements_downloader.exporter import safe_filename, FilesystemExporter
from docusign_agreements_downloader.models import Agreement, EnvelopeSummary


def test_safe_filename_basic():
    assert safe_filename("Hello World.pdf") == "Hello_World.pdf"
    assert safe_filename("  .. ") == "document"
    assert safe_filename("a" * 500).startswith("a" * 120)


def test_exporter_writes_agreement_json(tmp_path: Path):
    exporter = FilesystemExporter(tmp_path)
    agreement_dir, docs_dir, agreement_json = exporter.prepare_agreement_dirs("env1")
    assert agreement_dir.exists()
    assert docs_dir.exists()

    agreement = Agreement(envelope=EnvelopeSummary(envelope_id="env1", status="completed"), documents=[])
    exporter.write_agreement_json(agreement, agreement_json)
    assert agreement_json.exists()
    assert "env1" in agreement_json.read_text(encoding="utf-8")
