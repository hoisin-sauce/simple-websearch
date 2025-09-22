import requests
from bs4 import BeautifulSoup
import log
import tokens
from subdomains import Subdomain


def get_page_soup(url: Subdomain) -> BeautifulSoup:
    """
    Extracts a BeautifulSoup object from a url
    :param url: url of the website to extract from
    :return: BeautifulSoup object
    """
    page = requests.get(url.get_url())
    soup = BeautifulSoup(page.content, 'html.parser')
    for script in soup.find_all('script'):
        script.decompose()
    for style in soup.find_all('style'):
        style.decompose()
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
        if (sub := Subdomain(link.get('href'),
                                parent_url=parent_url)) not in links:
            links[sub] = 0
        links[sub] += 1
    log.log(f"found {len(links)} links making up {links}")
    return links


def get_tokens_from_soup(soup: BeautifulSoup) -> tokens.TokenContainer:
    """
    Extracts tokens from a BeautifulSoup object
    :param soup: BeautifulSoup object
    :return: dict of tokens and their counts
    """
    text = soup.get_text()

    token_dict = tokens.get_tokens(text)

    return token_dict