from docusign_agreements_downloader.util import guess_extension


def test_guess_extension():
    assert guess_extension("application/pdf") == "pdf"
    assert guess_extension("application/pdf; charset=binary") == "pdf"
    assert guess_extension(None) == "bin"
    assert guess_extension("application/unknown") == "bin"
