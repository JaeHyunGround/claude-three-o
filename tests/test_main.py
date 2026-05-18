"""Tests for CLI entrypoint (cli.py)."""

import sys
from unittest import mock

import pytest

from cli import COMMANDS, DESCRIPTION, main


@pytest.fixture(autouse=True)
def _restore_argv():
    original = sys.argv[:]
    yield
    sys.argv = original


class TestCommandRouting:
    def test_commands_dict_has_all_modules(self):
        assert "seo" in COMMANDS
        assert "geo" in COMMANDS
        assert "aao" in COMMANDS
        assert "score" in COMMANDS
        assert "dashboard" in COMMANDS
        assert "report-html" in COMMANDS

    def test_seo_has_subcommands(self):
        seo = COMMANDS["seo"]
        assert isinstance(seo, dict)
        assert "technical" in seo
        assert "content" in seo
        assert "keywords" in seo

    def test_geo_has_subcommands(self):
        geo = COMMANDS["geo"]
        assert isinstance(geo, dict)
        assert "mentions" in geo
        assert "citability" in geo
        assert "entity" in geo

    def test_aao_has_subcommands(self):
        aao = COMMANDS["aao"]
        assert isinstance(aao, dict)
        assert "selectability" in aao
        assert "conversion" in aao
        assert "feed" in aao

    def test_description_present(self):
        assert "Three-O" in DESCRIPTION
        assert "seo" in DESCRIPTION


class TestMainHelp:
    def test_no_args_prints_help(self):
        with pytest.raises(SystemExit) as exc:
            main(argv=[])
        assert exc.value.code == 0

    def test_help_flag(self):
        with pytest.raises(SystemExit) as exc:
            main(argv=["--help"])
        assert exc.value.code == 0

    def test_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["--version"])
        assert exc.value.code == 0
        assert "1.0.0" in capsys.readouterr().out


class TestUnknownCommand:
    def test_unknown_top_command(self):
        with pytest.raises(SystemExit) as exc:
            main(argv=["nonexistent"])
        assert exc.value.code == 1

    def test_unknown_subcommand(self):
        with pytest.raises(SystemExit) as exc:
            main(argv=["seo", "nonexistent"])
        assert exc.value.code == 1


class TestModuleDispatch:
    def test_dispatches_to_score_module(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["score", "three-o", "--seo", "80", "--geo", "70", "--aao", "60", "--json"])
            mock_import.assert_called_once_with("score_calculator")
            mock_module.main.assert_called_once()

    def test_dispatches_seo_subcommand(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["seo", "technical", "https://example.com", "--json"])
            mock_import.assert_called_once_with("seo_technical")
            mock_module.main.assert_called_once()

    def test_dispatches_geo_subcommand(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["geo", "mentions", "mybrand", "--json"])
            mock_import.assert_called_once_with("geo_mentions")
            mock_module.main.assert_called_once()

    def test_dispatches_report_html(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["report-html", "--input", "data.json"])
            mock_import.assert_called_once_with("report_html")
            mock_module.main.assert_called_once()

    def test_argv_rewritten_for_top_command(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["config", "check", "--json"])
            assert sys.argv == ["three-o config", "check", "--json"]

    def test_argv_rewritten_for_subcommand(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["aao", "feed", "https://shop.com", "--json"])
            assert sys.argv == ["three-o aao feed", "https://shop.com", "--json"]

    def test_module_without_main_exits(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock(spec=[])
            mock_import.return_value = mock_module
            with pytest.raises(SystemExit) as exc:
                main(argv=["config", "check"])
            assert exc.value.code == 1

    def test_seo_help_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["seo", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "technical" in out

    def test_seo_no_subcmd_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["seo"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "technical" in out
