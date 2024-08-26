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
from urllib.parse import urlparse

if "LFX_TAC_COMMITTEE_URL" in os.environ and os.environ["LFX_TAC_COMMITTEE_URL"] != '':
    tacmembersCsvFile = '_data/tacmembers.csv'
    urlparts = urlparse(os.environ["LFX_TAC_COMMITTEE_URL"]).path.split('/')
    if urlparts and urlparts[1] == 'project' and urlparts[3] == 'collaboration' and urlparts[4] == 'committees':
        committeeURL = 'https://api-gw.platform.linuxfoundation.org/project-service/v2/public/projects/{project_id}/committees/{committee_id}/members'.format(project_id=urlparts[2],committee_id=urlparts[5])
        csvRows = []

        with urllib.request.urlopen(committeeURL) as committeeURLResponse:
            committeeURLResponseJSON = json.load(committeeURLResponse)
            for committeeMember in committeeURLResponseJSON['Data']:
                print("Processing {} {}...".format(committeeMember['FirstName'].title(),committeeMember['LastName'].title()))
                csvRows.append({
                    'Full Name': "{} {}".format(committeeMember['FirstName'].title(),committeeMember['LastName'].title()),
                    'Account Name: Account Name': committeeMember['Organization']['Name'] if 'Organization' in committeeMember and 'Name' in committeeMember['Organization'] else None,
                    'Appointed By': committeeMember['AppointedBy'] if 'AppointedBy' in committeeMember else None,
                    'Voting Status': committeeMember['VotingStatus'] if 'VotingStatus' in committeeMember else None,
                    'Special Role': committeeMember['Role'] if 'Role' in committeeMember else None,
                    'Title': committeeMember['Title'] if 'Title' in committeeMember else None,
                    'HeadshotURL': committeeMember['LogoURL'] if 'LogoURL' in committeeMember else None
                    })

        with open(tacmembersCsvFile, 'w') as tacmembersCsvFileObject:
            writer = csv.DictWriter(tacmembersCsvFileObject, fieldnames = csvRows[0].keys())
            writer.writeheader() 
            writer.writerows(csvRows) 
