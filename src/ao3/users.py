# -*- encoding: utf-8

import requests

from .utils import *
from .works import Work


class User(object):

    # instead of passing plaintext passwords, pass the contents of the _otwarchive_session cookie!
    def __init__(self, username, cookie):
        self.username = username
        sess = requests.Session()

        jar = requests.cookies.RequestsCookieJar()
        # must be done separately bc the set func returns a cookie, not a jar
        jar.set("_otwarchive_session", cookie, domain="archiveofourown.org")
        # AO3 requires this cookie to be set
        jar.set("user_credentials", "1", domain="archiveofourown.org")
        sess.cookies = jar

        self.sess = sess

        # just for curiosity, count how many times deleted or locked works appear
        self.deleted = 0

    def __repr__(self):
        return "%s(username=%r)" % (type(self).__name__, self.username)

    def work_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the user's works' ids.
        We must be logged in to see locked works.
        If sort_by_updated=True, works are sorted by date the work was last
        updated, descending. Otherwise, sorting is by date the work was created,
        descending.
        """
        url = "https://archiveofourown.org/works?user_id=%s" % self.username
        date_type = DATE_UPDATED

        return get_list_of_work_ids(
            url,
            self.sess,
            date_type=date_type,
            max_count=max_count,
            oldest_date=oldest_date,
        )

    def gift_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the ids of works gifted to the user.
        We must be logged in to see locked works.
        If sort_by_updated=True, works are sorted by date the work was last
        updated, descending. Otherwise, sorting is by date the work was created,
        descending.
        """
        url = "https://archiveofourown.org/users/%s/gifts?page=%%d" % self.username
        date_type = DATE_UPDATED

        return get_list_of_work_ids(
            url,
            self.sess,
            date_type=date_type,
            max_count=max_count,
            oldest_date=oldest_date,
        )

    def bookmarks_ids(
        self,
        max_count=None,
        expand_series=False,
        oldest_date=None,
        sort_by_updated=False,
    ):
        """
        Returns a list of the user's bookmarks' ids. Ignores external work bookmarks.
        User must be logged in to see private bookmarks.
        If expand_series=True, all works in a bookmarked series will be treated
        as individual bookmarks. Otherwise, series bookmarks will be ignored.
        If sort_by_updated=True, bookmarks are sorted by date the work was last
        updated, descending. Otherwise, sorting is by date the bookmark was created,
        descending.
        """
        url = "https://archiveofourown.org/users/%s/bookmarks?page=%%d" % self.username
        date_type = DATE_INTERACTED_WITH

        if sort_by_updated:
            url += "&bookmark_search[sort_column]=bookmarkable_date"
            date_type = DATE_UPDATED

        return get_list_of_work_ids(
            url,
            self.sess,
            max_count,
            expand_series,
            oldest_date,
            date_type,
        )

    def marked_for_later_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the user's marked-for-later ids.
        Does not currently handle expanding series.
        """
        url = (
            "https://archiveofourown.org/users/%s/readings?show=to-read" % self.username
        )

        return get_list_of_work_ids(
            url,
            self.sess,
            max_count=max_count,
            expand_series=False,
            oldest_date=oldest_date,
            date_type=DATE_INTERACTED_WITH,
        )

    def user_subscription_ids(self, max_count=None):
        """
        Returns a list of the usernames that the user is subscribed to.
        """
        return self._get_list_of_subscription_ids(
            TYPE_USERS,
            max_count,
        )

    def series_subscription_ids(self, max_count=None):
        """
        Returns a list of ids of the series that the user is subscribed to.
        """
        return self._get_list_of_subscription_ids(
            TYPE_SERIES,
            max_count,
        )

    def work_subscription_ids(self, max_count=None):
        """
        Returns a list of the work ids that the user is subscribed to.
        """
        return self._get_list_of_subscription_ids(
            TYPE_WORKS,
            max_count,
        )

    def bookmarks(self, max_count=None, expand_series=False):
        """
        Returns a list of the user's bookmarks as Work objects.
        Takes forever.
        User must be logged in to see private bookmarks.
        """

        bookmark_total = 0
        bookmark_ids = self.bookmarks_ids(max_count, expand_series)
        bookmarks = []

        for bookmark_id in bookmark_ids:
            work = Work(bookmark_id, self.sess)
            bookmarks.append(work)

            bookmark_total = bookmark_total + 1
            print((str(bookmark_total) + "\t bookmarks found."))

        return bookmarks

    def reading_history(self):
        """Returns a list of articles in the user's reading history.

        This requires the user to turn on the Viewing History feature.

        Generates a tuple of work_id, date, numvisits, title, author, fandom, warnings,
        relationships, characters, freeforms, words, chapters, comments, kudos,
        bookmarks, hits, pubdate

        Note that the dates are datetime objects, but everything else is either a list
        of strings (if multiple values) or a string.
        """
        # TODO: What happens if you don't have this feature enabled?
        # TODO: probably this should be returned as a structured object instead of this giant tuple

        # URL for the user's reading history page
        api_url = (
            "https://archiveofourown.org/users/%s/readings?page=%%d" % self.username
        )

        for page_no in itertools.count(start=1):
            req = self.sess.get(api_url % page_no)
            print("On page: " + str(page_no))
            print("Cumulative deleted works encountered: " + str(self.deleted))

            # if timeout, wait and try again
            while len(req.text) < 20 and "Retry later" in req.text:
                print("timeout... waiting 3 mins and trying again")
                time.sleep(180)
                req = self.sess.get(api_url % page_no)

            soup = BeautifulSoup(req.text, features="html.parser")
            # The entries are stored in a list of the form:
            #
            #     <ol class="reading work index group">
            #       <li id="work_12345" class="reading work blurb group">
            #         ...
            #       </li>
            #       <li id="work_67890" class="reading work blurb group">
            #         ...
            #       </li>
            #       ...
            #     </ol>
            #
            ol_tag = soup.find("ol", attrs={"class": "reading"})
            for li_tag in ol_tag.findAll("li", attrs={"class": "blurb"}):
                try:
                    work_id = li_tag.attrs["id"].replace("work_", "")

                    # Within the <li>, the last viewed date is stored as
                    #
                    #     <h4 class="viewed heading">
                    #         <span>Last viewed:</span> 24 Dec 2012
                    #
                    #         (Latest version.)
                    #
                    #         Viewed once
                    #     </h4>
                    #
                    h4_tag = li_tag.find("h4", attrs={"class": "viewed"})
                    date_str = re.search(
                        r"[0-9]{1,2} [A-Z][a-z]+ [0-9]{4}", h4_tag.contents[2]
                    ).group(0)
                    date = datetime.strptime(date_str, "%d %b %Y").date()

                    if "Visited once" in h4_tag.contents[2]:
                        # TODO: probably want to change these int values to ints
                        # instead of strings...
                        numvisits = "1"
                    else:
                        numvisits = re.search(
                            r"Visited (\d*) times", h4_tag.contents[2]
                        ).group(1)

                    # cast all the beautifulsoup navigablestrings to strings
                    title = str(
                        li_tag.find("h4", attrs={"class": "heading"})
                        .find("a")
                        .contents[0]
                    )

                    author = []  # this is if there's multiple authors
                    author_tag = li_tag.find("h4", attrs={"class": "heading"})
                    for x in author_tag.find_all("a", attrs={"rel": "author"}):
                        author.append(str(x.contents[0]))
                    # TODO: if Anonymous author (no link), should not take the
                    # contents, since it'll be blank
                    # Probably something similar to the chapters checker

                    fandom = []
                    fandom_tag = li_tag.find("h5", attrs={"class": "fandoms"})
                    for x in fandom_tag.find_all("a", attrs={"class": "tag"}):
                        fandom.append(str(x.contents[0]))

                    warnings = []
                    for x in li_tag.find_all("li", attrs={"class": "warnings"}):
                        warnings.append(str(x.find("a").contents[0]))
                    relationships = []
                    for x in li_tag.find_all("li", attrs={"class": "relationships"}):
                        relationships.append(str(x.find("a").contents[0]))
                    characters = []
                    for x in li_tag.find_all("li", attrs={"class": "characters"}):
                        characters.append(str(x.find("a").contents[0]))
                    freeforms = []
                    for x in li_tag.find_all("li", attrs={"class": "freeforms"}):
                        freeforms.append(str(x.find("a").contents[0]))

                    # this is longer bc sometimes chapters are a link and sometimes
                    # not, so need to normalize
                    chapters = li_tag.find("dd", attrs={"class", "chapters"})
                    if chapters.find("a") is not None:
                        chapters.find("a").replaceWithChildren()
                    chapters = "".join(chapters.contents)
                    hits = str(li_tag.find("dd", attrs={"class", "hits"}).contents[0])

                    # sometimes the word count is blank
                    words_tag = li_tag.find("dd", attrs={"class", "words"})
                    if len(words_tag.contents) == 0:
                        words = "0"
                    else:
                        words = str(words_tag.contents[0])

                    # for comments/kudos/bookmarks, need to check if the tag exists, bc
                    # if there are no comments etc it will not exist
                    comments_tag = li_tag.find("dd", attrs={"class", "comments"})
                    if comments_tag is not None:
                        comments = str(comments_tag.contents[0].contents[0])
                    else:
                        comments = "0"
                    kudos_tag = li_tag.find("dd", attrs={"class", "kudos"})
                    if kudos_tag is not None:
                        kudos = str(kudos_tag.contents[0].contents[0])
                    else:
                        kudos = "0"
                    bookmarks_tag = li_tag.find("dd", attrs={"class", "bookmarks"})
                    if bookmarks_tag is not None:
                        bookmarks = str(bookmarks_tag.contents[0].contents[0])
                    else:
                        bookmarks = "0"

                    pubdate_str = li_tag.find(
                        "p", attrs={"class", "datetime"}
                    ).contents[0]
                    pubdate = datetime.strptime(pubdate_str, "%d %b %Y").date()
                    yield work_id, date, numvisits, title, author, fandom, warnings, relationships, characters, freeforms, words, chapters, comments, kudos, bookmarks, hits, pubdate

                except (KeyError, AttributeError) as e:
                    # A deleted work shows up as
                    #
                    #      <li class="deleted reading work blurb group">
                    #
                    # There's nothing that we can do about that, so just skip
                    # over it.
                    if "deleted" in li_tag.attrs["class"]:
                        self.deleted += 1
                        pass
                    # A locked work shows up with
                    #       <div class="mystery header picture module">
                    elif li_tag.find("div", attrs={"class", "mystery"}) is not None:
                        self.deleted += 1
                        pass
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
            if next_button.find("span", attrs={"class": "disabled"}):
                break

    def _get_list_of_subscription_ids(self, sub_type=TYPE_WORKS, max_count=None):
        """
        Returns a list of ids from a list of the user's subscriptions:
        work, series or username.
        """
        api_url = (
            "https://archiveofourown.org/users/%s/subscriptions?type=%s&page=%%d"
            % (self.username, sub_type)
        )

        sub_ids = []
        max_subs_found = False

        num_subs = 0
        for page_no in itertools.count(start=1):
            print(
                "Finding page: \t"
                + str(page_no)
                + " of list. \t"
                + str(num_subs)
                + " ids found."
            )

            req = get_with_timeout(self.sess, api_url % page_no)
            soup = BeautifulSoup(req.text, features="html.parser")

            table_tag = soup.find("dl", attrs={"class": "subscription"})

            for dt in table_tag.find_all("dt"):
                for link in dt.find_all("a"):
                    # For some reason, dt.find('a') is giving a NavigableString instead
                    # of a tag object, but dt.find_all('a') works. We only want the
                    # first of the links here.
                    yield link.get("href").replace("/" + sub_type + "/", "")
                    break

                num_subs += 1
                sub_ids.append(id)

                if max_count and num_subs >= max_count:
                    max_subs_found = True
                    sub_ids = sub_ids[0:max_count]
                    break

            if max_subs_found:
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

        return sub_ids
