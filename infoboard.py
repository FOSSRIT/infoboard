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

        # Container for hilights... vertically down the right
        hilights = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                           homogeneous=True)
        top_user, top_repo = data.top_contributions()

        # Top user box
        if top_user:
            user = Hilight()
            try:
                user.build_user(top_user)
                hilights.pack_start(user, True, False, 0)
            except:
                pass

        # Top project box
        if top_repo:
            repo = Hilight()
            try:
                repo.build_repo(top_repo)
                hilights.pack_start(repo, True, False, 0)
            except:
                pass

        super_box.add(hilights)

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
        try:
            for user in org.get_members():
                user_events = iter(user.get_events())
                limit = 5
                try:
                    while limit > 0:
                        event = data.event_info(user_events.next())
                        if extant_events and event[u'created_at'] < extant_events[0][u'created_at']:
                            break
                        new_events.add(event)
                        limit -= 1
                except StopIteration:
                    # We ran out of items to add. Oh well.
                    pass
        except:
            print("Something went wrong updating the events.")

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

        self.box.pack_start(url_to_image(user[u'avatar'], user[u'gravatar']),
                            False, False, 10)

        event_text = []
        if event[u'type'] == "CommitCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            event_text.append("{0} commented on a commit in {1}."
                .format(user_name, repo_link))
            comment = Entity.by_name(event[u'comment'])
            event_text.append(comment[u'body'])
        elif event[u'type'] == "CreateEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            new_type = event[u'payload']['ref_type']
            if new_type == 'repository':
                event_text.append("{0} created a new {1}, {2}."
                    .format(user_name, new_type, repo_link))
            else:
                event_text.append("{0} created {1} {3} in {2}."
                    .format(user_name, new_type, repo_link,
                            event[u'payload']['ref']))
            event_text.append(event[u'payload']['description'])
        elif event[u'type'] == "DeleteEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            new_type = event[u'payload']['ref_type']
            event_text.append("{0} deleted {1} {3} in {2}."
                .format(user_name, new_type, repo_link,
                        event[u'payload']['ref']))
        #DownloadEvent
        elif event[u'type'] == "FollowEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_text.append("{0} is now following {1}."
                .format(user_name,
                        event['payload']['target']['name'].encode('utf-8')))
        elif event[u'type'] == "ForkEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C2C9FF"))
            try:
                event_text.append("{0} forked {1} to {2}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['full_name']))
            except KeyError:
                event_text.append("{0} forked {1} to {2}/{3}."
                    .format(user_name, repo_link,
                            event[u'payload']['forkee']['owner']['login'],
                            event[u'payload']['forkee']['name']))
        #ForkApplyEvent
        elif event[u'type'] == "GistEvent":
            event_text.append("{0} {1}d a gist"
                .format(user_name, event['payload']['action']))
        #GollumEvent
        elif event[u'type'] == "IssueCommentEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFDDBD"))
            issue = Entity.by_name(event['issue'])
            event_text.append("{0} commented on issue #{1} in {2}."
                .format(user_name, issue['number'], repo_link))
            comment = Entity.by_name(event[u'comment'])
            event_text.append(issue[u'title'])
            event_text.append(comment[u'body'])
        elif event[u'type'] == "IssuesEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            issue = Entity.by_name(event['issue'])
            event_text.append("{0} {1} issue #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        issue['number'], repo_link))
            event_text.append(issue[u'title'])
        elif event[u'type'] == "MemberEvent":
            #self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#??????"))
            try:
                event_text.append("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['name'],
                            repo_link))
            except KeyError:
                event_text.append("{0} added {1} as a collaborator to {2}."
                    .format(user_name, event['payload']['member']['login'],
                            repo_link))
        #PublicEvent
        elif event[u'type'] == "PullRequestEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFBAF9"))
            # request = Entity.by_name(event['request'])
            event_text.append("{0} {1} pull request #{2} in {3}."
                .format(user_name, event['payload']['action'],
                        event['payload']['number'], repo_link))
        #PullRequestReviewCommentEvent
        elif event[u'type'] == "PushEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#C9FFC1"))
            event_text.append("{0} pushed {1} commit(s) to {2}."
                .format(user_name, len(event[u'payload']['commits']),
                        repo_link))
            for commit in event[u'payload']['commits']:
                event_text.append(commit['message'])
        #TeamAddEvent
        elif event[u'type'] == "WatchEvent":
            self.modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse("#FFFF80"))
            event_text.append("{0} is now watching {1}"
                .format(user_name, repo_link))
        else:
            event_text.append(event['type'])
        event_label = mk_label('\n'.join(event_text))
        self.box.pack_start(event_label, False, False, 0)
        self.show_all()


class Hilight(Gtk.EventBox):
    def __init__(self):
        super(Hilight, self).__init__()

    def build_user(self, user_stats):
        top_user = sorted(user_stats,
                          key=lambda user: user_stats[user]['count'],
                          reverse=True)
        top_user = None if len(top_user) == 0 else top_user[0]
        if not top_user:
            return
        user = Entity.by_name(top_user)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add(url_to_image(user['avatar'], user['gravatar']))
        text = ["{0} has been very busy this week!".format(user['name'])]
        for event_type, count in user_stats[top_user].items():
            if event_type == 'count':
                continue
            text.append("{0} made {1} {2} this week."
                .format(user['name'], count, event_type))
        box.add(mk_label('\n'.join(text)))
        self.add(box)
        self.show_all()

    def build_repo(self, repo_stats):
        top_repo = sorted(repo_stats,
                          key=lambda repo: repo_stats[repo]['count'],
                          reverse=True)
        top_repo = None if len(top_repo) == 0 else top_repo[0]
        if not top_repo:
            return
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        repo = Entity.by_name(top_repo)
        try:
            owner = Entity.by_name(repo['owner'])

            box.add(url_to_image(owner['avatar'], owner['gravatar']))
        except:
            pass
        text = ["{0} is a cool project!".format(repo['name'])]
        for user, count in repo_stats[top_repo].items():
            if user == 'count':
                continue
            text.append("{0} made {1} contributions this week."
                .format(Entity.by_name(user)['name'], count))
        box.add(mk_label('\n'.join(text)))
        self.add(box)
        self.show_all()


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
