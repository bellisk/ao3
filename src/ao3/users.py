from datetime import datetime
import itertools
import re
import time

from bs4 import BeautifulSoup
import requests

from .works import HistoryEntry, Work

WORK_TYPE = 'work'
SERIES_TYPE = 'series'
AO3_DATE_FORMAT = '%d %b %Y'


class User(object):

    # instead of passing plaintext passwords, pass the contents of the _otwarchive_session cookie!
    def __init__(self, username, cookie):
        self.username = username
        sess = requests.Session()

        jar=requests.cookies.RequestsCookieJar()
        jar.set('_otwarchive_session',cookie,domain='archiveofourown.org')  #must be done separately bc the set func returns a cookie, not a jar
        jar.set('user_credentials','1',domain='archiveofourown.org') #AO3 requires this cookie to be set
        sess.cookies=jar

        self.sess = sess

        self.deleted = 0 #just for curiosity, count how many times deleted or locked works appear

    def __repr__(self):
        return '%s(username=%r)' % (type(self).__name__, self.username)

    def bookmarks_ids(self, max_count=None, expand_series=False, oldest_date=None):
        """
        Returns a list of the user's bookmarks' ids. Ignores external work bookmarks.
        User must be logged in to see private bookmarks.
        If expand_series=True, all works in a bookmarked series will be treated
        as individual bookmarks. Otherwise, series bookmarks will be ignored.
        """
        return self._get_list_of_ids(
            'https://archiveofourown.org/users/%s/bookmarks?page=%%d',
            max_count,
            expand_series,
            oldest_date
        )

    def marked_for_later_ids(self, max_count=None, oldest_date=None):
        """
        Returns a list of the user's marked-for-later ids.
        Does not currently handle expanding series.
        """
        return self._get_list_of_ids(
            'https://archiveofourown.org/users/%s/readings?show=to-read&page=%%d',
            max_count,
            False,
            oldest_date
        )


    def _get_list_of_ids(self, list_url, max_count=None, expand_series=False, oldest_date=None):
        """
        Returns a list of work ids from a paginated list.
        Ignores external work bookmarks.
        User must be logged in to see private bookmarks.
        If expand_series=True, all works in a bookmarked series will be treated
        as individual bookmarks. Otherwise, series bookmarks will be ignored.
        """
        api_url = (list_url % self.username)

        bookmarks = []
        max_bookmarks_found = False

        num_works = 0
        for page_no in itertools.count(start=1):
            print("Finding page: \t" + str(page_no) + " of list. \t" + str(num_works) + " ids found.")

            req = self._get_with_timeout(api_url % page_no)
            soup = BeautifulSoup(req.text, features='html.parser')

            for id_type, id, date in self._get_work_or_series_ids_from_page(soup):
                if oldest_date and date and date < oldest_date:
                    print("Last interaction with " + id_type + " " + id + " was on " + datetime.strftime(date, AO3_DATE_FORMAT))
                    print("Stopping here")
                    max_bookmarks_found = True
                    break

                if id_type == WORK_TYPE:
                    num_works += 1
                    bookmarks.append(id)
                elif expand_series == True and id_type == SERIES_TYPE:
                    series_req = self._get_with_timeout(
                        'https://archiveofourown.org/series/%s'
                        % id
                    )
                    series_soup = BeautifulSoup(series_req.text, features='html.parser')
                    for t, i, d in self._get_work_or_series_ids_from_page(series_soup):
                        num_works += 1
                        bookmarks.append(i)

                if max_count and num_works >= max_count:
                    max_bookmarks_found = True
                    bookmarks = bookmarks[0:max_count]
                    break

            if max_bookmarks_found:
                break

            # The pagination button at the end of the page is of the form
            #
            #     <li class="next" title="next"> ... </li>
            #
            # If there's another page of results, this contains an <a> tag
            # pointing to the next page.  Otherwise, it contains a <span>
            # tag with the 'disabled' class.
            try:
                next_button = soup.find('li', attrs={'class': 'next'})
                if next_button.find('span', attrs={'class': 'disabled'}):
                    break
            except:
                # In case of absence of "next"
                break

        return bookmarks

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

        Generates a HistoryEntry.
        """
        # TODO: What happens if you don't have this feature enabled?

        # URL for the user's reading history page
        api_url = (
            'https://archiveofourown.org/users/%s/readings?page=%%d' %
            self.username)

        for page_no in itertools.count(start=1):
            req = self.sess.get(api_url % page_no)
            print("On page: "+str(page_no))
            print("Cumulative deleted works encountered: "+str(self.deleted))

            # if timeout, wait and try again
            while len(req.text) < 20 and "Retry later" in req.text:
                print("timeout... waiting 3 mins and trying again")
                time.sleep(180)
                req = self.sess.get(api_url % page_no)

            soup = BeautifulSoup(req.text, features='html.parser')
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
            ol_tag = soup.find('ol', attrs={'class': 'reading'})
            for li_tag in ol_tag.findAll('li', attrs={'class': 'blurb'}):
                try:
                    work_id = li_tag.attrs['id'].replace('work_', '')

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
                    h4_tag = li_tag.find('h4', attrs={'class': 'viewed'})
                    date_str = re.search(
                        r'[0-9]{1,2} [A-Z][a-z]+ [0-9]{4}',
                        h4_tag.contents[2]).group(0)
                    date = datetime.strptime(date_str, '%d %b %Y').date()

                    if "Visited once" in h4_tag.contents[2]:
                        num_visits=1
                    else:
                        num_visits=str(re.search(r'Visited (\d*) times',h4_tag.contents[2]).group(1))

                    work = HistoryEntry(work_id, date, num_visits, self.sess)

                    yield work

                except (KeyError, AttributeError) as e:
                    # A deleted work shows up as
                    #
                    #      <li class="deleted reading work blurb group">
                    #
                    # There's nothing that we can do about that, so just skip
                    # over it.
                    if 'deleted' in li_tag.attrs['class']:
                        self.deleted+=1
                        pass
                    # A locked work shows up with
                    #       <div class="mystery header picture module">
                    elif li_tag.find('div',attrs={'class','mystery'}) is not None:
                        self.deleted+=1
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
            next_button = soup.find('li', attrs={'class': 'next'})
            if next_button.find('span', attrs={'class': 'disabled'}):
                break

    def _get_work_or_series_ids_from_page(self, soup):
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

        list_tag = soup.find('ol', attrs={'class': 'bookmark'})
        if not list_tag:
            list_tag = soup.find('ol', attrs={'class': 'reading'})
        if not list_tag:
            list_tag = soup.find('ul', attrs={'class': 'series'})

        for li_tag in list_tag.findAll('li', attrs={'class': 'blurb'}):
            try:
                date = self._get_user_interaction_date(li_tag)
                # <h4 class="heading">
                #     <a href="/works/12345678">Work Title</a>
                #     <a href="/users/authorname/pseuds/authorpseud" rel="author">Author Name</a>
                # </h4>

                for h4_tag in li_tag.findAll('h4', attrs={'class': 'heading'}):
                    for link in h4_tag.findAll('a'):
                        if ('works' in link.get('href')) and not ('external_works' in link.get('href')):
                            yield WORK_TYPE, link.get('href').replace('/works/', ''), date
                        elif 'series' in link.get('href'):
                            yield SERIES_TYPE, link.get('href').replace('/series/', ''), date
            except KeyError:
                # A deleted work shows up as
                #
                #      <li class="deleted reading work blurb group">
                #
                # There's nothing that we can do about that, so just skip
                # over it.
                if 'deleted' in li_tag.attrs['class']:
                    pass
                else:
                    raise

    def _get_with_timeout(self, url):
        req = self.sess.get(url)

        # if timeout, wait and try again
        while len(req.text) < 20 and "Retry later" in req.text:
            print("timeout... waiting 3 mins and trying again")
            time.sleep(180)
            req = self.sess.get(url)

        return req

    def _get_user_interaction_date(self, li_tag):
        """Get a date from an li tag corresponding to a work, and return it as
         a datetime object.
        For bookmarked works, this will be the date of bookmarking.
        For marked-for-later works, it's the date last visited.
        For other works (from pages where we don't see information about the
        user's interaction with fics), return None.
        """
        for div in li_tag.findAll('div', attrs={'class': 'user'}):
            for p in div.findAll('p', attrs={'class': 'datetime'}):
                return datetime.strptime(p.text, AO3_DATE_FORMAT)

            last_visited = re.compile('Last visited: ([0-9]{2} [a-zA-Z]{3} [0-9]{4})')
            for h4 in div.findAll('h4', attrs={'class': 'viewed'}):
                date = last_visited.search(h4.text).group(1)
                return datetime.strptime(date, AO3_DATE_FORMAT)

        return None
