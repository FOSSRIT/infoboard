#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""
from __future__ import print_function, unicode_literals

import os
import re

import requests

from gi.repository import Gtk, GdkPixbuf, Gdk, GObject

# Setup caching
base_dir = os.path.split(__file__)[0]
from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity

import yaml
import data


class InfoWin(Gtk.Window):
    def __init__(self, settings):
        super(InfoWin, self).__init__()
        self.maximize()
        try:
            client = settings['client']
            common = settings['common']

            self.max_size = int(client['events'])
            self.max_repos = int(client['repositories'])
            self.max_users = int(client['users'])
            self.scale = float(client['scale'])

            self.org = common['organization']
            self.reload_interval = int(common['interval'])
        except KeyError:
            print("Something is wrong with your configuration file.")
            print("Using defaults...")
            self.org = "FOSSRIT"
            self.max_size = 20
            self.max_repos = 3
            self.max_users = 3
            self.scale = .8
            self.reload_interval = 360

        scrolls = Gtk.ScrolledWindow()
        super_box = Gtk.Box(homogeneous=True)

        # Container for events... goes vertically down the left
        self.event_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        super_box.add(self.event_box)

        # Container for hilights... vertically down the right
        self.hilights = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                homogeneous=True)
        super_box.add(self.hilights)

        scrolls.add_with_viewport(super_box)
        self.add(scrolls)
        self.refresh()
        GObject.timeout_add(self.reload_interval * 1000, self.refresh)

    def refresh(self):
        self.add_more_events()
        self.add_hilights()
        self.show_all()
        print("Refresh completed")
        return True

    def add_more_events(self):
        """Take the new events and add them to the screen, then remove any
           that are too old.
        """
        # Check the DB for events
        new_events = data.recent_events(limit=self.max_size)

        # Get what's on the screen and remove them from the update queue
        extant_events = map(lambda spot: spot.event, self.event_box.get_children())
        new_events = filter(lambda event: event not in extant_events, new_events)

        # Remove all the uninteresting events
        blacklist = ['DownloadEvent']
        new_events = filter(lambda event: event[u'type'] not in blacklist, new_events)

        # Add events to the top, starting from the oldest.
        for event in reversed(new_events):
            spot_box = EventWidget(self.scale)
            spot_box.populate(event)
            self.event_box.pack_end(spot_box, False, False, 2)

        # Reduce the list back down to [max_size]
        if len(new_events) + len(extant_events) > self.max_size:
            for event_widget in self.event_box.get_children()[self.max_size:]:
                self.event_box.remove(event_widget)

    def add_hilights(self):
        top_users, top_repos = data.top_contributions()
        self.hilights.foreach(lambda widget, _: self.hilights.remove(widget), None)

        sorted_users = sorted(top_users,
                              key=lambda user: top_users[user]['count'],
                              reverse=True)
        for index in range(self.max_users):
            if len(top_users) > index:
                # Top user box
                user_id = sorted_users[index]
                user = Hilight(2*self.scale)
                user.build_user(user_id, top_users[user_id])
                self.hilights.pack_start(user, True, False, 0)

        sorted_repos = sorted(top_repos,
                              key=lambda repo: top_repos[repo]['count'],
                              reverse=True)
        for index in range(self.max_repos):
            if len(top_repos) > index:
                # Top project box
                repo_id = sorted_repos[index]
                repo = Hilight(2*self.scale)
                repo.build_repo(repo_id, top_repos[repo_id])
                self.hilights.pack_start(repo, True, False, 0)


class EventWidget(Gtk.EventBox):
    def __init__(self, scale):
        super(EventWidget, self).__init__()
        self.box = Gtk.Box()
        self.add(self.box)
        self.scale = scale

    def populate(self, event):
        self.event = event
        user = Entity.by_name(event[u'actor'])
        user_name = user[u'name']
        repo = event[u'repo']

        if not Entity.by_name(repo):
            repo_link = event[u'repo']
            repo_desc = ''
        else:
            repo = Entity.by_name(repo)
            repo_link = '<a href="{0}">{1}</a>'.format(repo['url'], repo['name'])
            repo_desc = repo['description']

        self.box.pack_start(url_to_image(user[u'avatar'], user[u'gravatar'], self.scale),
                            False, False, 10)

        event_colors = {
            'commit': "#C9FFC1",
            'branch': "#C2C9FF",
            'issue': "#FFBAF9",
            'comment': "#FFDDBD",
            'social': "#FFFF80",
        }
        event_text = []
        color = "#FFFFFF"
        if event[u'type'] == "CommitCommentEvent":
            color = event_colors['comment']
            event_text.append("{0} commented on a commit in {1}."
                .format(user_name, repo_link))
            comment = Entity.by_name(event[u'comment'])
            event_text.append(comment[u'body'])
        elif event[u'type'] == "CreateEvent":
            color = event_colors['branch']
            new_type = event[u'payload']['ref_type']
            if new_type == 'repository':
                event_text.append("{0} created a new {1}, {2}."
                    .format(user_name, new_type, repo_link))
            else:
                event_text.append("{0} created {1} <tt>{3}</tt> in {2}."
                    .format(user_name, new_type, repo_link,
                            event[u'payload']['ref']))
            event_text.append(repo_desc)
        elif event[u'type'] == "DeleteEvent":
            color = event_colors['branch']
            new_type = event[u'payload']['ref_type']
            event_text.append("{0} deleted {1} <tt>{3}</tt> in {2}."
                .format(user_name, new_type, repo_link,
                        event[u'payload']['ref']))
        #DownloadEvent
        elif event[u'type'] == "FollowEvent":
            color = event_colors['social']
            target = event['payload']['target']
            try:
                event_text.append("{0} is now following {1}."
                    .format(user_name, target['name']))
            except KeyError:
                event_text.append("{0} is now following {1}."
                    .format(user_name, target['login']))
        elif event[u'type'] == "ForkEvent":
            color = event_colors['branch']
            try:
                event_text.append("{0} forked {1} to {2}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['full_name']))
            except KeyError:
                event_text.append("{0} forked {1} to {2}/{3}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['owner']['login'],
                            event[u'payload']['forkee']['name']))
            event_text.append(repo_desc)
        #ForkApplyEvent
        elif event[u'type'] == "GistEvent":
            event_text.append("{0} {1}d a gist"
                .format(user_name, event['payload']['action']))
        elif event[u'type'] == "GollumEvent":
            event_text.append("{0} updated {2} wiki pages in {1}."
                              .format(user_name, repo_link,
                                      len(event['payload']['pages'])))
            for page in event['payload']['pages']:
                event_text.append(page['title'])
        elif event[u'type'] == "IssueCommentEvent":
            color = event_colors['comment']
            issue = Entity.by_name(event['issue'])
            event_text.append("{0} commented on issue #{1} in {2}."
                .format(user_name, issue['number'], repo_link))
            comment = Entity.by_name(event[u'comment'])
            event_text.append(issue[u'title'])
            event_text.append(comment[u'body'])
        elif event[u'type'] == "IssuesEvent":
            color = event_colors['issue']
            issue = Entity.by_name(event['issue'])
            event_text.append("{0} {1} issue #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        issue['number'], repo_link))
            event_text.append(issue[u'title'])
        elif event[u'type'] == "MemberEvent":
            color = event_colors['social']
            try:
                event_text.append("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['name'],
                            repo_link))
            except KeyError:
                event_text.append("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['login'],
                            repo_link))
            event_text.append(repo_desc)
        elif event[u'type'] == "PublicEvent":
            event_text.append("{0} made {1} public."
                              .format(user_name, repo_link))
            event_text.append(repo_desc)
        elif event[u'type'] == "PullRequestEvent":
            color = event_colors['issue']
            # request = Entity.by_name(event['request'])
            event_text.append("{0} {1} pull request #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        event['payload']['number'], repo_link))
        elif event['type'] == 'PullRequestReviewCommentEvent':
            color = event_colors['social']
            event_text.append("{0} commented on an issue in {1}."
                              .format(user_name, repo_link))
            comment = Entity.by_name(event['comment'])
            event_text.append(comment['body'])
        elif event[u'type'] == "PushEvent":
            color = event_colors['commit']
            commits = filter(lambda x: x['distinct'], event[u'payload']['commits'])
            event_text.append("{0} pushed {1} commit(s) to {2}."
                .format(user_name, len(commits), repo_link))
            for commit in commits:
                event_text.append(u'• ' + commit['message'])
        #TeamAddEvent
        elif event[u'type'] == "WatchEvent":
            color = event_colors['social']
            event_text.append("{0} is now watching {1}"
                .format(user_name, repo_link))
            event_text.append(repo_desc)
        else:
            event_text.append(event['type'])

        self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(color))
        event_label = mk_label('\n'.join(event_text))
        self.box.pack_start(event_label, False, False, 0)


class Hilight(Gtk.EventBox):
    def __init__(self, scale):
        super(Hilight, self).__init__()
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)
        self.scale = scale

    def build_user(self, user_id, user_info):
        user = Entity.by_name(user_id)
        display_key = {
            'CommitCommentEvent': ('commented on', 'commits'),
            'CreateEvent': ('created', 'tags, branches, or repositories'),
            'DeleteEvent': ('deleted', 'tags, branches, or repositories'),
            # DownloadEvent
            'FollowEvent': ('followed', 'users'),
            'ForkEvent': ('forked', 'repositories'),
            'ForkApplyEvent': ('applied', 'patches'),
            'GistEvent': ('made or modified', 'gists'),
            'GollumEvent': ('made or modified', 'wiki pages'),
            'IssueCommentEvent': ('commented on', 'issues'),
            'IssuesEvent': ('made or modified', 'issues'),
            'MemberEvent': ('added', 'collaborators'),
            'PublicEvent': ('opened', 'repositories'),
            'PullRequestEvent': ('made or modified', 'pull requests'),
            'PullRequestReviewCommentEvent': ('commented on', 'pull requests'),
            'PushEvent': ('pushed', 'commits'),
            'TeamAddEvent': ('added', 'users to teams'),
            'WatchEvent': ('watched', 'repositories'),
        }

        text = ["{0} has been very busy this week!".format(user['name'])]
        for event_type, count in user_info.items():
            if event_type == 'count':
                continue
            elif event_type in ['CommitCommentEvent', 'FollowEvent',
                                'IssueCommentEvent', 'WatchEvent',
                                'PullRequestReviewCommentEvent',]:
                count = int(count * 10)
            display_text = display_key.get(event_type, ('made', event_type))
            text.append("{0} {1[0]} {2} {1[1]} this week."
                .format(user['name'], display_text, count, event_type))

        self.finish(user, text)

    def build_repo(self, repo_id, repo_info):
        repo = Entity.by_name(repo_id)
        owner = Entity.by_name(repo['owner'])

        text = ["{0} is a cool project!".format(repo['name'])]
        for user, count in repo_info.items():
            if user == 'count':
                continue
            text.append("{0} made {1} contributions this week."
                .format(Entity.by_name(user)['name'], count))

        self.finish(owner, text)

    def finish(self, user, text):
        if user:
            self.box.add(url_to_image(user['avatar'], user['gravatar'], self.scale))
        self.box.add(mk_label('\n'.join(text)))


# Convenience functions to make Gtk Widgets
def url_to_image(url, filename, scale=1):
    local_path = os.path.join(base_dir, "image_cache", filename)
    if not os.path.exists(local_path):
        r = requests.get(url)
        with open(local_path, 'w') as image_file:
            image_file.write(r.content)
    # Scale images to the desired size
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(local_path)
    size = scale * 100
    pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    img = Gtk.Image.new_from_pixbuf(pixbuf)
    return img


def mk_label(text):
    label = Gtk.Label()
    label.set_markup(text)
    label.set_line_wrap(True)
    return label


if __name__ == "__main__":
    # Load conf file
    yaml_location = os.path.join(os.path.split(__file__)[0], 'settings.yaml')
    with open(yaml_location) as yaml_file:
        conf = yaml.load(yaml_file)

    # Set up Knowledge
    engine = create_engine(conf['common']['db_uri'])
    init_model(engine)
    metadata.create_all(engine)

    win = InfoWin(conf)
    win.connect("delete-event", Gtk.main_quit)

    Gtk.main()
