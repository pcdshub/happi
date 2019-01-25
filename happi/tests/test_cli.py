# test_cli.py

import happi
from happi.cli import happi_cli


def test_cli_version(capsys):
    happi_cli(['--version'])
    readout = capsys.readouterr()
    assert happi.__version__ in readout.out
    assert happi.__file__ in readout.out
