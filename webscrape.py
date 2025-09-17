import datetime
import webstorage
import queue
import threading
import requests
import config
import re
import robots
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import nltk
import time
from nltk.corpus import stopwords
from nltk import PorterStemmer

class QueueContainer:
    def __init__(self):
        self.queues = dict()
        self.active_handlers = set()

    def get_queue(self, queue_name: str):
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

stemmer = PorterStemmer()

nltk.download('stopwords')
nltk.download('punkt')

stopwords = set(stopwords.words('english'))

# noinspection SpellCheckingInspection
db = webstorage.Database("webscrape.db", "webdbinit.sql")

queues = QueueContainer()

class Subdomain:
    def __init__(self, link, parent_url=None):
        o = urlparse(link)
        self.domain = o.netloc if o.netloc else parent_url
        self.o = o._replace(netloc = self.domain)._replace(scheme = "https")
        self.extension = o._replace(netloc = "")._replace(scheme = "").geturl()

    def get_url(self):
        return self.o.geturl()

    def __repr__(self):
        return self.o.geturl()

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
              parent_url: str | None = None) -> set[Subdomain]:
    """
    Extracts links from a BeautifulSoup object
    :param soup: BeautifulSoup object
    :param parent_url: parent url to extract links
    from in case only path specified
    :return: list of links in the object
    """
    links = set()
    for link in soup.find_all('a'):
        links.add(separate_link(link.get('href'), parent_url=parent_url))
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
        rp: robots.RobotsParser | None = None) -> tuple[set, dict[str, int]]:
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
    links = get_links(soup, parent_url=domain)
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

def get_robots_handler(link: str) -> robots.RobotsParser:
    """
    Get the robots.txt parser from the given link
    :param link: link to get robots.txt parser from
    :return: parser for domain from link
    """
    robots_txt = urlparse(link)._replace(
        params='', query='',
        fragment='', path="robots.txt").geturl()
    rp = robots.RobotsParser.from_uri(robots_txt)
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
    if queues.handler_exists(domain):
        return

    # Initial check to check if scraping of domain is allowed
    # By local rules
    assert site_is_allowed(domain), f"{domain} is not allowed by config"

    # Get the
    local_queue = queues.get_queue(domain)
    rp = get_robots_handler(domain)

    while True:
        try:
            to_handle = local_queue.get()
        except queue.Empty:
            continue

        try:
            links, tokens = process_url(to_handle, rp=rp)
        except AssertionError:
            # TODO log assertion issue
            continue

        insert_link(Subdomain(to_handle))
        update_tokens(to_handle, tokens)
        queue_links(links)

        time.sleep(config.Config.SECONDS_BETWEEN_SCRAPING_ON_SAME_SITE.value)

def update_tokens(url: str, tokens: dict[str, int]) -> None:
    site = Subdomain(url)
    params = {"extension": site.extension, "domain": site.domain}
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
    )[0]

    if not link:
        return True

    return bool(link['needsChecking'])

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

def queue_links(links: set[Subdomain]) -> None:
    """
    Queue links to their respective site handlers with checking
    :param links: links to be queued
    :return:
    """
    for link in links:
        # Check if link needs checking
        if not link_needs_checking(link):
            continue

        # Finally commit link to be searched
        if not queues.handler_exists(link.domain):
            create_handler(link.domain)
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

    threading.Thread(target=site_handler, args=(domain,)).start()

if __name__ == "__main__":
    db.reset_database()
    insert_link(Subdomain("https://selenium-python.readthedocs.io/"))
    link_needs_checking(Subdomain("https://selenium-python.readthedocs.io/"))