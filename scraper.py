#!/usr/bin/env python
from __future__ import print_function, unicode_literals
from time import sleep
import os

from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity
import yaml

from github import Github


def cache_events(client, org):
    """Pull new events from Github and return the [max_size] newest
       events.
    """

    try:
        members = client.organization_members(org)
    except:
        print('Error getting members')
        return

    for user in members:
        try:
            events = client.user_activity(user['login'])
            for event in events:
                if not Entity.by_name(event['repo']):
                    client.repo_information(event['repo'])
        except:
            print("Something went wrong updating the events for {0}." \
                  .format(user['login']))
            continue


    print("You have {0} of {1} calls left this hour."
          .format(*client.rate_limiting))


if __name__ == '__main__':
    yaml_location = os.path.join(os.path.split(__file__)[0], 'settings.yaml')
    with open(yaml_location) as yaml_file:
        conf = yaml.load(yaml_file)

    # Set up Knowledge
    engine = create_engine(conf['db_uri'])
    init_model(engine)
    metadata.create_all(engine)

    if conf['user'] and conf['password']:
        client = Github((conf['user'], conf['password']))
    else:
        client = Github()

    while True:
        cache_events(client, conf['organization'], conf['events'])
        sleep(conf['interval'])
