import requests
import json


def requests_wrapper(url, auth):
    r = requests.get(url, auth=auth)
    data = json.loads(r.content)
    return data


def organization_members(org_name, auth):
    return requests_wrapper('https://api.github.com/orgs/%s/members' % org_name, auth)


def user_activity(user_name, auth):
    return requests_wrapper('https://api.github.com/users/%s/events' % user_name, auth)


if __name__ == "__main__":
    auth = None
    users = organization_members('FOSSRIT', auth)
    print(users[0]['login'])
    print(user_activity(users[0]['login'], auth))
