# -*- encoding: utf-8
"""Utility functions."""

import itertools
import re
import time
from datetime import datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

# Regex for extracting the work ID from an AO3 URL.  Designed to match URLs
# of the form
#
#     https://archiveofourown.org/works/1234567
#     http://archiveofourown.org/works/1234567
#
WORK_URL_REGEX = re.compile(
    r"^https?://archiveofourown.org/works/" r"(?P<work_id>[0-9]+)"
)

LAST_VISITED_REGEX = re.compile("Last visited: ([0-9]{2} [a-zA-Z]{3} [0-9]{4})")

TYPE_WORKS = "works"
TYPE_SERIES = "series"
TYPE_USERS = "users"
AO3_DATE_FORMAT = "%d %b %Y"
DATE_UPDATED = "updated"
DATE_INTERACTED_WITH = "interacted"


def work_id_from_url(url):
    """Given an AO3 URL, return the work ID."""
    match = WORK_URL_REGEX.match(url)
    if match:
        return match.group("work_id")
    else:
        raise RuntimeError("%r is not a recognised AO3 work URL")


def work_url_from_id(work_id):
    return "https://archiveofourown.org/works/%s" % work_id


def series_url_from_id(series_id):
    return "https://archiveofourown.org/series/%s" % series_id


def user_url_from_id(user_id):
    return "https://archiveofourown.org/users/%s" % user_id


def get_list_of_work_ids(
    list_url,
    session,
    max_count=None,
    expand_series=False,
    oldest_date=None,
    date_type="",
):
    """
    Returns a list of work ids from a paginated list.
    Ignores external work bookmarks.
    User must be logged in to see private bookmarks.
    If expand_series=True, all works in a bookmarked series will be treated
    as individual bookmarks. Otherwise, series bookmarks will be ignored.
    """
    query = urlparse(list_url).query
    if not query:
        list_url += "?page=%d"
    elif "page" not in query:
        list_url += "&page=%d"

    work_ids = []
    max_works_found = False

    for page_no in itertools.count(start=1):
        print(
            "Finding page: \t"
            + str(page_no)
            + " of list. \t"
            + str(len(work_ids))
            + " ids found."
        )

        req = get_with_timeout(session, list_url % page_no)
        soup = BeautifulSoup(req.text, features="html.parser")

        for id_type, id, date in get_ids_and_dates_from_page(soup, date_type):
            if oldest_date and date and date < oldest_date:
                print(
                    id_type
                    + "/"
                    + id
                    + " has date "
                    + datetime.strftime(date, AO3_DATE_FORMAT)
                    + ". Stopping here."
                )
                max_works_found = True
                break

            if id_type == TYPE_WORKS:
                work_ids.append(id)
            elif expand_series is True and id_type == TYPE_SERIES:
                series_req = get_with_timeout(session, series_url_from_id(id))
                series_soup = BeautifulSoup(series_req.text, features="html.parser")
                for t, i, d in get_ids_and_dates_from_page(series_soup, date_type):
                    work_ids.append(i)

            if max_count and len(work_ids) >= max_count:
                max_works_found = True
                work_ids = work_ids[0:max_count]
                break

        if max_works_found:
            break

        # The pagination button at the end of the page is of the form
        #
        #     <li class="next" title="next"> ... </li>
        #
        # If there's another page of results, this contains an <a> tag
        # pointing to the next page.  Otherwise, it contains a <span>
        # tag with the 'disabled' class.
        try:
            next_button = soup.find("li", attrs={"class": "next"})
            if next_button.find("span", attrs={"class": "disabled"}):
                break
        except:
            # In case of absence of "next"
            break

    return work_ids


def get_ids_and_dates_from_page(soup, date_type):
    # Entries on a bookmarks page are stored in a list of the form:
    #
    #     <ol class="bookmark index group">
    #       <li id="bookmark_12345" class="bookmark blurb group" role="article">
    #         ...
    #       </li>
    #       ...
    #     </o>
    #
    # Entries on a reading page are stored in a list of the form:
    #
    #     <ol class ="reading work index group">
    #       <li class="reading work blurb group" id="work_12345" role="article">
    #         ...
    #       </li>
    #       ...
    #     </ul>
    #
    # Entries on a series page are stored in a list of the form:
    #
    #     <ul class ="series work index group">
    #       <li class="work blurb group" id="work_12345" role="article">
    #         ...
    #       </li>
    #       ...
    #     </ul>
    #
    # Entries on a user's works page are stored in a list of the form:
    #
    #     <ol class ="work index group">
    #       <li class="work blurb group" id="work_12345" role="article">
    #         ...
    #       </li>
    #       ...
    #     </ul>
    list_tag = soup.find("ol", attrs={"class": "index"})
    if not list_tag:
        list_tag = soup.find("ul", attrs={"class": "index"})

    for li_tag in list_tag.findAll("li", attrs={"class": "blurb"}):
        try:
            if date_type == DATE_UPDATED:
                date = get_work_update_date(li_tag)
            else:
                date = get_user_interaction_date(li_tag)

            # <h4 class="heading">
            #     <a href="/works/12345678">Work Title</a>
            #     <a href="/users/authorname/pseuds/authorpseud" rel="author">Author Name</a>
            # </h4>

            for h4_tag in li_tag.findAll("h4", attrs={"class": "heading"}):
                for link in h4_tag.findAll("a"):
                    if ("works" in link.get("href")) and not (
                        "external_works" in link.get("href")
                    ):
                        yield TYPE_WORKS, link.get("href").replace("/works/", ""), date
                    elif "series" in link.get("href"):
                        yield TYPE_SERIES, link.get("href").replace(
                            "/series/", ""
                        ), date
        except KeyError:
            # A deleted work shows up as
            #
            #      <li class="deleted reading work blurb group">
            #
            # There's nothing that we can do about that, so just skip
            # over it.
            if "deleted" in li_tag.attrs["class"]:
                pass
            else:
                raise


def get_with_timeout(session, url):
    req = session.get(url)

    # if timeout, wait and try again
    while len(req.text) < 20 and "Retry later" in req.text:
        print("timeout... waiting 3 mins and trying again")
        time.sleep(180)
        req = session.get(url)

    return req


def get_user_interaction_date(li_tag):
    """Get a date from an li tag corresponding to a work, and return it as
     a datetime object.
    For bookmarked works, this will be the date of bookmarking.
    For marked-for-later works, it's the date last visited.
    For other works (from pages where we don't see information about the
    user's interaction with fics), return None.
    """
    for div in li_tag.findAll("div", attrs={"class": "user"}):
        for p in div.findAll("p", attrs={"class": "datetime"}):
            return datetime.strptime(p.text, AO3_DATE_FORMAT)

        for h4 in div.findAll("h4", attrs={"class": "viewed"}):
            date = LAST_VISITED_REGEX.search(h4.text).group(1)
            return datetime.strptime(date, AO3_DATE_FORMAT)

    return None


def get_work_update_date(li_tag):
    for div in li_tag.findAll("div", attrs={"class": "header"}):
        for p in div.findAll("p", attrs={"class": "datetime"}):
            return datetime.strptime(p.text, AO3_DATE_FORMAT)
