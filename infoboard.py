#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""

import os

from urllib import urlretrieve

from gi.repository import Gtk
from github import Github

ORG = "FOSSRIT"

base_dir = os.path.split(__file__)[0]


class InfoWin(Gtk.Window):
    def __init__(self):
        super(InfoWin, self).__init__()
        self.set_default_size(600, 800)
        self.g = Github()
        self.org = self.g.get_organization(ORG)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        latest_events = self.org.get_events()[:10]
        for event in latest_events:
            box.add(Spotlight(event))
        self.add(box)


class Spotlight(Gtk.Box):
    def __init__(self, event):
        super(Spotlight, self).__init__()
        user = event.actor
        self.add(url_to_image(user.avatar_url, user.gravatar_id))
        event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        if event.type == "CreateEvent":
            event_box.add(Gtk.Label("{0} created a new {1}."
                .format(user.name, event.payload['ref_type'])))
            event_box.add(Gtk.Label(event.payload['description']))
        elif event.type == "IssueCommentEvent":
            event_box.add(Gtk.Label("{0} commented on an issue."
                .format(user.name)))
            event_box.add(Gtk.Label(event.payload['comment']['body']))
        elif event.type == "PushEvent":
            event_box.add(Gtk.Label("{0} pushed {1} commits."
                .format(user.name, len(event.payload['commits']))))
            for commit in event.payload['commits']:
                event_box.add(Gtk.Label(commit['message']))
        else:
            event_box.add(Gtk.Label(event.type))
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
