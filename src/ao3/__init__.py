# -*- encoding: utf-8
from urllib.parse import urlparse

import cloudscraper
import requests

from . import utils
from .comments import Comments
from .series import Series
from .users import User
from .works import Work


class AO3(object):
    """A scraper for the Archive of Our Own (AO3)."""

    def __init__(self):
        self.user = None
        self.session = cloudscraper.create_scraper()
        self.ao3_url = utils.BASE_URL

        #
    # bypasses AO3 login to avoid plaintext credential entry
    # user can input in their current AO3 session ID

    def login(self, username, cookie, ao3_url=utils.BASE_URL):
        """Log in to the archive.
        This allows you to access pages that are only available while
        logged in. Does no checking if the cookie is valid.
        The cookie should be the value for _otwarchive_session.

        The url of an AO3 mirror can be passed in, e.g. https://archiveofourown.gay (an
        official mirror run by the OTW).

        WARNING: passing the user's cookie into a non-official mirror is a security
        risk!
        This option is given as a workaround for Cloudflare issues that
        are currently occurring on https://archiveofourown.org.
        """
        session = cloudscraper.create_scraper()

        jar = requests.cookies.RequestsCookieJar()
        ao3_domain = urlparse(self.ao3_url).netloc
        # must be done separately bc the set func returns a cookie, not a jar
        jar.set("_otwarchive_session", cookie, domain=ao3_domain)
        # AO3 requires this cookie to be set
        jar.set("user_credentials", "1", domain=ao3_domain)
        session.cookies = jar

        self.session = session
        self.user = User(username, session, ao3_url)

    def __repr__(self):
        return f"{type(self).__name__}()"

    def work(self, id):
        """Look up a work that's been posted to AO3.
        :param id: the work ID.  In the URL to a work, this is the number.
            e.g. the work ID of https://archiveofourown.org/works/1234 is 1234.
        """
        return Work(id=id, sess=self.session, ao3_url=self.ao3_url)

    def comments(self, id):
        return Comments(id=id, sess=self.session, ao3_url=self.ao3_url)

    def series(self, id):
        """Look up a series of works posted to AO3.

        :param id: the series ID. In the url to a series, this is the number.
           e.g. the series ID of https://archiveofourown.org/series/1234 is 1234.
        """
        return Series(series_id=id, session=self.session, ao3_url=self.ao3_url)

    def author(self, username):
        """Look up an AO3 author by username. This method is called 'author' to avoid
        confusion with the logged-in user (self.user).

        :param username: the author's username, e.g. example_user in the url
            https://archiveofourown.org/users/example_user.
        """
        return User(username=username, session=self.session, ao3_url=self.ao3_url)

    def collection_work_ids(self, collection_id, max_count=0, oldest_date=None):
        url = utils.collection_url_from_id(collection_id) + "/works"
        return utils.get_list_of_work_ids(
            url,
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=utils.DATE_UPDATED,
        )
