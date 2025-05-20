# -*- encoding: utf-8
from bs4 import BeautifulSoup

from .utils import DATE_UPDATED, get_list_of_work_ids, get_with_timeout


class Series(object):
    """An AO3 series."""

    def __init__(self, id, session, ao3_url):
        self.id = id
        self.session = session
        self.ao3_url = ao3_url
        self.url = f"{self.ao3_url}/series/{self.id}"

    def work_ids(self, max_count=0, oldest_date=None):
        return get_list_of_work_ids(
            self.url,
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=DATE_UPDATED,
        )

    def info(self):
        req = get_with_timeout(self.session, self.url)
        soup = BeautifulSoup(req.text, features="html.parser")

        info = {"Title": soup.h2.text.strip()}

        dl = soup.find("dl", attrs={"class": "meta"})
        keys = [dt.text[:-1] for dt in dl.findAll("dt")]
        values = [dd.text for dd in dl.findAll("dd")]

        for i in range(len(keys)):
            if keys[i] != "Stats":
                info[keys[i]] = values[i]

        return info
