#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import argparse
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import io
from contextlib import redirect_stderr
import frontmatter

# Adjust this import to match your script/module name
from lfx_tac_actions.updateartwork import main, path_inside_cwd


class TestPathInsideCwd(unittest.TestCase):
    """Tests for path_inside_cwd helper function."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

    def tearDown(self):
        os.chdir(self.old_cwd)
        self.temp_dir.cleanup()

    def test_path_inside_cwd_valid(self):
        """Test that valid paths inside CWD are accepted and resolved."""
        valid_subfolder = "projects/subfolder"
        result = path_inside_cwd(valid_subfolder)

        expected = (Path(self.temp_dir.name) / valid_subfolder).resolve()
        self.assertEqual(result, expected)

    def test_path_inside_cwd_escapes_error(self):
        """Test that paths traversing outside CWD raise ArgumentTypeError."""
        escaping_path = "../outside_folder"
        with self.assertRaises(argparse.ArgumentTypeError) as ctx:
            path_inside_cwd(escaping_path)

        self.assertIn("escapes current working directory", str(ctx.exception))

class TestMainUpdateArtwork(unittest.TestCase):
    """Tests for the main workflow script."""

    def setUp(self):
        # Redirect stderr to an in-memory buffer for all tests in this class
        self.stderr_buffer = io.StringIO()
        self.stderr_redirect = redirect_stderr(self.stderr_buffer)
        self.stderr_redirect.__enter__()

        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_cwd = os.getcwd()
        os.chdir(self.temp_dir.name)

        # Patch argparse's internal stderr reference to silence usage output
        self.stderr_patcher = patch("argparse._sys.stderr", new_callable=io.StringIO)
        self.mock_stderr = self.stderr_patcher.start()

        # Patch setup_logging and setup_argparse
        self.log_patcher = patch("lfx_tac_actions.updateartwork.setup_logging")
        self.arg_patcher = patch("lfx_tac_actions.updateartwork.setup_argparse")

        self.mock_log = self.log_patcher.start()
        self.mock_arg = self.arg_patcher.start()

        def create_test_parser(description=""):
            p = argparse.ArgumentParser(description=description)
            p.add_argument("-l", "--log-level", default="INFO", help="Logging level")
            return p

        self.mock_arg.side_effect = create_test_parser

    def tearDown(self):
        self.stderr_patcher.stop()
        self.log_patcher.stop()
        self.arg_patcher.stop()
        os.chdir(self.old_cwd)
        self.temp_dir.cleanup()
        self.stderr_redirect.__exit__(None, None, None)

    @patch("requests.get")
    def test_main_invalid_slug(self, mock_get):
        """Ensure main rejects malicious or invalid slugs without making API calls."""
        with self.assertLogs(level="CRITICAL") as log:
            main(["-s", "invalid_slug!injection"])

            mock_get.assert_not_called()
            self.assertTrue(any("Invalid slug format" in message for message in log.output))

    @patch("requests.get")
    def test_main_api_failure(self, mock_get):
        """Ensure main handles API HTTP/connection failures gracefully."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("API Server Error")
        mock_response.url = "https://api-gw.platform.linuxfoundation.org/..."
        mock_get.return_value = mock_response

        with self.assertLogs(level="CRITICAL") as log:
            main(["-s", "valid-slug"])
            self.assertTrue(any("Error getting projects at" in message for message in log.output))

    @patch("cairosvg.svg2png")
    @patch("requests.get")
    def test_main_successful_svg_download(self, mock_get, mock_cairo):
        """Test full workflow: SVG download, CairoSVG conversion, and README frontmatter creation."""
        # Resolve project_dir so symlinks (/var vs /private/var on macOS) are normalized
        project_dir = (Path(self.temp_dir.name) / "projects").resolve()

        api_payload = {
            "Data": [
                {
                    "Name": "Adlik Project",
                    "Slug": "Adlik",
                    "ProjectLogo": "https://example.com/artwork/adlik.svg"
                }
            ]
        }

        mock_api_resp = MagicMock()
        mock_api_resp.json.return_value = api_payload
        mock_api_resp.raise_for_status.return_value = None

        mock_logo_resp = MagicMock()
        mock_logo_resp.content = b"<svg>test artwork</svg>"
        mock_logo_resp.raise_for_status.return_value = None
        mock_logo_resp.__enter__.return_value = mock_logo_resp

        mock_get.side_effect = [mock_api_resp, mock_logo_resp]

        main(["-s", "lf-ai-foundation", "-p", str(project_dir)])

        # 1. Verify SVG file creation
        svg_file = project_dir / "adlik" / "primary" / "color" / "adlik-primary-color.svg"
        self.assertTrue(svg_file.exists())
        self.assertEqual(svg_file.read_bytes(), b"<svg>test artwork</svg>")

        # 2. Verify CairoSVG trigger for PNG version
        png_file = svg_file.with_suffix(".png")
        mock_cairo.assert_called_once_with(
            url=str(svg_file),
            write_to=str(png_file),
            unsafe=True
        )

        # 3. Verify README.md frontmatter creation
        readme_file = project_dir / "adlik" / "README.md"
        self.assertTrue(readme_file.exists())

        post = frontmatter.load(readme_file)
        self.assertEqual(post["title"], "Adlik Project")
        self.assertEqual(post["featured_image"], "primary/color/adlik-primary-color.svg")

    @patch("cairosvg.svg2png")
    @patch("requests.get")
    def test_main_non_svg_skips_cairosvg(self, mock_get, mock_cairo):
        """Test PNG logos are downloaded without invoking CairoSVG."""
        project_dir = Path(self.temp_dir.name) / "projects"

        api_payload = {
            "Data": [
                {
                    "Name": "Raster Project",
                    "Slug": "RasterProj",
                    "ProjectLogo": "https://example.com/logo.png"
                }
            ]
        }

        mock_api_resp = MagicMock()
        mock_api_resp.json.return_value = api_payload

        mock_logo_resp = MagicMock()
        mock_logo_resp.content = b"\x89PNG..."
        # Allow use as a context manager ('with requests.get(...) as response:')
        mock_logo_resp.__enter__.return_value = mock_logo_resp

        mock_get.side_effect = [mock_api_resp, mock_logo_resp]

        main(["-s", "lf-ai-foundation", "-p", str(project_dir)])

        png_file = project_dir / "rasterproj" / "primary" / "color" / "rasterproj-primary-color.png"
        self.assertTrue(png_file.exists())

        # CairoSVG should NOT be called for .png inputs
        mock_cairo.assert_not_called()

    @patch("cairosvg.svg2png")
    @patch("requests.get")
    def test_main_updates_existing_readme(self, mock_get, mock_cairo):
        """Test updating an existing README.md preserves existing content and updates frontmatter."""
        project_dir = Path(self.temp_dir.name) / "projects"

        # Pre-create an existing README with existing metadata and body
        existing_readme = project_dir / "existingproj" / "README.md"
        existing_readme.parent.mkdir(parents=True, exist_ok=True)

        initial_post = frontmatter.Post(
            content="## Existing Section\n\nPreserve this text.",
            category="AI",
            title="Old Title"
        )
        existing_readme.write_text(frontmatter.dumps(initial_post), encoding="utf-8")

        api_payload = {
            "Data": [
                {
                    "Name": "Updated Title",
                    "Slug": "ExistingProj",
                    "ProjectLogo": "https://example.com/logo.svg"
                }
            ]
        }

        mock_api_resp = MagicMock()
        mock_api_resp.json.return_value = api_payload

        mock_logo_resp = MagicMock()
        mock_logo_resp.content = b"<svg>test artwork</svg>"
        # Allow use as a context manager ('with requests.get(...) as response:')
        mock_logo_resp.__enter__.return_value = mock_logo_resp

        mock_get.side_effect = [mock_api_resp, mock_logo_resp]

        main(["-s", "lf-ai-foundation", "-p", str(project_dir)])

        updated_post = frontmatter.load(existing_readme)

        # Updated fields
        self.assertEqual(updated_post["title"], "Updated Title")
        self.assertEqual(updated_post["featured_image"], "primary/color/existingproj-primary-color.svg")

        # Preserved fields and content
        self.assertEqual(updated_post["category"], "AI")
        self.assertIn("## Existing Section", updated_post.content)

if __name__ == "__main__":
    unittest.main()
