#!/usr/bin/env python
from __future__ import print_function, unicode_literals
from time import sleep
import os

from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity
import yaml

from github import Github
import data


def cache_events(client, org, limit):
    """Pull new events from Github and return the [max_size] newest
       events.
    """
    newest_events = data.recent_events(limit=limit)

    try:
        members = client.organization_members(org)
        logins = filter(lambda user: user['name'], members)
        newest_events = filter(lambda event: event['actor'] in logins,
                               newest_events)
    except:
        print('Error getting members')
        return newest_events

    for user in members:
        try:
            user_events = client.user_activity(user['login'])
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
        sleep(600)
