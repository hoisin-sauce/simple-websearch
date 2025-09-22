import config
from urllib.parse import urlparse, ParseResult

class Subdomain:
    o: ParseResult
    domain: str
    extension: str

    @staticmethod
    def get_for_domain(domain):
        return Subdomain.get_for_site(domain=domain)

    @staticmethod
    def get_for_site(scheme="https", netloc="", path="", params="", query="", fragment=""):
        link = ParseResult(scheme=scheme, netloc=netloc, path=path, params=params, query=query, fragment=fragment)
        return Subdomain(link.geturl())

    def __init__(self, link: str, parent_url: str | None =None):
        o = urlparse(link)
        if config.Config.IGNORE_URL_FRAGMENTS.value:
            o = o._replace(fragment="")
        self.domain = o.netloc if o.netloc else parent_url
        self.o = o._replace(netloc=self.domain)._replace(scheme="https")
        self.extension = o._replace(netloc="")._replace(scheme="").geturl()
        if not self.extension:
            self.extension = "/"
            return
        if self.extension[0] != "/":
            self.extension = "/" + self.extension

    def get_url(self):
        return self.o.geturl()

    def __repr__(self):
        return self.o.geturl()

    def __eq__(self, other):
        return self.o == other.o

    def __hash__(self):
        return hash(self.o)