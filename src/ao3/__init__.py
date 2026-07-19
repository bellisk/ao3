# -*- encoding: utf-8
from . import utils
from .collections import Collection
from .comments import Comments
from .series import Series
from .sessions import AO3SessionsHandler
from .users import User
from .works import Work


class AO3(object):
    """A scraper for the Archive of Our Own (AO3)."""

    def __init__(
        self, ao3_url=utils.BASE_URL, use_flaresolverr=False, flaresolverr_url=None
    ):
        """Init scraper.

        The url of an AO3 mirror can be passed in, e.g. https://archiveofourown.gay (an
        official mirror run by the OTW). This option is given as a workaround for
        Cloudflare issues that are currently occurring on https://archiveofourown.org.
        """
        self.user = None
        self.session_handler = AO3SessionsHandler(
            ao3_url=ao3_url,
            use_flaresolverr=use_flaresolverr,
            flaresolverr_url=flaresolverr_url,
        )
        self.ao3_url = ao3_url

    def login(self, username, cookie):
        """Log in to the archive.
        This allows you to access pages that are only available while
        logged in. Does no checking if the cookie is valid.
        The cookie should be the value for _otwarchive_session, which can be got from
        the browser when you are logged in there.
        This avoids passing the user's login credentials in plaintext.

        WARNING: passing the user's cookie into a non-official mirror is a security
        risk! Be careful if using an alternate AO3 url.
        """
        self.session_handler.login(cookie)
        self.user = User(username, self.session_handler)

    def __repr__(self):
        return f"{type(self).__name__}()"

    def work(self, id):
        """Look up a work that's been posted to AO3.

        :param id: the work ID.  In the URL to a work, this is the number.
            e.g. the work ID of https://archiveofourown.org/works/1234 is 1234.
        """
        return Work(id=id, session_handler=self.session_handler)

    def comments(self, id):
        """Look up comments on a work that's been posted to AO3.

        :param id: the work ID.  In the URL to a work, this is the number.
            e.g. the work ID of https://archiveofourown.org/works/1234 is 1234.
        """
        return Comments(work_id=id, session_handler=self.session_handler)

    def series(self, id):
        """Look up a series of works posted to AO3.

        :param id: the series ID. In the url to a series, this is the number.
           e.g. the series ID of https://archiveofourown.org/series/1234 is 1234.
        """
        return Series(id=id, session_handler=self.session_handler)

    def collection(self, id):
        """Look up a collection of works posted to AO3.

        :param id: the collection ID, e.g. example_collection in the url
           https://archiveofourown.org/collection/example_collection.
        """
        return Collection(id=id, session_handler=self.session_handler)

    def author(self, username):
        """Look up an AO3 author by username. This method is called 'author' to avoid
        confusion with the logged-in user (self.user).

        :param username: the author's username, e.g. example_user in the url
            https://archiveofourown.org/users/example_user.
        """
        return User(
            username=username,
            session_handler=self.session_handler,
        )
