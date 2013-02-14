Infoboard
=========

Infoboard is a simple GTK3 application for watching the activity of members of
a Github organization.

![Example screenshot](doc/images/infoboard.png?raw=true)

Overview
--------

Infoboard consists of two seperate pieces, `infoboard` (the frontend) and
`scraper` (the Github-interfacing backend). Both must be running in order for
the GTK application to get new events, however `infoboard` is not required to
run if another frontend (web, JSON, IRC bot, etc) is desired.

Configuration
-------------

The settings are stored in [settings.yaml](settings.yaml) and should look
something like this:

    user:
    password:
    organization: FOSSRIT
    events: 8
    users: 1
    repositories: 1
    scale: 1
    interval: 360000
    db_uri: sqlite:///knowledge.db

The settings `user` and `password` should be set to your Github
username/password, if desired.  `scraper` can run without this, but it will
only be able to make 60 API calls per hour, and will not see any private
information. `infoboard` does not require this to be set.

`organization` is the Github organization you wish to track. It can be any
Github organization, however you will not necessarily see events from all users
of an organization you are not a part of.

`events`, `users`, and `repositories` determine how the window is populated.
`events` defines the number of events present on the left side of the screen
at any given time. `users` and `repositories` define how many spotlighted
users and repositories (respectively) appear on the right.  These may be
tweaked independently for your device's screen and/or taste.

`scale` also tweaks the display, but this is simply a constant multiplier on
how large gravatars are scaled on the display.

`interval` is the time interval (in seconds) between refreshes of the display
and backend.

`db_uri` is a URI for any database recognized by
[SQLAlchemy](http://www.sqlalchemy.org/).
