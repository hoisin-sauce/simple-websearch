import queue
import sys
import threading
import atexit
import time
from types import FrameType

class ProfilerHandler:
    def __init__(self, filename="trace.log", separator="-",
                 only_relative_files=False, ignore_internal_methods=False,
                 auto_log_time: int | float | None = None):
        self.profiles : dict[str, queue.Queue[str]] = dict()
        self.indents : dict[str, int] = dict()
        self.filename : list[str] = filename.split(".")
        self.separator : str = separator
        self.only_relative_files : bool = only_relative_files
        self.ignore_internal_methods : bool = ignore_internal_methods
        self.log_count : int = 0
        self.auto_log_time : int | float | None = auto_log_time
        self.init_time : float = time.time()

        self.local_files : list[str] = list()

        if only_relative_files:
            import glob
            self.local_files = list(i[:-3] for i in glob.glob("*.py"))

        # Setup autologging
        if auto_log_time is not None:
            threading.Thread(target=self._auto_log, daemon=True).start()

        # Setup profiling
        threading.setprofile(self.profiler)
        sys.setprofile(self.profiler)

        # Register logging on program close
        atexit.register(self.log_profiles)

    def _auto_log(self):
        while True:
            time.sleep(self.auto_log_time)
            self.log_profiles()

    def get_profile(self):
        profile_name = threading.current_thread().name
        if profile_name not in self.profiles:
            self.profiles[profile_name] = queue.Queue()
            self.indents[profile_name] = 0
        return self.profiles[profile_name]

    @property
    def indent(self):
        profile_name = threading.current_thread().name
        if profile_name not in self.indents:
            self.indents[profile_name] = 0
        return self.indents[profile_name]

    @indent.setter
    def indent(self, value):
        profile_name = threading.current_thread().name
        self.indents[profile_name] = value

    def log_profiles(self):
        with open(
                f"{self.filename[0]}_{self.log_count}.{self.filename[1]}",
                "w", encoding="utf-8") as f:
            for profile in self.profiles.keys():
                f.write("=" * 40 + "\n\n")
                f.write(profile + "\n\n")
                f.write("=" * 40 + "\n")
                traced = self.profiles[profile]
                while not traced.empty():
                    f.write(traced.get() + "\n")
        self.log_count += 1


    def log(self, message: str):
        log_message = self.separator * self.indent + message
        self.get_profile().put(log_message)

    def profiler(self, frame: FrameType, event, arg):
        if self.only_relative_files:
            if '__main__' not in (name := frame.f_globals.get('__name__')):
                if name not in self.local_files:
                    return
        if self.ignore_internal_methods:
            if frame.f_code.co_name[:2] == "__":
                return
        match event:
            case 'call':
                self.log("-----")
                _locals = dict(**frame.f_locals)
                if frame.f_code.co_name == '__init__':
                    del _locals['self']
                self.log(f"Start {frame.f_code.co_qualname}")
                self.log(f"File: {frame.f_code.co_filename}")
                self.log(f"Relative File: {frame.f_globals.get('__name__')}")
                self.log(f"lineno: {frame.f_code.co_firstlineno}")
                self.log(f"time called: {time.time() - self.init_time}")
                self.log(f"Params:")
                for local_name, value in _locals.items():
                    self.log(f"{local_name}: {value}")
                self.indent += 1
            case 'return':
                self.indent -= 1
                self.log(f"Exit {frame.f_code.co_qualname}")
                self.log(f"Returned : {arg}")
                self.log("-----")
            case 'c_call':
                pass
            case 'c_return':
                pass
            case 'c_exception':
                self.log_profiles()

if __name__ == '__main__':
    def func(arg, kwarg=None) -> tuple[int, str]:
        n = arg + kwarg
        n = str(n)
        return 1, n

    def a(n):
        b(n)

    def b(m):
        c(m)

    def c(k):
        print(1, k)

    indent_level = 0

    def log(text):
        global indent_level
        print(f"{threading.current_thread().name} \t{indent_level * '-'}{text}")

    def profiler(frame: FrameType, event, arg):
        global indent_level
        match event:
            case 'call':
                log("-----")
                _locals = dict(**frame.f_locals)
                if frame.f_code.co_name == '__init__':
                    del _locals['self']
                log(f"Start {frame.f_code.co_qualname}")
                log(f"lineno: {frame.f_lineno}")
                log(f"Params:")
                for local_name, value in _locals.items():
                    log(f"{local_name}: {value}")
                indent_level += 1
            case 'return':
                indent_level -= 1
                log(f"Exit {frame.f_code.co_qualname}")
                log(f"Returned : {arg}")
                log("-----")
            case 'c_call':
                pass
            case 'c_return':
                pass
            case 'c_exception':
                pass

    class thing:
        def __init__(self, arg, kwarg=None):
            self.arg = arg
            self.kwarg = kwarg

        def __repr__(self):
            return f"<{self.__class__.__name__}({self.arg}, {self.kwarg})> afsdafasfs"

    logi = ProfilerHandler(only_relative_files=True)
    func(1,kwarg=2)
    a(2)

