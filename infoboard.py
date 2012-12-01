#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""

import os

from urllib import urlretrieve

from gi.repository import Gtk
from github import Github

ORG = "FOSSRIT"

# Setup caching
base_dir = os.path.split(__file__)[0]
from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, DBSession, Entity
engine = create_engine('sqlite://{0}/knowledge.db'.format(base_dir))
init_model(engine)
metadata.create_all(engine)


class InfoWin(Gtk.Window):
    def __init__(self):
        super(InfoWin, self).__init__()
        self.set_default_size(600, 800)
        self.g = Github()
        self.org = self.g.get_organization(ORG)

        scrolls = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        latest_events = self.org.get_events()[:10]
        for event in latest_events:
            box.add(Spotlight(event_info(event)))
        scrolls.add_with_viewport(box)
        self.add(scrolls)


class Spotlight(Gtk.Box):
    def __init__(self, event):
        super(Spotlight, self).__init__()
        user = event.children.get(event[u'actor'])
        self.add(url_to_image(user[u'avatar'], user[u'gravatar']))
        event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if event[u'type'] == "CreateEvent":
            new_type = event[u'payload']['ref_type']
            if new_type == 'repository':
                event_box.add(Gtk.Label("{0} created a new {1}, {2}."
                    .format(user[u'name'], new_type, event[u'repo'])))
            else:
                event_box.add(Gtk.Label("{0} created a new {1} in {2}."
                    .format(user[u'name'], new_type, event[u'repo'])))
            event_box.add(Gtk.Label(event[u'payload']['description']))
        elif event[u'type'] == "IssueCommentEvent":
            event_box.add(Gtk.Label("{0} commented on an issue in {1}."
                .format(user[u'name'], event['repo'])))
            comment = event.children.get(event[u'comment'])
            event_box.add(Gtk.Label(comment[u'body']))
        elif event[u'type'] == "PushEvent":
            event_box.add(Gtk.Label("{0} pushed {1} commit(s) to {2}."
                .format(user[u'name'], len(event[u'payload']['commits']),
                        event[u'repo'])))
            for commit in event[u'payload']['commits']:
                event_box.add(Gtk.Label(commit['message']))
        elif event[u'type'] == "WatchEvent":
            event_box.add(Gtk.Label("{0} is now watching {1}"
                .format(user[u'name'], event[u'repo'])))
        else:
            event_box.add(Gtk.Label(event['type']))
        self.add(event_box)


def url_to_image(url, filename):
    local_path = os.path.join(base_dir, "image_cache", filename)
    if not os.path.exists(local_path):
        urlretrieve(url, local_path)
    img = Gtk.Image.new_from_file(local_path)
    return img


def event_info(event):
    event_name = u'event_{0}'.format(event.id)
    if not Entity.by_name(event_name):
        entity = Entity(event_name)
        actor = user_info(event.actor)
        entity[u'actor'] = actor.name
        entity.append(actor)
        entity[u'repo'] = event.repo.name
        entity[u'type'] = event.type
        entity[u'payload'] = event.payload
        if event.type == "IssueCommentEvent":
            comment = comment_info(event.payload['comment'])
            entity.append(comment)
            entity[u'comment'] = comment.name
        DBSession.add(entity)
    return Entity.by_name(event_name)


def user_info(user):
    user_name = u'user_{0}'.format(user.id)
    if not Entity.by_name(user_name):
        entity = Entity(user_name)
        entity[u'avatar'] = user.avatar_url
        entity[u'gravatar'] = user.gravatar_id
        entity[u'name'] = user.name
        DBSession.add(entity)
    return Entity.by_name(user_name)


def comment_info(comment):
    comment_name = u'comment_{0}'.format(comment['id'])
    if not Entity.by_name(comment_name):
        entity = Entity(comment_name)
        entity[u'body'] = comment['body']
        DBSession.add(entity)
    return Entity.by_name(comment_name)


if __name__ == "__main__":
    win = InfoWin()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    Gtk.main()
