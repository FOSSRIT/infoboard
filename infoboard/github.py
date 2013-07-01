"""Provides a wrapper around certain github API calls."""
from __future__ import unicode_literals

from cgi import escape
from urllib2 import HTTPError

import requests
import json
import logging

import data


class Github(object):
    def __init__(self, auth=None):
        self.auth = auth
        self.rate_limiting = (5000, 5000)
        self.broken_repos = ['/']

    def _requests_wrapper(self, url):
        try:
            if self.auth:
                r = requests.get(url, auth=self.auth)
            else:
                r = requests.get(url)
        except requests.exceptions.ConnectionError:
            return []

        self.rate_limiting = (r.headers['x-ratelimit-remaining'],
                              r.headers['x-ratelimit-limit'])
        if r.status_code == 404:
            r.raise_for_status()
        
        try:
            payload = json.loads(escape(r.content))
        except ValueError:
            # JSON decoding failed
            return dict()
        if 'message' in payload:
            # Github has a message for us but not a response
            logging.error(payload)
            return dict()

        return payload

    def organization_members(self, org_name):
        members = self._requests_wrapper('https://api.github.com/orgs/%s/members' % org_name)
        return map(data.user_info, members)

    def user_activity(self, user_name):
        events = self._requests_wrapper('https://api.github.com/users/%s/events' % user_name)
        return map(data.event_info, events)

    def repo_information(self, repo_name):
        if repo_name in self.broken_repos:
            return
        try:
            repository = self._requests_wrapper('https://api.github.com/repos/%s' % repo_name)
            return data.repo_info(repository)
        except requests.exceptions.HTTPError:
            logging.error("Error finding repo http://github.com/{0}"
                          .format(repo_name))
            self.broken_repos.append(repo_name)
            return None


if __name__ == "__main__":
    g = Github()
    users = g.organization_members('FOSSRIT')
    logging.info(users[0]['login'])
    logging.info(g.user_activity(users[0]['login']))
