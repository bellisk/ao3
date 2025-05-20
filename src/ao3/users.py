# -*- encoding: utf-8
from . import Series
from .utils import *
from .works import Work


class User(object):
    """An AO3 author, not necessarily the user whose account we are logging in to.

    For authors who are not our user, we can see their works and public bookmarks, but
    no information on subscriptions or private bookmarks.
    """

    def __init__(self, username, session, ao3_url=BASE_URL):
        self.username = username
        self.session = session
        self.ao3_url = ao3_url
        self.url = f"{self.ao3_url}/users/{self.username}"

        # just for curiosity, count how many times deleted or locked works appear
        self.deleted = 0

    def __repr__(self):
        return f"{type(self).__name__}(username={self.username!r})"

    def works_count(self):
        url = f"{self.url}/works"
        req = get_with_timeout(self.session, url)
        soup = BeautifulSoup(req.text, features="html.parser")
        header_text = soup.h2.text
        m = re.search(WORKS_HEADER_REGEX, header_text)

        if m:
            return int(m.group(1))

        return 0

    def work_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the user's works' ids.
        We must be logged in to see locked works.
        If sort_by_updated=True, works are sorted by date the work was last
        updated, descending. Otherwise, sorting is by date the work was created,
        descending.
        """
        url = f"{self.url}/works"
        date_type = DATE_UPDATED

        return get_list_of_work_ids(
            url,
            self.session,
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
        url = f"{self.ao3_url}/users/{self.username}/gifts?page=%d"
        date_type = DATE_UPDATED

        return get_list_of_work_ids(
            url,
            self.session,
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
        url = f"{self.ao3_url}/users/{self.username}/bookmarks?page=%d"
        date_type = DATE_INTERACTED_WITH

        if sort_by_updated:
            url += "&bookmark_search[sort_column]=bookmarkable_date"
            date_type = DATE_UPDATED

        return self.get_list_of_work_ids(
            url,
            self.session,
            max_count,
            expand_series,
            oldest_date,
            date_type,
        )

    def get_list_of_work_ids(
        self,
        list_url,
        session,
        max_count=None,
        expand_series=False,
        oldest_date=None,
        date_type="",
    ):
        """
        TODO: this was just copied over from utils.py, and I removed the expand-series
        TODO: loop from there. Clean up!

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
                "Loading page: \t %d of list. \t %d ids found up to now."
                % (page_no, len(work_ids))
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
                    print(f"Getting all urls from series {id}....")
                    series = Series(id, session, self.ao3_url)
                    for i in series.work_ids():
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

        print(str(len(work_ids)) + " ids found.")

        return work_ids

    def marked_for_later_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the user's marked-for-later ids.
        """
        url = f"{self.ao3_url}/users/{self.username}/readings?show=to-read"

        return get_list_of_work_ids(
            url,
            self.session,
            max_count=max_count,
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
            work = Work(bookmark_id, self.session, self.ao3_url)
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
        api_url = f"{self.ao3_url}/users/{self.username}/readings?page=%d"

        for page_no in itertools.count(start=1):
            req = get_with_timeout(self.session, api_url % page_no)
            print("On page: " + str(page_no))
            print("Cumulative deleted works encountered: " + str(self.deleted))

            # if timeout, wait and try again
            while len(req.text) < 20 and "Retry later" in req.text:
                print("timeout... waiting 3 mins and trying again")
                time.sleep(180)
                req = get_with_timeout(self.session, api_url % page_no)

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
        api_url = f"{self.ao3_url}/users/{self.username}/subscriptions?type={sub_type}&page=%d"

        sub_ids = []
        max_subs_found = False

        num_subs = 0
        for page_no in itertools.count(start=1):
            print(
                "Loading page: \t"
                + str(page_no)
                + " of list. \t"
                + str(num_subs)
                + " ids found up to now."
            )

            req = get_with_timeout(self.session, api_url % page_no)
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
