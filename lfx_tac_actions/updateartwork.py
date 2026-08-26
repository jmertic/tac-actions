#!/usr/bin/env python3
#
# Copyright this project and it's contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import requests
import os
from urllib.parse import urlparse, quote
from pathlib import Path
import logging
import re
import frontmatter
import cairosvg
import argparse
import yaml

from . import setup_logging, setup_argparse

def path_inside_cwd(path_str: str) -> Path:
    cwd = Path.cwd().resolve()

    # Resolve the path relative to CWD
    target_path = (cwd / path_str).resolve()

    # Check if the target is contained within CWD
    if not target_path.is_relative_to(cwd):
        raise argparse.ArgumentTypeError(
            f"Path '{path_str}' escapes current working directory ({cwd})"
        )

    return target_path

def main(args=None):
    parser = setup_argparse(description="Downloads the logo for the subprojects of a project identified by `--slug`, saving them in the current working directory with naming format of `SLUG/primary/color/SLUG-primary-color.svg` and updating the `SLUG/README.md` as appropriate.")
    parser.add_argument("-s", "--slug", help="Umbrella Foundation slug", required=True)
    parser.add_argument("-p", "--project-path",
        help="Path to where project logos are to be saved (must be inside CWD)",
        type=path_inside_cwd,
        default=(Path.cwd() / "projects"))
    args = parser.parse_args(args)

    setup_logging(args.log_level)

    endpoint_url = 'https://api-gw.platform.linuxfoundation.org/project-service/v1/public/projects?$filter=parentSlug%20eq%20{}%20and%20status%20eq%20Active&pageSize=2000&orderBy=name&hasLogo=true'

    # Validate the string to prevent SSRF / Injection. A standard slug should only contain alphanumeric characters and hyphens.
    if not re.match(r'^[a-zA-Z0-9-]+$', args.slug):
        logging.critical(f"Invalid slug format: '{args.slug}'. Slugs must only contain alphanumeric characters and hyphens.")
        return

    # Safely URL-encode the validated slug just as a secondary defense mechanism
    safe_slug = quote(args.slug)

    try:
        response = requests.get(endpoint_url.format(safe_slug))
        response.raise_for_status()
        projectlist = response.json()
    except Exception as e:
        logging.critical(f"Error getting projects at {response.url} - {e}")
        return

    if len(projectlist['Data']) == 0:
        logging.critical(f"No records found for `{safe_slug}`")

    foundslugs = []
    for record in projectlist['Data']:
        logging.info("Processing artwork for {}".format(record.get('Name')))
        _, extension = os.path.splitext(urlparse(record.get('ProjectLogo')).path)
        logo_path = (args.project_path / record.get('Slug').lower() / "primary" / "color" / f"{record.get('Slug').lower()}-primary-color").with_suffix(extension)
        try:
            with requests.get(record.get('ProjectLogo'),stream=False) as response:
                response.raise_for_status()
                logo_path.parent.mkdir(parents=True, exist_ok=True)
                with open(logo_path, 'wb') as f:
                    logging.info("Writing file {}".format(f.name))
                    f.write(response.content)
                if extension == '.svg':
                    # add png version as well
                    logging.info("Writing file {}".format(str(logo_path.with_suffix(".png"))))
                    cairosvg.svg2png(
                        url=str(logo_path),
                        write_to=str(logo_path.with_suffix(".png")),
                        unsafe=True
                    )
        except Exception as e:
            logging.exception(f"Error getting file {record.get('ProjectLogo')} - '{e}'")
            continue

        readme_path = args.project_path / record.get('Slug').lower() / "README.md"
        try:
            post = frontmatter.load(readme_path)
        except FileNotFoundError:
            post = frontmatter.Post(content="")

        post['title'] = record.get('Name')
        post['featured_image'] = str(logo_path.relative_to(args.project_path / record.get('Slug').lower()))

        readme_path.parent.mkdir(parents=True, exist_ok=True)
        readme_path.write_text(frontmatter.dumps(post), encoding="utf-8")
        foundslugs.append(record.get('Slug').lower())

    # Hide projects that don't come through the endpoint ( would likely be Archived ones )
    # Iterate through all README.md files in subdirectories
    for readme_path in Path(args.project_path).rglob("README.md"):
        if readme_path.parent.name in foundslugs:
            continue

        try:
            content = readme_path.read_text(encoding="utf-8")
            post = frontmatter.loads(content)

            # Preserve existing order and ensure target key is last
            metadata = dict(post.metadata)
            metadata.pop("level", None)
            metadata["level"] = 'Archived'

            # Format YAML manually with sort_keys=False
            yaml_frontmatter = yaml.dump(
                metadata, sort_keys=False, allow_unicode=True
            ).strip()

            # Recombine front matter and markdown body
            body = post.content
            new_content = f"---\n{yaml_frontmatter}\n---\n{body}"

            readme_path.write_text(new_content, encoding="utf-8")

            logging.info(f"Marked {readme_path} as Archived")

        except Exception as e:
            print(f"Error processing {readme_path}: {e}")


if __name__ == '__main__':
    main()
