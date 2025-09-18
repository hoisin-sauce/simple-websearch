import datetime
import webstorage
import queue
import threading
import requests
import config
import re
import robots
from urllib.parse import urlparse, ParseResult
from bs4 import BeautifulSoup
import nltk
import time
from nltk.corpus import stopwords
from nltk import PorterStemmer
import log
import inspect

# TODO change from assertion to simple log and return for disallowed websites

class ThreadManager:
    def __init__(self):
        self.threads: queue.Queue[threading.Thread] = queue.Queue()

    def join_threads(self):
        while not self.threads.empty():
            self.threads.get().join()

    def add_thread(self, thread: threading.Thread):
        self.threads.put(thread)


class QueueContainer:
    def __init__(self):
        self.queues = dict()
        self.active_handlers = set()

    def get_queue(self, queue_name: str):
        if queue_name not in self.queues:
            self.queues[queue_name] = queue.Queue()
        return self.queues[queue_name]

    def handler_exists(self, handler_name: str):
        log.log(
            f"handler {handler_name} checking current handlers are {self.active_handlers}")
        return handler_name in self.active_handlers

    def register_handler(self, handler: str):
        assert not self.handler_exists(handler)
        self.active_handlers.add(handler)

    def unregister_handler(self, handler: str):
        self.active_handlers.remove(handler)


stemmer = PorterStemmer()

nltk.download('stopwords')
nltk.download('punkt')

stopwords = set(stopwords.words('english'))

# noinspection SpellCheckingInspection
db = webstorage.Database("webscrape.db", "webdbinit.sql")

thread_manager = ThreadManager()

queues = QueueContainer()


class Subdomain:
    def __init__(self, link, parent_url=None):
        o = urlparse(link)
        if config.Config.IGNORE_URL_FRAGMENTS.value:
            o = o._replace(fragment="")
        self.domain = o.netloc if o.netloc else parent_url
        self.o = o._replace(netloc=self.domain)._replace(scheme="https")
        self.extension = o._replace(netloc="")._replace(scheme="").geturl()

    def get_url(self):
        return self.o.geturl()

    def __repr__(self):
        return self.o.geturl()

    def __eq__(self, other):
        return self.o == other.o

    def __hash__(self):
        return hash(self.o)


def get_page_soup(url: str) -> BeautifulSoup:
    """
    Extracts a BeautifulSoup object from a url
    :param url: url of the website to extract from
    :return: BeautifulSoup object
    """
    page = requests.get(url)
    soup = BeautifulSoup(page.content, 'html.parser')
    return soup


def get_links(soup: BeautifulSoup,
              parent_url: str | None = None) -> dict[Subdomain, int]:
    """
    Extracts links from a BeautifulSoup object
    :param soup: BeautifulSoup object
    :param parent_url: parent url to extract links
    from in case only path specified
    :return: list of links in the object
    """
    links = dict()
    all_links = soup.find_all('a')
    for link in all_links:
        if (sub := separate_link(link.get('href'),
                                parent_url=parent_url)) not in links:
            links[sub] = 0
        links[sub] += 1
    log.log(f"found {len(links)} links making up {links}")
    return links


def get_tokens(soup: BeautifulSoup) -> dict:
    """
    Extracts tokens from a BeautifulSoup object
    :param soup: BeautifulSoup object
    :return: dict of tokens and their counts
    """
    # TODO tokenise in groups to allow for advanced searching
    text = soup.get_text()
    tokens = re.split(r'\W+', text)
    token_dict = {}

    for token in tokens:
        token = token.lower()
        token = stemmer.stem(token)

        if token in stopwords or not token:
            continue

        if token in token_dict:
            token_dict[token] += 1
        else:
            token_dict[token] = 1

    return token_dict


def separate_link(link: str, parent_url: str | None = None) -> Subdomain:
    """
    Converts a link to a subdomain
    TODO rewrite to use just urllib objects
    TODO this entire class is useless
    :param link: Link to site
    :param parent_url: Parent URL in case link is of the form /path...
    rather than netloc/path
    :return: Processed subdomain object
    """
    return Subdomain(link, parent_url=parent_url)


def process_url(link: str,
                rp: robots.RobotsParser | None = None) -> tuple[
    dict[Subdomain, int], dict[str, int]]:
    """
    Process url to get tokens and links found on page with checking
    :param link: Link to site
    :param rp: optional robots.RobotsParser
    :return:
    """
    domain = separate_link(link).domain
    if rp is None:
        rp = get_robots_handler(link)
    assert site_is_allowed(domain), \
        f"URL {link} is not allowed by config"
    assert can_check(link, rp=rp), \
        f"URL {link} is not allowed by robots.txt"
    soup = get_page_soup(link)
    # TODO write assertion or check for www.robotstxt.org/meta.html meta tags
    tokens = get_tokens(soup)
    links: dict[Subdomain, int] = get_links(soup, parent_url=domain)
    return links, tokens


def can_check(link: str, rp: robots.RobotsParser | None = None) -> bool:
    """
    Check whether a link is allowed by robots.txt
    :param link: link to check
    :param rp: optional robots.txt parser,
    if not given will automatically fetch
    :return:
    """
    if rp is None:
        rp = get_robots_handler(link)
    return rp.can_fetch("*", link)


def site_is_allowed(domain: str) -> bool:
    """
    Check if a domain is allowed by local config
    :param domain: Domain to check
    :return: Boolean representing if domain is allowed
    """
    allowed_sites = domain in config.Config.ALLOWED_SITES.value
    blocked_sites = domain in config.Config.BLOCKED_SITES.value
    limited_by_config = config.Config.LIMIT_SITES_TO_ALLOWED_SITES.value

    return not blocked_sites and (allowed_sites or not limited_by_config)


def get_robots_handler(domain: str) -> robots.RobotsParser:
    """
    Get the robots.txt parser from the given link
    :param domain: domain to get robots.txt parser from
    :return: parser for domain
    """
    robots_txt = ParseResult(
        scheme="https", netloc=domain, path="robots.txt",
        params="", query="", fragment="").geturl()
    try:
        rp = robots.RobotsParser.from_uri(robots_txt)
    except ValueError:
        log.log(
            f"Robots parser for {domain} "
            + f"failed to be created robots url was {robots_txt}")
        raise
    return rp


def site_handler(domain) -> None:
    """
    Handles all scraping for a single domain/netloc to maintain scraping speeds
    and remove redundant calls to read robots.txt
    :param domain: Domain to be scraped
    :return:
    """

    # TODO maintain continuity by using locks
    # ensures only one handler exists for the domain
    '''
    if queues.handler_exists(domain):
        return
    '''

    # Initial check to check if scraping of domain is allowed
    # By local rules
    assert site_is_allowed(domain), f"{domain} is not allowed by config"

    log.log(f"handler launched for {domain}")

    # Get the
    local_queue = queues.get_queue(domain)
    rp = get_robots_handler(domain)

    while True:
        try:
            log.log(f"handler {domain} fetching")
            to_handle = local_queue.get()
        except queue.Empty:
            time.sleep(
                config.Config.SECONDS_BETWEEN_SCRAPING_ON_SAME_SITE.value)
            continue

        print(f"handler {domain} processing {to_handle}")

        try:
            links, tokens = process_url(to_handle, rp=rp)
            print(f"fetched links: {links}")
        except AssertionError:
            # TODO log assertion issue
            print(f"failed to fetch links: {to_handle}")
            continue

        insert_link(Subdomain(to_handle))
        update_tokens(to_handle, tokens)
        update_links(Subdomain(to_handle), links)
        queue_links(links)

        time.sleep(config.Config.SECONDS_BETWEEN_SCRAPING_ON_SAME_SITE.value)


def update_links(origin: Subdomain, targets: dict[Subdomain, int]) -> None:
    log.log(f"Update links for {origin} links provided are {targets}")

    assert all(isinstance(target, Subdomain) for target in targets), \
        "Targets must be subdomains"
    # TODO clear links on update
    connection = {
        "origin_url": origin.domain,
        "origin_extension": origin.extension
    }

    for target, occurrences in targets.items():
        try:
            connection["target_url"] = target.domain
            connection["target_extension"] = target.extension
            connection["occurrences"] = occurrences

        except AttributeError:
            log.log(
                f"Error occured while updating links for {origin}, link was {target}\n Traceback: {"\n".join(repr(i) for i in inspect.stack())}")
            raise

        print(connection)
        db.execute_script(config.Config.INSERT_PAGE_LINK.value, params=connection)


def update_tokens(url: str, tokens: dict[str, int]) -> None:
    # TODO clear tokens before links are properly checked
    site = Subdomain(url)
    params = {"extension": site.extension, "url": site.domain}
    for token, count in tokens.items():
        params["token"] = token
        params["occurrences"] = count
        db.execute_script(config.Config.INSERT_TOKEN.value, params=params)


def link_needs_checking(link: Subdomain) -> bool:
    """
    Check if a link needs to be checked
    :param link: link to verify
    :return: boolean indicating if link needs to be checked
    """
    link = db.execute(
        config.Config.GET_LINK.value,
        params=(link.domain, link.extension),
        is_file=True
    )

    if not link:
        return True

    return bool(link[0]['needsChecking'])


def insert_link(link: Subdomain) -> None:
    """
    Insert a link into the database
    :param link: link
    :return:
    """
    next_check_date = (datetime.datetime.now()
                       + datetime.timedelta(
                days=config.Config.DAYS_TILL_NEXT_PAGE_CHECK.value
            )
                       )

    params = {
        "url": link.domain,
        "checked": next_check_date,
        "extension": link.extension
    }

    db.execute_script(config.Config.INSERT_LINK.value,
                      params=params)


def queue_links(links: dict[Subdomain, int]) -> None:
    """
    Queue links to their respective site handlers with checking
    :param links: links to be queued
    :return:
    """
    for link, _ in links.items():
        log.log(f"checking link {link}")
        # Check if link needs checking
        if not link_needs_checking(link):
            continue

        # Finally commit link to be searched
        if not queues.handler_exists(link.domain):
            log.log(f"creating handler for {link.domain}")
            create_handler(link.domain)

        log.log(f"handling link {link}")
        queues.get_queue(link.domain).put(link.get_url())


def create_handler(domain: str) -> None:
    """
    Starts a thread handling the given domain's scraping
    :param domain: Domain to be scraped
    :return:
    """
    try:
        queues.register_handler(domain)
    except AssertionError:
        return

    log.log(f"creating handler for {domain}")
    handler = threading.Thread(target=site_handler, args=(domain,))
    thread_manager.add_thread(handler)
    handler.start()


def old_links_daemon() -> None:
    while True:
        try:
            urls_to_check = db.execute(config.Config.FIND_OLD_LINKS.value,
                                       is_file=True)

            urls_to_check = {
                Subdomain(subdomain["link"]): 0 for subdomain in urls_to_check}

            queue_links(urls_to_check)

            time.sleep(config.Config.DAEMON_WAIT_TIME_SECONDS.value)
        except Exception as e:
            log.log(e)
            raise


def start_scraping() -> None:
    log.log("Starting background")
    background_scraper = threading.Thread(target=old_links_daemon, daemon=True)
    background_scraper.start()

    log.log("Starting primary scraping")
    sites_to_scrape: dict[Subdomain, int] = dict()
    for site in config.Config.SCRAPING_SITES.value:
        log.log(f"Starting scraping for {site}")
        sites_to_scrape[Subdomain(site)] = 0

    log.log("Queuing links")
    queue_links(sites_to_scrape)


if __name__ == "__main__":
    db.reset_database()
    start_scraping()
    thread_manager.join_threads()
