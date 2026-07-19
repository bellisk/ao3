# -*- encoding: utf-8
from .utils import DATE_UPDATED, get_list_of_work_ids


class Collection(object):
    """An AO3 collection."""

    def __init__(self, id, session_handler):
        self.id = id
        self.session_handler = session_handler
        self.path = f"/collections/{self.id}"

    def work_ids(self, max_count=0, oldest_date=None):
        return get_list_of_work_ids(
            f"{self.path}/works",
            self.session_handler,
            max_count=max_count,
            oldest_date=oldest_date,
            date_type=DATE_UPDATED,
        )
