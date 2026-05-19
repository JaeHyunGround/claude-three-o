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
        from config import VERSION
        assert VERSION in capsys.readouterr().out


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


class TestShortFlags:
    def test_short_help_flag(self):
        with pytest.raises(SystemExit) as exc:
            main(argv=["-h"])
        assert exc.value.code == 0

    def test_short_version_flag(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["-V"])
        assert exc.value.code == 0
        from config import VERSION
        assert VERSION in capsys.readouterr().out


class TestErrorMessages:
    def test_unknown_command_stderr(self, capsys):
        with pytest.raises(SystemExit):
            main(argv=["bogus"])
        err = capsys.readouterr().err
        assert "Unknown command: bogus" in err
        assert "Available:" in err

    def test_unknown_subcommand_stderr(self, capsys):
        with pytest.raises(SystemExit):
            main(argv=["geo", "bogus"])
        err = capsys.readouterr().err
        assert "Unknown geo sub-command: bogus" in err
        assert "Available:" in err

    def test_unknown_aao_subcommand(self, capsys):
        with pytest.raises(SystemExit):
            main(argv=["aao", "nonexistent"])
        err = capsys.readouterr().err
        assert "Unknown aao sub-command: nonexistent" in err


class TestPillarHelp:
    def test_geo_help_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["geo", "--help"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "mentions" in out
        assert "citability" in out

    def test_geo_no_subcmd_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["geo"])
        assert exc.value.code == 0
        assert "mentions" in capsys.readouterr().out

    def test_aao_help_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["aao", "-h"])
        assert exc.value.code == 0
        out = capsys.readouterr().out
        assert "selectability" in out
        assert "feed" in out

    def test_aao_no_subcmd_lists_subcommands(self, capsys):
        with pytest.raises(SystemExit) as exc:
            main(argv=["aao"])
        assert exc.value.code == 0
        assert "selectability" in capsys.readouterr().out


class TestAdditionalDispatch:
    def test_hyphenated_subcommand_llms_txt(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["geo", "llms-txt", "https://example.com"])
            mock_import.assert_called_once_with("geo_llms_txt")

    def test_dispatches_drift(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["drift", "mybrand", "--json"])
            mock_import.assert_called_once_with("three_o_drift")

    def test_dispatches_plan(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["plan", "restaurant"])
            mock_import.assert_called_once_with("three_o_plan")

    def test_dispatches_rewrite(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["rewrite", "--url", "https://example.com"])
            mock_import.assert_called_once_with("content_rewrite")

    def test_dispatches_recommend(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["recommend", "--input", "data.json"])
            mock_import.assert_called_once_with("recommendations")

    def test_dispatches_report_pdf(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["report-pdf", "--input", "data.json"])
            mock_import.assert_called_once_with("report_pdf")

    def test_dispatches_competitor(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["competitor", "https://a.com", "https://b.com"])
            mock_import.assert_called_once_with("three_o_competitor")

    def test_dispatches_aao_subcommand(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["aao", "scenario", "mybrand"])
            mock_import.assert_called_once_with("aao_scenario")
            assert sys.argv == ["three-o aao scenario", "mybrand"]

    def test_dispatches_seo_naver(self):
        with mock.patch("cli.importlib.import_module") as mock_import:
            mock_module = mock.MagicMock()
            mock_import.return_value = mock_module
            main(argv=["seo", "naver", "https://example.kr"])
            mock_import.assert_called_once_with("seo_naver")
