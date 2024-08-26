#!/usr/bin/env python3
#
# Copyright this project and its contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import csv
import json
import os
import subprocess
from urllib.parse import urlparse

if "TAC_AGENDA_GH_PROJECT_URL" in os.environ and os.environ["TAC_AGENDA_GH_PROJECT_URL"] != '':
    urlparts = urlparse(os.environ["TAC_AGENDA_GH_PROJECT_URL"]).path.split('/')
    if urlparts and urlparts[1] == 'orgs' and urlparts[3] == 'projects':
        csvFile = '_data/meeting-agenda-items.csv'
        jsonProjectData = subprocess.run("gh project item-list {gh_project_id} --owner {gh_org} --format json".format(gh_project_id=urlparts[4],gh_org=urlparts[2]), shell=True, capture_output=True).stdout

        csvRows = []
        projectData = json.loads(jsonProjectData)
        for item in projectData['items']:
            print("Processing {}...".format(item['content']['title']))
            meetingItem = {
                'title': item['content']['title'],
                'url': item['content']['url'],
                'number': item['content']['number'],
                'scheduled_date': item['scheduled Date'] if 'scheduled Date' in item else None,
                'status': item['status'] if 'status' in item else None
                }
            if 'labels' in item:
                if '1-new-project-wg' in item['labels']:
                    meetingItem['meeting_label'] = '1-new-project-wg'
                elif '2-annual-review' in item['labels']:
                    meetingItem['meeting_label'] = '2-annual-review'
                elif '3-tac-meeting-long' in item['labels']:
                    meetingItem['meeting_label'] = '3-tac-meeting-long'
                elif '4-tac-meeting-short' in item['labels']:
                    meetingItem['meeting_label'] = '4-tac-meeting-short'
            else:
                meetingItem['meeting_label'] = None
            csvRows.append(meetingItem)

        with open(csvFile, 'w') as csvFileObject:
            writer = csv.DictWriter(csvFileObject, fieldnames = csvRows[0].keys())
            writer.writeheader() 
            writer.writerows(csvRows) 
