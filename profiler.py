import queue
import sys, threading
import atexit
from types import FrameType

class ProfilerHandler:
    def __init__(self, filename="trace.log", separator="-",
                 only_relative_files=False, ignore_internal_methods=False):
        self.profiles : dict[str, queue.Queue[str]] = dict()
        self.indents : dict[str, int] = dict()
        self.filename : str = filename
        self.separator : str = separator
        self.only_relative_files : bool = only_relative_files
        self._written : bool = False
        self.ignore_internal_methods : bool = ignore_internal_methods
        threading.setprofile(self.profiler)
        sys.setprofile(self.profiler)
        atexit.register(self.log_profiles)

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
        if self._written:
            return
        with open(self.filename, "w", encoding="utf-8") as f:
            for profile in self.profiles.keys():
                f.write("=" * 40 + "\n\n")
                f.write(profile + "\n\n")
                f.write("=" * 40 + "\n")
                traced = self.profiles[profile]
                data = list(traced.queue)
                for line in data:
                    f.write(line + "\n")
        self._written = True


    def log(self, message: str):
        log_message = self.separator * self.indent + message
        self.get_profile().put(log_message)

    def profiler(self, frame: FrameType, event, arg):
        if self.only_relative_files:
            if '__main__' not in frame.f_globals.get('__name__'):
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
                pass

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