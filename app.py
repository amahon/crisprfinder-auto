#!/usr/bin/env python

import os
import pprint
import uuid
import re

import requests
from clint.textui.progress import Bar as ProgressBar
import requests_toolbelt
from bs4 import BeautifulSoup


# Before we do anything, let's set a couple of utility variables.

# Set up a couple of directories.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, 'data', 'input')
OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')

# Define the URL that we will post requests against.
CRISPRFINDER_DOMAIN = 'http://crispr.i2bc.paris-saclay.fr'
CRISPRFINDER_POST_PATH = '/cgi-bin/crispr/advRunCRISPRFinder.cgi'

# First, we need to collect all of our input data. We will do this by iterating
# through the files found in data/input and storing their path in the 
# list `input_files`
input_files = []

# Iterate over files in `INPUT_DIR`
for entry in os.scandir(INPUT_DIR):
    # Since we only want FASTA files, we will only proceed with files that
    # end with the string `.fasta`
    if entry.name.endswith('.fasta'):
        input_files += [entry, ]


def create_upload_progress_callback(encoder):
    upload_size = encoder.len
    bar = ProgressBar(expected_size=upload_size, filled_char='=')

    def callback(monitor):
        bar.show(monitor.bytes_read)

    return callback


def submit_fasta(dir_entry):

    print('Uploading FASTA: {}'.format(dir_entry.name))

    request_uuid = uuid.uuid1()

    encoder = requests_toolbelt.multipart.encoder.MultipartEncoder({
        'fname': (dir_entry.name, open(dir_entry.path, 'rb'), 'application/octet-stream'),
        'SeqContent': '',
        'MAX_FILE_SIZE': '100000000',
        'user_id': '',
        'DIRname': str(request_uuid),
        'submit': 'FindCRISPR',
    })

    callback = create_upload_progress_callback(encoder)
    monitor = requests_toolbelt.multipart.encoder.MultipartEncoderMonitor(encoder, callback)

    headers = {
        'Content-Type': monitor.content_type,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Origin': 'http://crispr.i2bc.paris-saclay.fr',
        'Referer': 'http://crispr.i2bc.paris-saclay.fr/Server/',
        'Upgrade-Insecure-Requests': 1,
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36'
    }

    url = '{}{}'.format(CRISPRFINDER_DOMAIN, CRISPRFINDER_POST_PATH)
    response = requests.post(url, headers=headers, data=monitor)

    return (dir_entry, request_uuid, response, )



def process_response(dir_entry, request_uuid, response):

    soup = BeautifulSoup(response.content, 'html.parser')
    crispr_count_re = re.compile("Confirmed CRISPRs = ([0-9]+)")
    crispr_count_td = soup.find('td', string=crispr_count_re)
    crispr_count_match = crispr_count_re.match(crispr_count_td.contents[0])
    n_confirmed_crisprs = int(crispr_count_match.groups()[0])

    print('Found {} Confirmed Crisprs'.format(n_confirmed_crisprs))

    for i in range(n_confirmed_crisprs):

        crispr_number = i + 1

        print('Downloading CRISPR {}'.format(crispr_number))

        headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Origin': 'http://crispr.i2bc.paris-saclay.fr',
            'Referer': 'http://crispr.i2bc.paris-saclay.fr/Server/',
            'Upgrade-Insecure-Requests': 1,
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.94 Safari/537.36'
        }

        url = '{}/tmp/output/crisprfinder/{}/tmp_1/tmp_1_Crispr_{}'.format(CRISPRFINDER_DOMAIN, request_uuid, crispr_number)
        response = requests.post(url, headers=headers)

        print('Waiting for response...')
        output_filename = os.path.join(OUTPUT_DIR, ('{}.{}.CRISPR'.format(dir_entry.name, crispr_number)))
        print('Saving CRISPR Details to file: {}'.format(os.path.relpath(output_filename, BASE_DIR)))
        with open(output_filename, 'wb') as output_file:
            output_file.write(response.content)

for dir_entry in input_files:
    dir_entry, request_uuid, response = submit_fasta(dir_entry)
    process_response(dir_entry, request_uuid, response)