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
from knowledge.model import init_model, metadata, Entity
engine = create_engine('sqlite://{0}/knowledge.db'.format(base_dir))
init_model(engine)
metadata.create_all(engine)

# Yes, I know.  I swear there's nothing sketchy in here.
from data import *


class InfoWin(Gtk.Window):
    def __init__(self):
        super(InfoWin, self).__init__()
        self.set_default_size(600, 800)
        self.g = Github()
        print("You have {0} of {1} calls left this hour."
            .format(*self.g.rate_limiting))
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
        user = Entity.by_name(event[u'actor'])
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
        elif event[u'type'] == "ForkEvent":
            event_box.add(Gtk.Label("{0} forked {1} to {2}"
                .format(user[u'name'], event[u'repo'],
                        event[u'payload']['forkee']['full_name'])))
        elif event[u'type'] == "IssueCommentEvent":
            issue = Entity.by_name(event['issue'])
            event_box.add(Gtk.Label("{0} commented on issue #{1} in {2}."
                .format(user[u'name'], issue['number'], event['repo'])))
            comment = Entity.by_name(event[u'comment'])
            event_box.add(Gtk.Label(comment[u'body']))
        elif event[u'type'] == "IssuesEvent":
            issue = Entity.by_name(event['issue'])
            event_box.add(Gtk.Label("{0} {1} issue #{2} in {3}."
                .format(user[u'name'], event['payload']['action'],
                        issue['number'], event['repo'])))
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



if __name__ == "__main__":
    win = InfoWin()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    Gtk.main()
