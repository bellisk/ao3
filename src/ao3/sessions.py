import json
import time
from urllib.parse import urlparse

import requests
from requests import Response

DEFAULT_AO3_URL = "https://archiveofourown.org"
DEFAULT_FLARESOLVERR_PROXY_URL = "http://localhost:8191/v1"


class AO3SessionsHandler(object):
    def __init__(
        self,
        ao3_url=DEFAULT_AO3_URL,
        use_flaresolverr=False,
        flaresolverr_url=None,
    ):
        self.cookies = None
        self.ao3_url = ao3_url
        self.use_flaresolverr = use_flaresolverr

        self.requests_session = requests.session()

        if self.use_flaresolverr:
            if flaresolverr_url is not None:
                self.flaresolverr_url = flaresolverr_url
            else:
                self.flaresolverr_url = DEFAULT_FLARESOLVERR_PROXY_URL

            # Create FlareSolverr session
            headers = {"Content-Type": "application/json"}
            data = {"cmd": "sessions.create"}
            response = self.requests_session.post(
                self.flaresolverr_url, headers=headers, json=data
            )
            response.raise_for_status()
            response_json = json.loads(response.text)

            if response_json.get("status") != "ok":
                raise RuntimeError(
                    f"Error creating FlareSolverr session: {response_json['message']}"
                )

            self.flaresolverr_session_id = response_json["session"]
            print(
                f"Created FlareSolverr session with id {self.flaresolverr_session_id}"
            )

    def login(self, cookie):
        if self.use_flaresolverr:
            self.cookies = [
                {
                    "name": "_otwarchive_session",
                    "value": cookie,
                },
                {
                    "name": "user_credentials",
                    "value": "1",
                },
            ]
        else:
            jar = requests.cookies.RequestsCookieJar()
            ao3_domain = urlparse(self.ao3_url).netloc
            jar.set("_otwarchive_session", cookie, domain=ao3_domain)
            jar.set("user_credentials", "1", domain=ao3_domain)
            self.requests_session.cookies = jar

    def end_session(self):
        if self.use_flaresolverr:
            # Destroy FlareSolverr session
            headers = {"Content-Type": "application/json"}
            data = {"cmd": "sessions.destroy", "session": self.flaresolverr_session_id}
            response = self.requests_session.post(
                self.flaresolverr_url, headers=headers, json=data
            )
            response.raise_for_status()
            response_json = json.loads(response.text)

            if response_json.get("status") != "ok":
                raise RuntimeError(
                    f"Error destroying FlareSolverr session: {response_json['message']}"
                )
        self.requests_session.close()

    def get(self, path):
        """Get the path at the set ao3_url, using FlareSolverr if it is configured.

        :param path: a path starting with /, e.g. /users/my-username or /works/12345
        :return:
        """
        if self.use_flaresolverr:
            headers = {"Content-Type": "application/json"}
            data = {
                "cmd": "request.get",
                "url": self.ao3_url + path,
                "cookies": self.cookies,
            }
            return self.requests_session.post(
                self.flaresolverr_url, headers=headers, json=data
            )

        return self.requests_session.get(self.ao3_url + path)

    def get_with_timeout(self, path):
        # Enforce pause between requests
        time.sleep(5)

        # if timeout, wait and try again
        while True:
            response = self.get(path)
            if response.status_code == 200:
                break
            elif response.status_code == 503:
                print("Got error 503... waiting 10 seconds and trying again")
                time.sleep(10)
            elif response.status_code == 525:
                print("Got Cloudflare error 525... waiting 10 seconds and trying again")
                time.sleep(10)
            elif len(response.text) < 20 and "Retry later" in response.text:
                print("Timeout... waiting 3 mins and trying again")
                time.sleep(180)
            else:
                raise RuntimeError(
                    f"Error getting url {path}: "
                    f"{response.status_code}, {response.reason}"
                )

        return response
