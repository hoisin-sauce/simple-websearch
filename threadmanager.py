import queue
import threading
from typing import Callable

import log
import sitedatabasehandler
from subdomains import Subdomain


class ThreadManager:
    def __init__(self):
        self.threads: queue.Queue[threading.Thread] = queue.Queue()

    def join_threads(self):
        while not self.threads.empty():
            self.threads.get().join()

    def add_thread(self, thread: threading.Thread):
        self.threads.put(thread)


class QueueContainer:
    def __init__(self,
                 database_handler: sitedatabasehandler.SiteDatabaseHandler,
                 site_handler: Callable):
        self.queues = dict()
        self.active_handlers = set()
        self.db = database_handler
        self.site_handler = site_handler

    def get_queue(self, queue_name: str) -> queue.Queue:
        if queue_name not in self.queues:
            self.queues[queue_name] = queue.Queue()
        return self.queues[queue_name]

    def handler_exists(self, handler_name: str):
        return handler_name in self.active_handlers

    def register_handler(self, handler: str):
        assert not self.handler_exists(handler)
        self.active_handlers.add(handler)

    def unregister_handler(self, handler: str):
        self.active_handlers.remove(handler)

    def queue_links(self, links: dict[Subdomain, int]) -> None:
        """
        Queue links to their respective site handlers with checking
        :param links: links to be queued
        :return:
        """
        for link, _ in links.items():
            log.log(f"checking link {link}")
            # Check if link needs checking
            if not self.db.link_needs_checking(link):
                continue

            # Finally commit link to be searched
            if not self.handler_exists(link.domain):
                log.log(f"creating handler for {link.domain}")
                self.create_handler(link)

            log.log(f"handling link {link}")
            self.get_queue(link.domain).put(link)

    def create_handler(self, domain: Subdomain) -> None:
        """
        Starts a thread handling the given domain's scraping
        :param domain: Domain to be scraped
        :return:
        """
        try:
            self.register_handler(domain.domain)
        except AssertionError:
            return

        log.log(f"creating handler for {domain}")
        self.site_handler(domain, self.db, self.get_queue(domain.domain), self).start()