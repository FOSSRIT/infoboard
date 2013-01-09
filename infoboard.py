#!/usr/bin/env python
# -*- coding: UTF-8 -*-
"""InfoBoard is a Python/GTK3 app for displaying live info about developers"""

import os
import re

from urllib import urlretrieve

from gi.repository import Gtk, GdkPixbuf, Gdk, GObject
from github import Github

# Setup caching
base_dir = os.path.split(__file__)[0]
from sqlalchemy import create_engine
from knowledge.model import init_model, metadata, Entity
engine = create_engine('sqlite://{0}/knowledge.db'.format(base_dir))
init_model(engine)
metadata.create_all(engine)

import yaml
import data


class InfoWin(Gtk.Window):
    def __init__(self, settings):
        super(InfoWin, self).__init__()
        self.set_default_size(800, 800)
        try:
            self.org = g.get_organization(settings['organization'])
            self.max_size = int(settings['events'])
            self.max_repos = int(settings['repositories'])
            self.max_users = int(settings['users'])
            self.scale = float(settings['scale'])
        except KeyError:
            print("Something is wrong with your configuration file.")
            print("Using defaults...")
            self.org = g.get_organization("FOSSRIT")
            self.max_size = 20
            self.max_repos = 3
            self.max_users = 3
            self.scale = .8

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
        GObject.timeout_add(360000, self.refresh)

    def refresh(self):
        events = self.cache_new_events()
        self.add_more_events(events)
        self.add_hilights()

        print("You have {0} of {1} calls left this hour.".format(*g.rate_limiting))
        return True

    def cache_new_events(self):
        """Pull new events from Github and return the [max_size] newest
           events.
        """
        newest_events = data.recent_events(limit=self.max_size)

        try:
            members = self.org.get_members()
            newest_events = filter(lambda event: event['actor'] in members,
                                   newest_events)
        except:
            print('Error getting members')
            return newest_events

        for user in members:
            try:
                user_events = iter(user.get_events())
            except:
                print("Something went wrong updating the events.")
                continue

            limit = self.max_size
            while limit > 0:
                try:
                    event = data.event_info(user_events.next())
                except:
                    # We either ran out of elements early, or hit a problem
                    # pinging Github.  Either way, skip to the next user.
                    continue
                if len(newest_events) > 0 and event[u'created_at'] <= newest_events[0][u'created_at']:
                    break
                newest_events.append(event)
                limit -= 1

        newest_events.sort(key=lambda event: event[u'created_at'], reverse=True)
        size = min(len(newest_events), self.max_size)
        return newest_events[:size]

    def add_more_events(self, new_events):
        """Take the new events and add them to the screen, then remove any
           that are too old.
        """
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

        self.event_box.show_all()

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
        user_name = user[u'name'].encode('utf-8')
        repo = Entity.by_name(event[u'repo'])
        if repo:
            repo_link = '<a href="{0}">{1}</a>'.format(repo['url'], repo['name'])
            repo_desc = repo['description']
        else:
            repo_link = event[u'repo']
            repo_desc = ''

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
                    .format(user_name, target['name'].encode('utf-8')))
            except KeyError:
                event_text.append("{0} is now following {1}."
                    .format(user_name, target['login'].encode('utf-8')))
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
        #PullRequestReviewCommentEvent
        elif event[u'type'] == "PushEvent":
            color = event_colors['commit']
            event_text.append("{0} pushed {1} commit(s) to {2}."
                .format(user_name, event[u'payload']['size'],
                        repo_link))
            for commit in event[u'payload']['commits']:
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
        self.show_all()


class Hilight(Gtk.EventBox):
    def __init__(self, scale):
        super(Hilight, self).__init__()
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(self.box)
        self.scale = scale

    def build_user(self, user_id, user_info):
        user = Entity.by_name(user_id)

        text = ["{0} has been very busy this week!".format(user['name'])]
        for event_type, count in user_info.items():
            if event_type == 'count':
                continue
            elif event_type == 'social actions':
                count = int(count * 10)
            text.append("{0} made {1} {2} this week."
                .format(user['name'], count, event_type))

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
        self.show_all()


# Convenience functions to make Gtk Widgets
def url_to_image(url, filename, scale=1):
    local_path = os.path.join(base_dir, "image_cache", filename)
    if not os.path.exists(local_path):
        urlretrieve(url, local_path)
    # Resize files to 80px x 80px
    pixbuf = GdkPixbuf.Pixbuf.new_from_file(local_path)
    size = scale * 100
    pixbuf = pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)
    img = Gtk.Image.new_from_pixbuf(pixbuf)
    return img


def mk_label(text):
    text = re.sub('<img', '&lt;img', text)
    label = Gtk.Label()
    label.set_markup(text)
    label.set_line_wrap(True)
    return label


if __name__ == "__main__":
    yaml_location = os.path.join(os.path.split(__file__)[0], 'settings.yaml')
    with open(yaml_location) as yaml_file:
        conf = yaml.load(yaml_file)
    g = Github(conf['user'], conf['password'])
    win = InfoWin(conf)
    win.connect("delete-event", Gtk.main_quit)
    win.show_all()

    Gtk.main()
