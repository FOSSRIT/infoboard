#!/usr/bin/env python
"""
This script connects to the infoboard db and scrapes github calls at regular
intervals.  It should cache all the events and repositories it sees for later
use by the frontend(s).
"""

from __future__ import unicode_literals
from time import sleep
import logging
import os

from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity
import yaml

from github import Github


def cache_events(client, org):
    """Pull new events from Github."""

    try:
        members = client.organization_members(org)
    except:
        logging.error('Error getting members')
        return

    client.broken_repos = ['/']
    for user in members:
        logging.debug("Looking up user {}".format(user))
        events = client.user_activity(user['login'])
        for event in events:
            if not Entity.by_name(event['repo']):
                client.repo_information(event['repo'])


    logging.info("You have {0} of {1} calls left this hour."
          .format(*client.rate_limiting))


if __name__ == '__main__':
    loglog = logging.getLogger()
    loglog.setLevel(logging.INFO)
    yaml_location = os.path.join(os.path.split(__file__)[0], 'settings.yaml')
    with open(yaml_location) as yaml_file:
        conf = yaml.load(yaml_file)
    backend = conf['backend']
    common = conf['common']

    # Set up Knowledge
    engine = create_engine(common['db_uri'])
    init_model(engine)
    metadata.create_all(engine)

    if backend['user'] and backend['password']:
        client = Github((backend['user'], backend['password']))
    else:
        client = Github()

    while True:
        cache_events(client, common['organization'])
        sleep(common['interval'])
