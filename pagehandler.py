import requests
from bs4 import BeautifulSoup
import log
import tokens
from subdomains import Subdomain


def get_page_soup(response: requests.Response) -> BeautifulSoup:
    """
    Extracts a BeautifulSoup object from a url
    :param response: Response from url
    :return: BeautifulSoup object
    """

    soup = BeautifulSoup(response.content, 'html.parser')
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
    parent_url = parent_url.lower()
    links: dict[Subdomain, int] = dict()
    all_links = soup.find_all('a')
    for link in all_links:
        sub = Subdomain(link.get('href').lower(),parent_url=parent_url)
        for o_link in links:
            if o_link.get_url() == sub.get_url():
                links[o_link] += 1
                break
        else:
            links[sub] = 1
    log.log(f"found {len(links)} links making up {links.keys()}")
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