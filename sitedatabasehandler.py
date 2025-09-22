from subdomains import Subdomain
from typing import Any, Generator
from tokens import TokenContainer
import datetime
import webstorage
import log
import config
import inspect

class SiteDatabaseHandler:
    def __init__(self, database: webstorage.Database):
        self.db: webstorage.Database = database

    def update_links(self, origin: Subdomain, targets: dict[Subdomain, int]) -> None:
        log.log(f"Update links for {origin} links provided are {targets}")

        assert all(isinstance(target, Subdomain) for target in targets), \
            "Targets must be subdomains"
        # TODO clear links on update

        if config.Config.EXECUTE_MANY:
            links = SiteDatabaseHandler.link_generator(origin, targets)

            self.db.execute_many(config.Config.INSERT_MANY_PAGE_LINK.value,
                            params=links)

        else:
            connection: dict[str, Any] = {
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
                        f"Error occurred while updating links for {origin}, link was {target}\n Traceback: {"\n".join(repr(i) for i in inspect.stack())}")
                    raise

                self.db.execute_script(config.Config.INSERT_PAGE_LINK.value,
                                  params=connection)

    @staticmethod
    def link_generator(
                       origin: Subdomain, targets: dict[Subdomain, int]) -> \
            Generator[dict[str, Any], None, None]:
        connection: dict[str, Any] = {
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
                    f"Error occurred while updating links for {origin}, link was {target}\n Traceback: {"\n".join(repr(i) for i in inspect.stack())}")
                raise

            yield connection

    def update_tokens(self, site: Subdomain, page_tokens: TokenContainer) -> None:
        # TODO clear tokens before links are properly checked
        if config.Config.EXECUTE_MANY:
            token_names = page_tokens.token_name_tuples()
            self.db.execute_many(config.Config.ENSURE_TOKEN_EXISTS.value,
                            params=token_names)

            token_gen = self.token_generator(site, page_tokens)
            self.db.execute_many(config.Config.INSERT_MANY_TOKEN.value,
                            params=token_gen)
        else:
            params: dict[str, Any] = {"extension": site.extension,
                                      "url": site.domain}
            for token in page_tokens.tokens():
                params["token"] = token.token_name
                params["occurrences"] = token.token_count
                self.db.execute_script(config.Config.INSERT_TOKEN.value,
                                  params=params)

    @staticmethod
    def token_generator(site: Subdomain, page_tokens: TokenContainer) -> \
    Generator[dict[str, Any], None, None]:
        params: dict[str, Any] = {"extension": site.extension,
                                  "url": site.domain}
        for token in page_tokens.tokens():
            params["token"] = token.token_name
            params["occurrences"] = token.token_count
            yield params

    def link_needs_checking(self, link: Subdomain) -> bool:
        """
        Check if a link needs to be checked
        :param link: link to verify
        :return: boolean indicating if link needs to be checked
        """
        link = self.db.execute(
            config.Config.GET_LINK.value,
            params=(link.domain, link.extension),
            is_file=True
        )

        if not link:
            return True

        return bool(link[0]['needsChecking'])

    def insert_link(self, link: Subdomain) -> None:
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

        self.db.execute_script(config.Config.INSERT_LINK.value,
                          params=params)

    def link_recently_checked(self, link: Subdomain) -> bool:
        if config.Config.ALLOW_DUPLICATES_DESPITE_TIMING.value:
            return False

        params = [link.domain, link.extension]
        check = self.db.execute(config.Config.TIME_CHECK_LINK.value, params=params,
                           is_file=True)

        if not check:
            return False

        log.log(f"{link} was in check")

        if check[0]["checked_recently"]:
            return True

        return False