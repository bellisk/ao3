# -*- encoding: utf-8

import requests

from . import utils
from .comments import Comments
from .users import User
from .works import Work


class AO3(object):
    """A scraper for the Archive of Our Own (AO3)."""

    def __init__(self):
        self.user = None
        self.session = requests.Session()

    # bypasses AO3 login to avoid plaintext credential entry
    # user can input in their current AO3 session ID

    def login(self, username, cookie):
        """Log in to the archive.
        This allows you to access pages that are only available while
        logged in. Does no checking if the cookie is valid.
        The cookie should be the value for _otwarchive_session
        """
        self.user = User(username, cookie)
        self.session = self.user.sess

    def __repr__(self):
        return f"{type(self).__name__}()"

    def work(self, id):
        """Look up a work that's been posted to AO3.
        :param id: the work ID.  In the URL to a work, this is the number.
            e.g. the work ID of https://archiveofourown.org/works/1234 is 1234.
        """
        return Work(id=id, sess=self.session)

    def comments(self, id):
        return Comments(id=id, sess=self.session)

    def users_work_ids(self, username, max_count=0, oldest_date=None):
        url = utils.user_url_from_id(username) + "/works"
        return utils.get_list_of_work_ids(
            url,
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=utils.DATE_UPDATED,
        )

    def series_work_ids(self, series_id, max_count=0, oldest_date=None):
        url = utils.series_url_from_id(series_id)
        return utils.get_list_of_work_ids(
            url,
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=utils.DATE_UPDATED,
        )

    def collection_work_ids(self, collection_id, max_count=0, oldest_date=None):
        url = utils.collection_url_from_id(collection_id) + "/works"
        return utils.get_list_of_work_ids(
            url,
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=utils.DATE_UPDATED,
        )

    def users_works_count(self, username):
        """Returns the number of works by a user across all pseuds"""
        return utils.get_user_works_count(username, self.session)

    def series_info(self, series_id):
        """Returns information about a series"""
        return utils.get_series_info(series_id, self.session)
