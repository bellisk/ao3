# -*- encoding: utf-8

import itertools
import json
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup, Tag

# Making this a separate class from Work bc the URL being fetched is different and we will need to iterate through pages of comments.


class WorkNotFound(Exception):
    pass


class RestrictedWork(Exception):
    pass


class Comments(object):
    def __init__(self, id, sess=None):
        self.id = id
        if sess is None:
            sess = requests.Session()
        self.sess = sess

    def __repr__(self):
        return "%s(id=%r)" % (type(self).__name__, self.id)

    def parsecomment(self, li_tag):  # inside class so the self info stays attached
        h4_tag = li_tag.find("h4", attrs={"class": "heading"})
        if h4_tag.find("a") is None:
            user = str(h4_tag.contents[0].strip())
            anon = True
        else:
            user = str(h4_tag.find("a").contents[0])
            anon = False

        if h4_tag.find("span", attrs={"class": "parent"}) is None:
            chapter = "on Chapter 1"
        else:
            chapter = str(h4_tag.find("span", attrs={"class": "parent"}).contents[0])

        ul_tag = li_tag.find("ul", attrs={"class": "actions"})
        if "Parent Thread" in str(
            ul_tag
        ):  # this is possibly the laziest way to search but hey, it works
            toplevel = False
        else:
            toplevel = True

        work_id_raw = str(self)
        work_id_split = work_id_raw.split("'")
        work_id_num = work_id_split[1]
        work_id = work_id_num[:-2]

        date = str(li_tag.find("span", attrs={"class": "date"}).contents[0])
        month = str(li_tag.find("abbr", attrs={"class": "month"}).contents[0])
        year = str(li_tag.find("span", attrs={"class": "year"}).contents[0])
        time = str(li_tag.find("span", attrs={"class": "time"}).contents[0])
        timezone = str(li_tag.find("abbr", attrs={"class": "timezone"}).contents[0])
        date_time = date + " " + month + " " + year + " " + time

        content = str(
            li_tag.find("blockquote", attrs={"class": "userstuff"}).contents[0]
        )

        return work_id, user, anon, toplevel, date_time, timezone, chapter, content

    def recursemorecomments(self, url):
        mc_req = self.sess.get(url)
        # if timeout, wait and try again
        while len(mc_req.text) < 20 and "Retry later" in mc_req.text:
            print("timeout... waiting 3 mins and trying again")
            time.sleep(180)
            mc_req = self.sess.get(url)

        mc_soup = BeautifulSoup(mc_req.text, features="html.parser")
        for mc_li_tag in mc_soup.findAll("li", attrs={"class": "comment"}):
            try:
                yield self.parsecomment(mc_li_tag)
            except AttributeError:
                if "more comments in this thread" in str(
                    mc_li_tag
                ):  # potentially will break if nested further?? unsure what that looks like though
                    for x in self.recursemorecomments(
                        "https://archiveofourown.org" + mc_li_tag.find("a").get("href")
                    ):
                        yield x
                else:
                    raise

    def comment_contents(self):
        """Generator for next comment on the work.
        Generates a tuple of user, anon (boolean value -- true if anon), toplevel (boolean value - true if toplevel comment), (day of month, month, year, time), timezone, content
        Unless otherwise specified, all values are returned as strings
        Returned datetime is for the time the comment was made, not the edited time

        """

        api_url = (
            "https://archiveofourown.org/works/%s?page=%%d&show_comments=true&view_full_work=true"
            % self.id
        )

        for page_no in itertools.count(start=1):
            req = self.sess.get(api_url % page_no)
            # if timeout, wait and try again
            while len(req.text) < 20 and "Retry later" in req.text:
                print("timeout... waiting 3 mins and trying again")
                time.sleep(180)
                req = self.sess.get(api_url % page_no)

            # make sure work can be found
            if req.status_code == 404:
                raise WorkNotFound("Unable to find a work with id %r" % self.id)
            elif req.status_code != 200:
                raise RuntimeError(
                    "Unexpected error from AO3 API: %r (%r)"
                    % (req.text, req.status_code)
                )
            if "This work could have adult content" in req.text:
                raise RestrictedWork(
                    "Work ID %s may have adult content"
                )  # force login to look at this, though theoretically the URL would just have to be modified to add view_adult=true. but i don't want to test this now :P
            if "This work is only available to registered users" in req.text:
                raise RestrictedWork("Looking at work ID %s requires login")

            soup = BeautifulSoup(req.text, features="html.parser")
            for li_tag in soup.findAll("li", attrs={"class": "comment"}):
                try:
                    yield self.parsecomment(li_tag)
                except AttributeError:
                    # deleted comment only has text
                    if "Previous comment deleted" in str(li_tag):
                        pass
                    elif "more comments in this thread" in str(li_tag):
                        for x in self.recursemorecomments(
                            "https://archiveofourown.org" + li_tag.find("a").get("href")
                        ):
                            yield x
                    else:
                        raise

            # The pagination button at the end of the page is of the form
            #
            #     <li class="next" title="next"> ... </li>
            #
            # If there's another page of results, this contains an <a> tag
            # pointing to the next page.  Otherwise, it contains a <span>
            # tag with the 'disabled' class.
            next_button = soup.find("li", attrs={"class": "next"})
            if next_button is None:  # if only one page of comments
                break
            if next_button.find("span", attrs={"class": "disabled"}):
                break
