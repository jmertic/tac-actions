#!/usr/bin/env python3
#
# Copyright this project and its contributors
# SPDX-License-Identifier: Apache-2.0
#
# encoding=utf8

import yaml
import urllib.request
import urllib.parse
import json
import os

if "LANDSCAPE_URL" in os.environ and os.environ["LANDSCAPE_URL"] != '' and "ARTWORK_URL" in os.environ and os.environ["ARTWORK_URL"] != '':
    cloMonitorFile = '_data/clomonitor.yaml'
    landscapeBaseURL = os.environ["LANDSCAPE_URL"] 
    landscapeHostedProjects = landscapeBaseURL+'/data/exports/projects-hosted.json'

    artworkRepoLogoURL = os.environ["LANDSCAPE_URL"]

    projectEntries = []

    with urllib.request.urlopen(landscapeHostedProjects) as hostedProjectsResponse:
        projectData = json.load(hostedProjectsResponse)
        if projectData['project'] == 'emeritus':
            continue
        print("Processing {}...".format(projectData['name']))
        
        # grab correct logo from artwork repo
        logo_url = ''
        logo_url_dark = ''
        if 'artwork_url' in projectData:
            urlparts = urllib.parse.urlparse(projectData['artwork_url'])
            with urllib.request.urlopen('{}://{}/assets/data.json'.format(urlparts.scheme,urlparts.netloc)) as artworkResponse:
                artworkData = json.load(artworkResponse)
                logo_url = '{}://{}{}{}'.format(urlparts.scheme,urlparts.netloc,urlparts.path,artworkData[urlparts.path]['primary_logo'])
                logo_url_dark = '{}://{}{}{}'.format(urlparts.scheme,urlparts.netloc,urlparts.path,artworkData[urlparts.path]['dark_logo'])
        else:
            logo_url = project['logo']
            logo_url_dark = project['logo']

        projectEntry = {
            'name': projectData['id'],
            'display_name': projectData['name'],
            'description': projectData['description'],
            'category': 'Visual Effects and Computer Graphics',
            'logo_url': logo_url,
            'logo_url_dark': logo_url_dark,
            'devstats_url': projectData['dev_stats_url'] if 'dev_stats_url' in projectData else None,
            'maturity': projectData['maturity'],
            'repositories': []
        }
        if 'repositories' in projectData:
            for repo in projectData['repositories']:
                projectEntry['repositories'].append({
                    'name': repo['url'].rsplit('/', 1)[-1],
                    'url': repo['url'],
                    'exclude': ['clomonitor']
                })
            projectEntries.append(projectEntry)
    
with open(cloMonitorFile, 'w') as cloMonitorFileObject:
    yaml.dump(projectEntries, cloMonitorFileObject, sort_keys=False, indent=2)
