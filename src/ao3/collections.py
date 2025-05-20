# -*- encoding: utf-8
from .utils import DATE_UPDATED, get_list_of_work_ids


class Collection(object):
    """An AO3 collection."""

    def __init__(self, id, session, ao3_url):
        self.id = id
        self.session = session
        self.ao3_url = ao3_url
        self.url = f"{self.ao3_url}/collections/{self.id}"

    def work_ids(self, max_count=0, oldest_date=None):
        return get_list_of_work_ids(
            f"{self.url}/works",
            self.session,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=DATE_UPDATED,
        )
