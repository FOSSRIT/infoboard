"""
Many calls to PyGithub hide lazy calls to the Github API.  These functions
wrap the actual work so that the data returned can get cached in Knowledge.
"""
from __future__ import print_function, unicode_literals

from collections import defaultdict
from datetime import datetime, timedelta

from knowledge.model import DBSession, Entity


def recent_events(days=0, limit=0):
    events = DBSession.query(Entity) \
                      .filter(Entity.name.startswith('event\_', escape='\\')) \
                      .all()
    if days > 0:
        yesterday = datetime.now() - timedelta(days=days)
        events = filter(lambda event: event['created_at'] > yesterday, events)
    events.sort(key=lambda event: event['created_at'], reverse=True)
    if len(events) > limit > 0:
        events = events[:limit]
    return events


def top_contributions():
    week_activity = recent_events(7)
    user_activity = defaultdict(lambda: defaultdict(int))
    repo_activity = defaultdict(lambda: defaultdict(int))
    for event in week_activity:
        if event['type'] == 'PushEvent':
            changes = event['payload']['size']
            key = 'commits'
        elif event['type'] in ['CommitCommentEvent', 'FollowEvent',
                               'IssueCommentEvent', 'WatchEvent']:
            # Social (non-coding) events carry less weight
            changes = .1
            key = 'social actions'
        else:
            changes = 1
            key = event['type']
        user_activity[event['actor']]['count'] += changes
        user_activity[event['actor']][key] += changes

        if Entity.by_name(event['repo']):
            if event['type'] in ['CommitCommentEvent', 'FollowEvent',
                               'IssueCommentEvent', 'WatchEvent']:
                changes = 1
            repo_activity[event['repo']]['count'] += changes
            repo_activity[event['repo']][event['actor']] += changes
    return user_activity, repo_activity


def event_info(event):
    event_name = u'event_{0}'.format(event['id'])
    if not Entity.by_name(event_name):
        print("Caching new event {0}".format(event_name))
        entity = Entity(event_name)
        entity['name'] = event_name
        entity[u'actor'] = user_info(event['actor']).name
        entity[u'repo'] = event['repo']['name']
        entity[u'type'] = event['type']
        entity[u'payload'] = event['payload']
        entity[u'created_at'] = datetime.strptime(event['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        if event['type'] in ["CommitCommentEvent", "IssueCommentEvent"]:
            entity[u'comment'] = comment_info(event['payload']['comment']).name
        if event['type'] in ["IssueCommentEvent", "IssuesEvent"]:
            entity['issue'] = issue_info(event['payload']['issue']).name
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(event_name)


def user_info(user):
    user_name = u'user_{0}'.format(user['id'])
    if not Entity.by_name(user_name):
        print("Caching new user {0}".format(user_name))
        entity = Entity(user_name)
        entity['login'] = user['login']
        entity['gravatar'] = user['gravatar_id']
        entity['avatar'] = u'http://www.gravatar.com/avatar/{0}?s=200' \
                             .format(user['gravatar_id'])
        # Not everyone has set a name for their account.
        if user.get('name'):
            entity[u'name'] = user['name']
        else:
            entity[u'name'] = user['login']
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(user_name)


def repo_info(repo):
    repo_name = repo.get('full_name', '{0}/{1}'.format(repo['owner']['login'],
                                                       repo['name']))
    if not Entity.by_name(repo_name):
        print("Caching new repository {0}".format(repo_name))
        entity = Entity(repo_name)
        entity['name'] = repo['full_name']
        # Evidently you cannot set facts to None. (?)
        if not repo['description']:
            entity['description'] = u''
        else:
            entity['description'] = repo['description']
        entity['url'] = repo['html_url']
        entity['owner'] = user_info(repo['owner']).name
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(repo_name)


def comment_info(comment):
    comment_name = u'comment_{0}'.format(comment['id'])
    if not Entity.by_name(comment_name):
        print("Caching new comment {0}".format(comment_name))
        entity = Entity(comment_name)
        entity[u'body'] = comment['body']
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(comment_name)


def issue_info(issue):
    issue_name = u'issue_{0}'.format(issue['id'])
    if not Entity.by_name(issue_name):
        print("Caching new issue {0}".format(issue_name))
        entity = Entity(issue_name)
        entity[u'title'] = issue['title']
        entity[u'number'] = issue['number']
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(issue_name)
