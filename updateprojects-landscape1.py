#!/usr/bin/env python3
#
# Copyright this project and its contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import csv
import urllib.request
import json
import os

if "LANDSCAPE_URL" in os.environ and os.environ["LANDSCAPE_URL"] != '':
    projectsCsvFile = '_data/projects.csv'
    landscapeBaseURL = os.environ["LANDSCAPE_URL"] 
    landscapeHostedProjects = landscapeBaseURL+'/data/exports/projects-hosted.json'
    landscapeSingleItem = landscapeBaseURL+'/data/items/{}.json'

    csvRows = []

    with urllib.request.urlopen(landscapeHostedProjects) as hostedProjectsResponse:
        for projectStage in json.load(hostedProjectsResponse):
            for project in projectStage['items']:
                with urllib.request.urlopen(landscapeSingleItem.format(project['id'])) as singleItemResponse:
                    projectData = json.load(singleItemResponse)
                    categories = []
                    categories.append(projectData['path'])
                    if 'second_path' in projectData:
                        categories = categories + projectData['second_path']
                    print("Processing {}...".format(projectData['name']))
                    csvRows.append({
                            'Name': projectData['name'],
                            'Level': projectData['project'],
                            'Logo URL': project['logo'],
                            'Slug': projectData['id'],
                            'Categories': ','.join(categories),
                            'Website': projectData['homepage_url'],
                            'Chair': projectData['extra']['chair'] if 'extra' in projectData and 'chair' in projectData['extra'] else None,
                            'TAC Representative': projectData['extra']['TAC_representative'] if 'extra' in projectData and 'TAC_representative' in projectData['extra'] else None,
                            'Documentation': projectData['extra']['documentation_url'] if 'extra' in projectData and 'documentation_url' in projectData['extra'] else None,
                            'Calendar': projectData['extra']['calendar_url'] if 'extra' in projectData and 'calendar_url' in projectData['extra'] else None,
                            'Artwork': projectData['extra']['artwork_url'] if 'extra' in projectData and 'artwork_url' in projectData['extra'] else None,
                            'iCal': projectData['extra']['ical_url'] if 'extra' in projectData and 'ical_url' in projectData['extra'] else None,
                            'LFX Insights URL': projectData['extra']['dev_stats_url'] if 'extra' in projectData and 'dev_stats_url' in projectData['extra'] else None,
                            'Accepted Date': projectData['extra']['accepted'] if 'extra' in projectData and 'accepted' in projectData['extra'] else None,
                            'Last Review Date': projectData['extra']['annual_review_date'] if 'extra' in projectData and 'annual_review_date' in projectData['extra'] else None,
                            'Next Review Date': projectData['extra']['next_annual_review_date'] if 'extra' in projectData and 'next_annual_review_date' in projectData['extra'] else None,
                            'Slack': projectData['extra']['chat_channel'] if 'extra' in projectData and 'chat_channel' in projectData['extra'] else projectData['extra']['slack_url'] if 'extra' in projectData and 'slack_url' in projectData['extra'] else None,
                            'Mailing List': projectData['extra']['mailing_list_url'] if 'extra' in projectData and 'mailing_list_url' in projectData['extra'] else None,
                            'Github Org': projectData['project_org'] if 'project_org' in projectData else None,
                            'Best Practices Badge ID': projectData['bestPracticeBadgeId'] if 'bestPracticeBadgeId' in projectData else None,
                            'Primary Github Repo': projectData['repo_url'] if 'repo_url' in projectData else None,
                            'Contributed By': projectData['extra']['contributed_by'] if 'extra' in projectData and 'contributed_by' in projectData['extra'] else None
                            })

    with open(projectsCsvFile, 'w') as projectsCsvFileObject:
        writer = csv.DictWriter(projectsCsvFileObject, fieldnames = csvRows[0].keys())
        writer.writeheader() 
        writer.writerows(csvRows) 
