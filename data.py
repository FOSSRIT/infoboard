"""
Many calls to PyGithub hide lazy calls to the Github API.  These functions
wrap the actual work so that the data returned can get cached in Knowledge.
"""

from knowledge.model import DBSession, Entity


def event_info(event):
    event_name = u'event_{0}'.format(event.id)
    if not Entity.by_name(event_name):
        print("Caching new event {0}".format(event_name))
        entity = Entity(event_name)
        entity[u'actor'] = user_info(event.actor).name
        entity[u'repo'] = event.repo.name
        entity[u'type'] = event.type
        entity[u'payload'] = event.payload
        if event.type in ["CommitCommentEvent", "IssueCommentEvent"]:
            entity[u'comment'] = comment_info(event.payload['comment']).name
        if event.type in ["IssueCommentEvent", "IssuesEvent"]:
            entity['issue'] = issue_info(event.payload['issue']).name
        DBSession.add(entity)
        DBSession.commit()
    return Entity.by_name(event_name)


def user_info(user):
    user_name = u'user_{0}'.format(user.id)
    if not Entity.by_name(user_name):
        print("Caching new user {0}".format(user_name))
        entity = Entity(user_name)
        entity[u'avatar'] = user.avatar_url
        entity[u'gravatar'] = user.gravatar_id
        # Not everyone has set a name for their account.
        if user.name:
            entity[u'name'] = user.name
        else:
            entity[u'name'] = user.login
        DBSession.add(entity)
    return Entity.by_name(user_name)


def comment_info(comment):
    comment_name = u'comment_{0}'.format(comment['id'])
    if not Entity.by_name(comment_name):
        print("Caching new comment {0}".format(comment_name))
        entity = Entity(comment_name)
        entity[u'body'] = comment['body']
        DBSession.add(entity)
    return Entity.by_name(comment_name)


def issue_info(issue):
    issue_name = u'issue_{0}'.format(issue['id'])
    if not Entity.by_name(issue_name):
        print("Caching new issue {0}".format(issue_name))
        entity = Entity(issue_name)
        entity[u'title'] = issue['title']
        entity[u'number'] = issue['number']
        DBSession.add(entity)
    return Entity.by_name(issue_name)
