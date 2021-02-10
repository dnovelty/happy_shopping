import json
from http.cookiejar import LWPCookieJar

import requests


def callback_2_json(s):
    begin = s.find('{')
    end = s.rfind('}') + 1
    return json.loads(s[begin:end])


def status_ok(resp):
    return resp.status == requests.codes.OK
