import json
from datetime import datetime

import cloudscraper
from bs4 import BeautifulSoup, Tag

from .utils import BASE_URL, get_with_timeout
from .works import Work


class BookmarkNotFound(Exception):
    pass


class PrivateBookmark(Exception):
    pass


class Bookmark(object):
    def __init__(self, id, session=None, ao3_url=BASE_URL):
        self.id = id
        if session is None:
            session = cloudscraper.create_scraper()
        self.session = session
        self.ao3_url = ao3_url

        # Fetch the HTML for this bookmark
        req = get_with_timeout(session, f"{self.ao3_url}/bookmarks/{self.id}")

        if req.status_code == 404:
            raise BookmarkNotFound(f"Unable to find a bookmark with id {self.id!r}")
        elif req.status_code != 200:
            raise RuntimeError(
                f"Unexpected error from AO3 API: {req.text!r} ({req.status_code!r})"
            )

        # Check for private bookmarks, which are only visible to their creator.from
        if "Log in" in req.text:
            raise PrivateBookmark(
                f"Bookmark {self.id} is private. If this is your bookmark, "
                f"log in to access it."
            )
        if (
            "Sorry, you don't have permission to access the page you were trying to "
            "reach" in req.text
        ):
            raise PrivateBookmark(f"Bookmark {self.id} is private.")

        self._html = req.text
        self._soup = BeautifulSoup(self._html, "html.parser")

    def __repr__(self):
        return f"{type(self).__name__}(id={self.id!r})"

    def __eq__(self, other):
        return self.id == other.id

    def __ne__(self, other):
        return not (self == other)

    def __hash__(self):
        return hash(repr(self))

    @property
    def url(self):
        """A URL to this bookmark."""
        return f"{self.ao3_url}/bookmarks/{self.id}"

    @property
    def work_id(self):
        """The id of the bookmarked work"""
        # TODO: handle external bookmarks
        # The link to the work is stored in an <h4> tag of the form
        #
        #   <h4 class="heading">
        #       <a href="/works/[work_id]">[title]</a>
        #       by
        #       <a rel="author" href="/users/[author]">[author]</a>
        #   </h4>
        heading_tag = self._soup.find("h4", attrs={"class": "title"})
        for a_tag in heading_tag.find_all("a"):
            if not hasattr(a, "rel"):
                return a_tag.attrs["href"].replace("/works", "")

    @property
    def work(self):
        return Work(self.work_id, self.session, self.ao3_url)
