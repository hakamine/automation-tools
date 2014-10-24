#!/usr/bin/env python2

from __future__ import print_function
import base64
import datetime
import json
import os
import requests
import sys
import time


def get_status(unit_uuid, unit_type):
    """ Get status of the SIP or Transfer with unit_uuid.

    :param str unit_uuid: UUID of the unit to query for.
    :param str unit_type: SIP or Transfer.
    :returns: Status of the unit from Archivematica.
    """
    # If transfer & completed, used SIP UUID to get status
    # Update last_unit
    pass

def send_email():
    pass


def start_transfer(ss_url, ts_location_uuid, ts_path, pipeline_uuid, am_url, user_name, api_key):
    # Start new transfer
    # Get sorted list from source dir
    url = ss_url + '/api/v2/location/' + ts_location_uuid + '/browse/'
    params = {}
    if ts_path:
        params = {'path': base64.b64encode(ts_path)}
    response = requests.get(url, params=params)
    if response.status_code != 200:
        print('Unable to browse transfer source location', ts_location_uuid, file=sys.stderr)
        sys.exit(1)
    dirs = response.json()['directories']
    dirs = map(base64.b64decode, dirs)

    # Find first one not already started (store in DB?)
    count_file = "count"
    try:
        with open(count_file, 'r') as f:
            last_transfer = int(f.readline())
    except Exception:
        last_transfer = 0
    start_at = last_transfer
    target = dirs[start_at]
    print("Starting with", target)
    # Get CP Loc UUID
    url = ss_url + '/api/v2/location/'
    params = {'pipeline__uuid': pipeline_uuid, 'purpose': 'CP'}
    response = requests.get(url, params=params)
    resource_uri = response.json()['objects'][0]['resource_uri']
    # Copy to pipeline
    url = ss_url + resource_uri
    source = os.path.join(ts_path, target)
    destination = os.path.join("watchedDirectories", "activeTransfers", "standardTransfer", target)
    data = {
        'origin_location': '/api/v2/location/' + ts_location_uuid + '/',
        'pipeline': pipeline_uuid,
        'files': [{'source': source, 'destination': destination}]
    }
    response = requests.post(url, data=json.dumps(data), headers={'Content-Type': 'application/json'})

    # Run munging scripts (What params to scripts?)
    # Update default config
    # TODO pick correct processingMCP based on existence of access dir
    # processing_available = '/home/users/hbecker/archivematica/src/MCPServer/share/sharedDirectoryStructure/sharedMicroServiceTasksConfigs/processingMCPConfigs/'
    # shutil.copyfile(processing_available + "defaultProcessingMCP.xml", destination + "/processingMCP.xml")

    # Approve transfer
    print("Ready to start")
    result = approve_transfer(target, am_url, api_key, user_name)
    # TODO Mark as started
    if result:
        start_at = start_at + 1
        print('Approved', result)
        with open(count_file, 'w') as f:
            print(start_at, file=f)
        with open(last_unit_file, 'w') as f:
            print(result, 'file', file=f)
    else:
        print('Not approved')

    print("Finished " + target + " at " + str(datetime.datetime.now()))
    print(" ")


def list_transfers(url, api_key, user_name):
    get_url = url + "/api/transfer/unapproved"
    g = requests.get(get_url, params={'username': user_name, 'api_key': api_key})
    return g.json()


def approve_transfer(directory_name, url, api_key, user_name):
    print("Approving " + directory_name)
    time.sleep(6)
    # List available transfers
    post_url = url + "/api/transfer/approve"
    waiting_transfers = list_transfers(url, api_key, user_name)
    for a in waiting_transfers['results']:
        print("Found waiting transfer: " + a['directory'])
        if a['directory'] == directory_name:
            # Post to approve transfer
            params = {'username': user_name, 'api_key': api_key, 'type': a['type'], 'directory': directory_name}
            r = requests.post(post_url, data=params)
            if r.status_code != 200:
                return False
            return a['uuid']
        else:
            print(a['directory'] + " is not what we are looking for")
    else:
        return False

def main():
    # Params/config file info
    # Transfer type, dir only vs files
    # AM URL
    am_url = 'http://127.0.0.1'
    # SS URL
    ss_url = 'http://127.0.0.1:8000'
    # Source transfer dir and Location UUID
    ts_location_uuid = 'b8b2e0ef-f599-4d70-a91c-a4b13da0b355'
    ts_path = "TestTransfers"
    pipeline_uuid = 'd46cfa6a-9a5e-4f1f-8f16-9ff6f84d925a'
    # username & api key
    user_name = 'demo'
    api_key = 'f17657bd1349a4a8b682853c27fcf4cffa27a466'

    now = datetime.datetime.now()
    print("Waking up at ", now)
    # FIXME Set the cwd to the same as this file so count_file works
    this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.chdir(this_dir)

    # Check status of last unit
    # Find last unit started
    last_unit_file = 'last_unit'
    try:
        with open(last_unit_file, 'r') as f:
            last_unit = f.readline()
    except Exception:
        last_unit = ''
    print('last_unit', last_unit)
    unit_uuid, unit_type = last_unit.split()
    # Get status
    status = get_status(unit_uuid, unit_type)
    # If processing, exit
    if status == 'PROCESSING':
        sys.exit(0)
    # If waiting on input, send email, exit
    elif status == 'USER_INPUT':
        send_email()
        sys.exit(0)
    # If failed, rejected, start new transfer
    elif status in ('FAIELD', 'REJECTED'):
        start_transfer(ss_url, ts_location_uuid, ts_path, pipeline_uuid, am_url, user_name, api_key)

if __name__ == '__main__':
    sys.exit(main())
