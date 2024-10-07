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
    landscapeHostedProjects = '{}/api/projects/all.json'.format(landscapeBaseURL)

    csvRows = []

    with urllib.request.urlopen(landscapeHostedProjects) as hostedProjectsResponse:
        projectData = json.load(hostedProjectsResponse)
        categories = []
        categories.append("{category} / {subcategory}".format(category=projectData['category'],subcategory=projectData['subcategory'])
        if 'additional_categories' in projectData:
            for additional_category in projectData['additional_categories']:
                categories.append("{category} / {subcategory}".format(category=additional_category['category'],subcategory=additional_category['subcategory'])
        print("Processing {}...".format(projectData['name']))
        csvRows.append({
                'Name': projectData['name'],
                'Level': projectData['maturity'],
                'Logo URL': project['logo_url'],
                #'Slug': projectData['id'],
                'Categories': ','.join(categories),
                'Website': projectData['homepage_url'],
                #'Chair': projectData['extra']['chair'] if 'extra' in projectData and 'chair' in projectData['extra'] else None,
                #'TAC Representative': projectData['extra']['TAC_representative'] if 'extra' in projectData and 'TAC_representative' in projectData['extra'] else None,
                #'Documentation': projectData['extra']['documentation_url'] if 'extra' in projectData and 'documentation_url' in projectData['extra'] else None,
                #'Calendar': projectData['extra']['calendar_url'] if 'extra' in projectData and 'calendar_url' in projectData['extra'] else None,
                'Artwork': projectData['artwork_url'] if 'artwork_url' in projectData else None,
                #'iCal': projectData['extra']['ical_url'] if 'extra' in projectData and 'ical_url' in projectData['extra'] else None,
                'LFX Insights URL': projectData['dev_stats_url'] if 'dev_stats_url' in projectData else None,
                'Accepted Date': projectData['accepted_at'] if 'accepted_at' in projectData else None,
                #'Last Review Date': projectData['extra']['annual_review_date'] if 'extra' in projectData and 'annual_review_date' in projectData['extra'] else None,
                #'Next Review Date': projectData['extra']['next_annual_review_date'] if 'extra' in projectData and 'next_annual_review_date' in projectData['extra'] else None,
                'Slack URL': projectData['slack_url'] if 'slack_url' in projectData else None,
                'Chat Channel': projectData['chat_channel'] if 'chat_channel' in projectData else None,
                'Mailing List': projectData['mailing_list_url'] if 'mailing_list_url' in projectData else None,
                #'Github Org': projectData['project_org'] if 'project_org' in projectData else None,
                #'Best Practices Badge ID': projectData['bestPracticeBadgeId'] if 'bestPracticeBadgeId' in projectData else None,
                #'Primary Github Repo': projectData['repo_url'] if 'repo_url' in projectData else None,
                #'Contributed By': projectData['extra']['contributed_by'] if 'extra' in projectData and 'contributed_by' in projectData['extra'] else None
                })

    with open(projectsCsvFile, 'w') as projectsCsvFileObject:
        writer = csv.DictWriter(projectsCsvFileObject, fieldnames = csvRows[0].keys())
        writer.writeheader() 
        writer.writerows(csvRows) 
