import datetime
import threading
import urllib
import urllib.error
import requests
import requestmanager
import pagehandler
import threadmanager
from sitedatabasehandler import SiteDatabaseHandler
from subdomains import Subdomain
import config
import log
import queue
import robots
import time
import tokens
import urllib.robotparser as parser
from typing import Tuple


class SiteHandler:
    @staticmethod
    def site_is_allowed(site: Subdomain) -> bool:
        """
        Check if a domain is allowed by local config
        :param site: Subdomain to check the domain of
        :return: Boolean representing if domain is allowed
        """
        domain = site.domain

        allowed_sites = domain in config.Config.ALLOWED_SITES.value
        blocked_sites = domain in config.Config.BLOCKED_SITES.value
        limited_by_config = config.Config.LIMIT_SITES_TO_ALLOWED_SITES.value

        return not blocked_sites and (allowed_sites or not limited_by_config)

    def __init__(self, domain: Subdomain,
                 database_handler: SiteDatabaseHandler,
                 command_queue: queue.Queue,
                 queue_handler: threadmanager.QueueContainer,):
        self.db = database_handler
        self.domain = domain
        self.command_queue = command_queue
        self.rp = self.get_robots_handler()
        self.queue_handler = queue_handler

        request_timings = self.get_request_timings()
        self.request_manager = requestmanager.RequestManager(*request_timings)

    def get_request_timings(self) -> \
            Tuple[int | None, datetime.timedelta | None]:
        local_parser = parser.RobotFileParser()
        local_parser.set_url(
            self.domain.o._replace(path="/robots.txt").geturl())
        try:
            local_parser.read()
        except urllib.error.URLError:
            return None, None
        request_rate = local_parser.request_rate("*")

        if request_rate is None:
            return None, None

        return (request_rate.requests,
                datetime.timedelta(seconds=request_rate.seconds))

    def start(self):
        threading.Thread(target=self.site_handler).start()

    def get_robots_handler(self) -> robots.RobotsParser:
        """
        Get the robots.txt parser from the given link
        :return: parser for domain
        """
        robots_txt = Subdomain.get_for_site(
            netloc=self.domain.domain, path="robots.txt")
        try:
            rp = robots.RobotsParser.from_uri(robots_txt)
        except ValueError:
            log.log(
                f"Robots parser for {self.domain} "
                + f"failed to be created robots url was {robots_txt}")
            raise
        return rp

    def site_handler(self) -> None:
        """
        Handles all scraping for a single domain/netloc to maintain scraping speeds
        and remove redundant calls to read robots.txt
        :return:
        """

        # Initial check to check if scraping of domain is allowed
        # By local rules
        if not SiteHandler.site_is_allowed(self.domain):
            log.log(f"{self.domain} is not allowed by config")
            return

        log.log(f"handler launched for {self.domain}")

        # Get the relevant data about the domain


        while True:
            try:
                log.log(f"handler {self.domain} fetching")
                to_handle = self.command_queue.get(
                    timeout=config.Config.THREADING_TIMEOUT.value,
                )

            except queue.Empty:
                log.log(f"handler {self.domain} expired to idle timeout")
                break

            # link in time range
            if self.db.link_recently_checked(to_handle):
                log.log(f"handler {self.domain} already checked link {to_handle}")
                continue

            log.log(f"handler {self.domain} processing {to_handle}")

            # attempt to process url
            try:
                links, page_tokens = self.process_url(to_handle)
                log.log(f"fetched links: {links}")
            except AssertionError:
                log.log(f"failed to fetch links: {to_handle}")
                continue

            if config.Config.TRACK_DATABASE_TIMES.value:
                start_time = time.time()

            # insert necessary data into database
            self.db.insert_link(to_handle)
            self.db.update_tokens(to_handle, page_tokens)
            self.db.update_links(to_handle, links)

            if config.Config.TRACK_DATABASE_TIMES.value:
                # noinspection PyUnboundLocalVariable
                elapsed_time = time.time() - start_time
                log.log(
                    f"Inserting links for {to_handle} took {elapsed_time} seconds")

            self.queue_handler.queue_links(links)

    def process_url(self, link: Subdomain) -> tuple[
        dict[Subdomain, int], tokens.TokenContainer]:
        """
        Process url to get tokens and links found on page with checking
        :param link: Link to site
        :return:
        """
        domain = link.domain
        assert self.site_is_allowed(link), \
            f"URL {link} is not allowed by config"
        assert self.can_check(link), \
            f"URL {link} is not allowed by robots.txt"

        response = self.get_page(link)
        soup = pagehandler.get_page_soup(response)
        # TODO write assertion or check for www.robotstxt.org/meta.html meta tags
        page_tokens = pagehandler.get_tokens_from_soup(soup)
        links: dict[Subdomain, int] = pagehandler.get_links(soup, parent_url=domain)
        return links, page_tokens

    def can_check(self, link: Subdomain,) -> bool:
        """
        Check whether a link is allowed by robots.txt
        :param link: link to check
        if not given will automatically fetch
        :return:
        """
        return self.rp.can_fetch("*", link.get_url())

    def get_page(self, link: Subdomain) -> requests.Response:
        """
        Actually get the page from a link
        :param link: page to be fetched
        :return: requests.Response object from page
        """
        return self.request_manager.request(link.get_url())
