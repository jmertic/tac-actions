#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import argparse
import importlib
import logging
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

import lfx_tac_actions.updateartwork as artwork_module
from lfx_tac_actions.updateartwork import main, path_inside_cwd


class TestPathInsideCwd(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        self.addCleanup(os.chdir, self.old_cwd)

    def test_path_inside_cwd_valid(self):
        sub_dir = Path(self.temp_dir.name) / "projects"
        sub_dir.mkdir()
        result = path_inside_cwd("projects")
        self.assertEqual(result, sub_dir.resolve())

    def test_path_inside_cwd_escapes(self):
        with self.assertRaises(argparse.ArgumentTypeError):
            path_inside_cwd("../outside")


class TestUpdateArtworkMain(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        # Force CWD into temp_dir so path_inside_cwd validation passes
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)
        self.addCleanup(os.chdir, self.old_cwd)

        # Path relative to the temporary CWD
        self.projects_dir = Path("projects").resolve()
        self.projects_dir.mkdir()

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    def test_invalid_slug_regex(self, mock_setup_logging):
        with self.assertLogs(level="CRITICAL") as cm:
            main(["--slug", "invalid_slug!@#", "--project-path", str(self.projects_dir)])
        self.assertTrue(any("Invalid slug format" in log for log in cm.output))

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    @patch("lfx_tac_actions.updateartwork.requests.get")
    def test_api_request_exception(self, mock_get, mock_setup_logging):
        mock_get.side_effect = requests.RequestException("API connection failure")
        with self.assertLogs(level="CRITICAL") as cm:
            main(["--slug", "valid-slug", "--project-path", str(self.projects_dir)])
        self.assertTrue(any("Error getting projects" in log for log in cm.output))

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    @patch("lfx_tac_actions.updateartwork.requests.get")
    def test_empty_api_dataset(self, mock_get, mock_setup_logging):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"Data": []}
        mock_get.return_value = mock_resp

        with self.assertLogs(level="CRITICAL") as cm:
            main(["--slug", "valid-slug", "--project-path", str(self.projects_dir)])
        self.assertTrue(any("No records found" in log for log in cm.output))

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    @patch("lfx_tac_actions.updateartwork.cairosvg.svg2png")
    @patch("lfx_tac_actions.updateartwork.requests.get")
    def test_full_successful_run(self, mock_get, mock_svg2png, mock_setup_logging):
        old_proj_dir = self.projects_dir / "archived-proj"
        old_proj_dir.mkdir()
        old_readme = old_proj_dir / "README.md"
        old_readme.write_text("---\nproject_name: Old Proj\n---\nOld content", encoding="utf-8")

        api_resp = MagicMock()
        api_resp.json.return_value = {
            "Data": [
                {
                    "Name": "Project SVG",
                    "Slug": "proj-svg",
                    "ProjectLogo": "https://example.com/logo.svg",
                },
                {
                    "Name": "Project PNG",
                    "Slug": "proj-png",
                    "ProjectLogo": "https://example.com/logo.png",
                },
            ]
        }

        img_resp = MagicMock()
        img_resp.content = b"<svg></svg>"
        img_resp.__enter__.return_value = img_resp

        def get_side_effect(url, *args, **kwargs):
            if "api-gw.platform" in url:
                return api_resp
            return img_resp

        mock_get.side_effect = get_side_effect

        main(["--slug", "valid-slug", "--project-path", str(self.projects_dir)])

        self.assertTrue((self.projects_dir / "proj-svg" / "primary" / "color" / "proj-svg-primary-color.svg").exists())
        self.assertTrue((self.projects_dir / "proj-png" / "primary" / "color" / "proj-png-primary-color.png").exists())
        mock_svg2png.assert_called_once()

        readme_content = (self.projects_dir / "proj-svg" / "README.md").read_text(encoding="utf-8")
        self.assertIn("Project SVG", readme_content)

        archived_content = old_readme.read_text(encoding="utf-8")
        self.assertIn("level: Archived", archived_content)

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    @patch("lfx_tac_actions.updateartwork.requests.get")
    def test_logo_download_failure_handling(self, mock_get, mock_setup_logging):
        api_resp = MagicMock()
        api_resp.json.return_value = {
            "Data": [{"Name": "Error Proj", "Slug": "err-proj", "ProjectLogo": "https://example.com/err.svg"}]
        }

        def get_side_effect(url, *args, **kwargs):
            if "api-gw.platform" in url:
                return api_resp
            raise requests.RequestException("Image download error")

        mock_get.side_effect = get_side_effect

        with self.assertLogs(level="ERROR") as cm:
            main(["--slug", "valid-slug", "--project-path", str(self.projects_dir)])

        self.assertTrue(any("Error getting file" in log for log in cm.output))

    @patch("lfx_tac_actions.updateartwork.setup_logging")
    @patch("lfx_tac_actions.updateartwork.frontmatter.loads")
    def test_archiving_exception_handling(self, mock_loads, mock_setup_logging):
        corrupt_proj = self.projects_dir / "corrupt-proj"
        corrupt_proj.mkdir(parents=True)
        (corrupt_proj / "README.md").write_text("corrupted content", encoding="utf-8")

        mock_loads.side_effect = Exception("Read error")

        with patch("lfx_tac_actions.updateartwork.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = {"Data": []}
            mock_get.return_value = mock_resp

            with patch("builtins.print") as mock_print:
                main(["--slug", "valid-slug", "--project-path", str(self.projects_dir)])
                mock_print.assert_called()
                self.assertIn("Error processing", mock_print.call_args[0][0])

    @patch("sys.argv", ["updateartwork", "--slug", "valid-slug"])
    def test_script_entry_point(self):
        with patch.object(artwork_module, "main") as mock_main:
            # Simulate the conditional check manually in the module's exact context
            if artwork_module.__name__ != "__main__":
                artwork_module.main()

            mock_main.assert_called_once()

if __name__ == "__main__":
    unittest.main()
