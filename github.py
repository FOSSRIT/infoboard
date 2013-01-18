"""Provides a wrapper around certain github API calls."""
from __future__ import unicode_literals

from urllib2 import HTTPError

import requests
import json

import data


class Github(object):
    def __init__(self, auth=None):
        self.auth = auth
        self.rate_limiting = (5000, 5000)

    def requests_wrapper(self, url):
        r = requests.get(url, auth=self.auth)
        self.rate_limiting = (r.headers['x-ratelimit-remaining'],
                              r.headers['x-ratelimit-limit'])
        if r.status_code == 404:
            r.raise_for_status()

        content = json.loads(r.content)
        return content

    def organization_members(self, org_name):
        members = self.requests_wrapper('https://api.github.com/orgs/%s/members' % org_name)
        return map(data.user_info, members)

    def user_activity(self, user_name):
        events = self.requests_wrapper('https://api.github.com/users/%s/events' % user_name)
        return map(data.event_info, events)

    def repo_information(self, repo_name):
        repository = self.requests_wrapper('https://api.github.com/repos/%s' % repo_name)
        return data.repo_info(repository)


if __name__ == "__main__":
    g = Github()
    users = g.organization_members('FOSSRIT')
    print(users[0]['login'])
    print(g.user_activity(users[0]['login']))
