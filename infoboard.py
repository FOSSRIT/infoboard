#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""

import os

from urllib import urlretrieve

from gi.repository import Gtk, GdkPixbuf, Gdk, GObject
from github import Github

ORG = 'FOSSRIT'

# Setup caching
base_dir = os.path.split(__file__)[0]
from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity
engine = create_engine('sqlite://{0}/knowledge.db'.format(base_dir))
init_model(engine)
metadata.create_all(engine)

import data


class InfoWin(Gtk.Window):
    def __init__(self):
        super(InfoWin, self).__init__()
        self.max_size = 20
        self.set_default_size(600, 800)

        scrolls = Gtk.ScrolledWindow()
        super_box = Gtk.Box(homogeneous=True)

        # Container for events... goes vertically down the left
        self.event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        super_box.add(self.event_box)

        scrolls.add_with_viewport(super_box)
        self.add(scrolls)
        self.add_more_events(data.recent_events())
        GObject.timeout_add(360000, self.add_more_events)

    def add_more_events(self, initial=None):
        extant_events = map(lambda spot: spot.event, self.event_box.get_children())
        if initial:
            new_events = set(initial)
        else:
            new_events = set()
        org = g.get_organization(ORG)
        for user in org.get_members():
            try:
                eventities = map(data.event_info, user.get_events()[:5])
            except IndexError:
                eventities = map(data.event_info, user.get_events())
            new_events.update(eventities)

        # Remove any events already onscreen
        new_events.difference_update(set(extant_events))
        # There is no set.sort(), so use sorted and overwrite
        new_events = sorted(new_events, key=lambda event: event[u'created_at'], reverse=True)

        # Remove all the uninteresting events
        blacklist = ['DownloadEvent']
        new_events = filter(lambda event: event[u'type'] not in blacklist, new_events)

        # Don't try to add more events than we have.
        size = min(len(new_events), self.max_size)
        for event in reversed(new_events[:size]):
            # Don't use this as an excuse to pop old events to the top of the
            # list.
            if extant_events and event[u'created_at'] < extant_events[0][u'created_at']:
                continue
            spot_box = EventWidget()
            try:
                spot_box.populate(event)
                self.event_box.pack_end(spot_box, True, False, 2)
            except:
                pass
        self.event_box.show_all()

        print("You have {0} of {1} calls left this hour.".format(*g.rate_limiting))
        return True


class EventWidget(Gtk.EventBox):
    def __init__(self):
        super(EventWidget, self).__init__()
        self.box = Gtk.Box()
        self.add(self.box)

    def populate(self, event):
        self.event = event
        user = Entity.by_name(event[u'actor'])
        user_name = user[u'name'].encode('utf-8')
        repo = Entity.by_name(event[u'repo'])
        if repo:
            repo_link = '<a href="{0}">{1}</a>'.format(repo['url'], repo['name'])
        else:
            repo_link = event[u'repo']

        self.box.add(url_to_image(user[u'avatar'], user[u'gravatar']))

        event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if event[u'type'] == "CommitCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            event_box.add(mk_label("{0} commented on a commit in {1}."
                .format(user_name, repo_link)))
            comment = Entity.by_name(event[u'comment'])
            event_box.add(mk_label(comment[u'body']))
        elif event[u'type'] == "CreateEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            new_type = event[u'payload']['ref_type']
            if new_type == 'repository':
                event_box.add(mk_label("{0} created a new {1}, {2}."
                    .format(user_name, new_type, repo_link)))
            else:
                event_box.add(mk_label("{0} created a new {1} in {2}."
                    .format(user_name, new_type, repo_link)))
            event_box.add(mk_label(event[u'payload']['description']))
        elif event[u'type'] == "DeleteEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            new_type = event[u'payload']['ref_type']
            event_box.add(mk_label("{0} deleted a {1} in {2}."
                .format(user_name, new_type, repo_link)))
        #DownloadEvent
        elif event[u'type'] == "FollowEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_box.add(mk_label("{0} is now following {1}."
                .format(user_name,
                        event['payload']['target']['name'].encode('utf-8'))))
        elif event[u'type'] == "ForkEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            try:
                event_box.add(mk_label("{0} forked {1} to {2}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['full_name'])))
            except KeyError:
                event_box.add(mk_label("{0} forked {1} to {2}/{3}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['owner']['login'],
                            event[u'payload']['forkee']['name'])))
        #ForkApplyEvent
        elif event[u'type'] == "GistEvent":
            event_box.add(mk_label("{0} {1}d a gist"
                .format(user_name, event['payload']['action'])))
        #GollumEvent
        elif event[u'type'] == "IssueCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            issue = Entity.by_name(event['issue'])
            event_box.add(mk_label("{0} commented on issue #{1} in {2}."
                .format(user_name, issue['number'], repo_link)))
            comment = Entity.by_name(event[u'comment'])
            event_box.add(mk_label(issue[u'title']))
            event_box.add(mk_label(comment[u'body']))
        elif event[u'type'] == "IssuesEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            issue = Entity.by_name(event['issue'])
            event_box.add(mk_label("{0} {1} issue #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        issue['number'], repo_link)))
            event_box.add(mk_label(issue[u'title']))
        elif event[u'type'] == "MemberEvent":
            #self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#??????"))
            try:
                event_box.add(mk_label("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['name'],
                            repo_link)))
            except KeyError:
                event_box.add(mk_label("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['login'],
                            repo_link)))
        #PublicEvent
        elif event[u'type'] == "PullRequestEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            # request = Entity.by_name(event['request'])
            event_box.add(mk_label("{0} {1} pull request #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        event['payload']['number'], repo_link)))
        #PullRequestReviewCommentEvent
        elif event[u'type'] == "PushEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C9FFC1"))
            event_box.add(mk_label("{0} pushed {1} commit(s) to {2}."
                .format(user_name, len(event[u'payload']['commits']),
                        repo_link)))
            for commit in event[u'payload']['commits']:
                event_box.add(mk_label(commit['message']))
        #TeamAddEvent
        elif event[u'type'] == "WatchEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_box.add(mk_label("{0} is now watching {1}"
                .format(user_name, repo_link)))
        else:
            event_box.add(mk_label(event['type']))
        self.box.pack_end(event_box, False, False, 0)


def url_to_image(url, filename):
    local_path = os.path.join(base_dir, "image_cache", filename)
    if not os.path.exists(local_path):
        urlretrieve(url, local_path)
    # Resize files to 80px x 80px
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(local_path)
    pixbuf = pixbuf.scale_simple(80, 80, GdkPixbuf.InterpType.BILINEAR)
    img = Gtk.Image.new_from_pixbuf(pixbuf)
    return img


def mk_label(text):
    label = Gtk.Label()
    label.set_markup(text)
    label.set_line_wrap(True)
    return label


if __name__ == "__main__":
    g = Github()
    win = InfoWin()
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    Gtk.main()
