# -*- encoding: utf-8
from bs4 import BeautifulSoup

from .utils import DATE_UPDATED, get_list_of_work_ids


class Series(object):
    """An AO3 series."""

    def __init__(self, id, session_handler):
        self.id = id
        self.session_handler = session_handler
        self.path = f"/series/{self.id}"

    def work_ids(self, max_count=0, oldest_date=None):
        return get_list_of_work_ids(
            self.path,
            self.session_handler,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=DATE_UPDATED,
        )

    def info(self):
        response = self.session_handler.get_with_timeout(self.path)
        soup = BeautifulSoup(response.text, features="html.parser")

        info = {"Title": soup.h2.text.strip()}

        dl = soup.find("dl", attrs={"class": "meta"})
        keys = [dt.text[:-1] for dt in dl.findAll("dt")]
        values = [dd.text for dd in dl.findAll("dd")]

        for i in range(len(keys)):
            if keys[i] != "Stats":
                info[keys[i]] = values[i]

        return info
