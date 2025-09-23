import datetime
import queue
import threading
import time
import requests
import log

class Request:
    """
    Class to simplify result return flow across multiple threads
    """
    def __init__(self, url: str):
        self.url = url
        self.result = queue.Queue()

    def set(self, value: requests.Response):
        """
        Set the return for the request
        :param value: Return value
        :return:
        """
        self.result.put(value)


    def get(self):
        """
        Returns the final result
        :return:
        """
        return self.result.get()

    def __repr__(self):
        return repr(self.url)


class RequestManager:
    global_max_requests_for_period: int | None = None
    global_request_period: datetime.timedelta | None = None
    global_requests: int = 0
    global_request_period_start: datetime.datetime | None = None
    global_request_queue: queue.Queue[Request] | None = None
    global_request_handler: threading.Thread | None = None

    default_request_period: datetime.timedelta | None = None
    default_max_requests_for_period: int | None = None

    @staticmethod
    def set_global_period(max_requests: int | None = None,
            max_request_period: datetime.timedelta | None = None,) -> None:
        """
        Set global request period and the maximum number of requests to allow.
        :param max_requests: Maximum number of requests to allow in the period.
        :param max_request_period: Request period
        :return:
        """
        RequestManager.global_max_requests_for_period = max_requests
        RequestManager.global_request_period = max_request_period

    @staticmethod
    def set_default_period(request_period: datetime.timedelta | None = None,
            max_requests: int | None = None) -> None:
        """
        Set default request period and the maximum number of requests to allow.
        :param request_period: Timespan of request period
        :param max_requests: Maximum number of requests to allow in the period.
        :return:
        """

        RequestManager.default_request_period = request_period
        RequestManager.default_max_requests_for_period = max_requests

    @staticmethod
    def request_handler() -> None:
        """
        Internal method to manage the global requests
        :return:
        """
        assert RequestManager.global_request_period is not None, \
            "Set max request rate before starting"
        assert RequestManager.global_max_requests_for_period is not None, \
            "Set max request period before starting"

        while True:
            request: Request = RequestManager.global_request_queue.get()

            if RequestManager.global_request_period_start is None:
                RequestManager.reset_global_request_period()

            if datetime.datetime.now() > \
                RequestManager.global_request_period \
                + RequestManager.global_request_period_start:
                RequestManager.reset_global_request_period()

            if RequestManager.global_requests < \
                    RequestManager.global_max_requests_for_period:
                RequestManager.process_request(request)
                continue

            log.log("Waiting for request period to end")
            RequestManager.wait_for_end_of_request_period()
            log.log("Request period ended")
            RequestManager.process_request(request)


    @staticmethod
    def reset_global_request_period() -> None:
        """
        Reset global request period
        :return:
        """
        RequestManager.global_request_period_start = datetime.datetime.now()
        RequestManager.global_requests = 0

    @staticmethod
    def process_request(request: Request) -> None:
        """
        Internal method to process request and return result to the thread that
        called it
        :param request:
        :return:
        """
        log.log(f"Processing request: {request}")
        request.set(requests.get(request.url))
        RequestManager.global_requests += 1

    @staticmethod
    def wait_for_end_of_request_period() -> None:
        """
        Internal method to wait for end of request period
        :return:
        """
        delay: datetime.timedelta = datetime.datetime.now() \
            - RequestManager.global_request_period \
            - RequestManager.global_request_period_start
        time.sleep(delay.seconds)

    def __init__(self, max_requests: int | None,
                 period: datetime.timedelta | None,) -> None:
        """
        Request handler for an individual source
        Used to rate limit requests
        :param max_requests:
        :param period:
        """
        if period is None:
            assert RequestManager.default_request_period is not None, \
                "No default request period specified, specify a default request period using RequestManger.set_default_period"
            period = RequestManager.default_request_period

        if max_requests is None:
            assert RequestManager.default_max_requests_for_period is not None, \
                "No default max requests specified, specify a default max requests value using RequestManger.set_default_period"
            max_requests = RequestManager.default_max_requests_for_period

        self.max_requests: int = max_requests
        self.period: datetime.timedelta = period
        self.request_period_start: datetime.datetime | None = None
        self.request_queue: queue.Queue[Request] = queue.Queue()
        self.requests: int = 0

        if RequestManager.global_request_queue is None:
            RequestManager.global_request_queue = queue.Queue()

        if RequestManager.global_request_handler is None:
            RequestManager.global_request_handler = threading.Thread(
                target=RequestManager.request_handler, daemon=True)
            RequestManager.global_request_handler.start()

        threading.Thread(target=self.handler, daemon=True).start()

    def request(self, url) -> requests.Response:
        """
        Request the url
        Only method other than __init__ that should be interacted with
        :param url:
        :return:
        """
        request: Request = Request(url)
        self.request_queue.put(request)
        return request.get()

    def handler(self)-> None:
        """
        Internal method to handle requests to a single source
        :return:
        """
        while True:
            request: Request = self.request_queue.get()

            if self.request_period_start is None:
                self.reset_request_period()
                self.add_global_request(request)
                continue

            if self.request_period_start + self.period \
                    < datetime.datetime.now():
                self.reset_request_period()
                self.add_global_request(request)
                continue

            if self.requests < self.max_requests:
                self.add_global_request(request)
                continue

            delay: datetime.timedelta = \
                datetime.datetime.now() \
                - (self.request_period_start + self.period)
            log.log(f"Now: {datetime.datetime.now()}, start: {self.request_period_start}, period: {self.period}")

            if (wait := delay.total_seconds()) > 0:
                log.log(f"Waiting for request period to finish for {wait} seconds")
                time.sleep(wait)

            self.reset_request_period()
            self.add_global_request(request)

    def add_global_request(self, url) -> None:
        """
        Adds a global request to the queue from a local handler
        :param url:
        :return:
        """
        self.requests += 1
        log.log(f"Adding global request to queue {url}")
        RequestManager.global_request_queue.put(url)

    def reset_request_period(self) -> None:
        """
        Resets local request period
        :return:
        """
        log.log(f"Resetting request period with {self.requests} processed (max is {self.max_requests})")
        self.request_period_start = datetime.datetime.now()
        self.requests = 0
