#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""

import os

from urllib import urlretrieve

from gi.repository import Gtk, GdkPixbuf, Gdk
from github import Github

ORGS = ["FOSSRIT", 'nycapitolcamp']
USERS = ['Qalthos', 'oddshocks', 'rossdylan', 'ryansb', 'ralphbean']

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

        events = set()
        for org in ORGS:
            org = g.get_organization(org)
            events.update(org.get_events()[:25])
        for user in USERS:
            user = g.get_user(user)
            events.update(user.get_events()[:5])

        # There is no set.sort(), so use sorted and overwrite
        events = sorted(events, key=lambda event: event.created_at, reverse=True)

        scrolls = Gtk.ScrolledWindow()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for event in events:
            box.add(Spotlight(event_info(event)))
        scrolls.add_with_viewport(box)
        self.add(scrolls)


class Spotlight(Gtk.EventBox):
    def __init__(self, event):
        super(Spotlight, self).__init__()
        user = Entity.by_name(event[u'actor'])
        box = Gtk.Box()
        box.add(url_to_image(user[u'avatar'], user[u'gravatar']))
        event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if event[u'type'] == "CommitCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            event_box.add(Gtk.Label("{0} commented on a commit in {1}."
                .format(user[u'name'], event['repo'])))
            comment = Entity.by_name(event[u'comment'])
            event_box.add(Gtk.Label(comment[u'body']))
        elif event[u'type'] == "CreateEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            new_type = event[u'payload']['ref_type']
            if new_type == 'repository':
                event_box.add(Gtk.Label("{0} created a new {1}, {2}."
                    .format(user[u'name'], new_type, event[u'repo'])))
            else:
                event_box.add(Gtk.Label("{0} created a new {1} in {2}."
                    .format(user[u'name'], new_type, event[u'repo'])))
            event_box.add(Gtk.Label(event[u'payload']['description']))
    #DeleteEvent
    #DownloadEvent
        elif event[u'type'] == "FollowEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_box.add(Gtk.Label("{0} is now following {1}."
                .format(user[u'name'], event['payload']['target']['name'])))
        elif event[u'type'] == "ForkEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            event_box.add(Gtk.Label("{0} forked {1} to {2}"
                .format(user[u'name'], event[u'repo'],
                        event[u'payload']['forkee']['full_name'])))
    #ForkApplyEvent
        elif event[u'type'] == "GistEvent":
            event_box.add(Gtk.Label("{0} {1}d a gist"
                .format(user[u'name'], event['payload']['action'])))
    #GollumEvent
        elif event[u'type'] == "IssueCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            issue = Entity.by_name(event['issue'])
            event_box.add(Gtk.Label("{0} commented on issue #{1} in {2}."
                .format(user[u'name'], issue['number'], event['repo'])))
            comment = Entity.by_name(event[u'comment'])
            event_box.add(Gtk.Label(issue[u'title']))
            event_box.add(Gtk.Label(comment[u'body']))
        elif event[u'type'] == "IssuesEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            issue = Entity.by_name(event['issue'])
            event_box.add(Gtk.Label("{0} {1} issue #{2} in {3}."
                .format(user[u'name'], event['payload']['action'],
                        issue['number'], event['repo'])))
            event_box.add(Gtk.Label(issue[u'title']))
    #MemberEvent
    #PublicEvent
        elif event[u'type'] == "PullRequestEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            # request = Entity.by_name(event['request'])
            event_box.add(Gtk.Label("{0} {1} pull request #{2} in {3}."
                .format(user[u'name'], event['payload']['action'],
                        event['payload']['number'], event['repo'])))
    #PullRequestReviewCommentEvent
        elif event[u'type'] == "PushEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C9FFC1"))
            event_box.add(Gtk.Label("{0} pushed {1} commit(s) to {2}."
                .format(user[u'name'], len(event[u'payload']['commits']),
                        event[u'repo'])))
            for commit in event[u'payload']['commits']:
                event_box.add(Gtk.Label(commit['message']))
    #TeamAddEvent
        elif event[u'type'] == "WatchEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_box.add(Gtk.Label("{0} is now watching {1}"
                .format(user[u'name'], event[u'repo'])))
        else:
            event_box.add(Gtk.Label(event['type']))
        event_box.add(Gtk.Label(event.name))
        box.add(event_box)
        self.add(box)


def url_to_image(url, filename):
    local_path = os.path.join(base_dir, "image_cache", filename)
    if not os.path.exists(local_path):
        urlretrieve(url, local_path)
    # Resize files to 80px x 80px
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(local_path)
    pixbuf = pixbuf.scale_simple(80, 80, GdkPixbuf.InterpType.BILINEAR)
    img = Gtk.Image.new_from_pixbuf(pixbuf)
    return img


if __name__ == "__main__":
    g = Github()
    print("You have {0} of {1} calls left this hour.".format(*g.rate_limiting))
    win = InfoWin()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    Gtk.main()
