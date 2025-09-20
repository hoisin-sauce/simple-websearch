import threading
import config

if config.Config.ENABLE_LOGGING_PROFILER:
    import profiler as p
    profiler = p.ProfilerHandler(only_relative_files=config.Config.ONLY_LOG_RELATIVE_CALLS.value,
        ignore_internal_methods=config.Config.IGNORE_INTERNAL_CALLS.value)

def log_with_thread(message):
    print(f"{threading.current_thread().name}: {message}")

def do_nothing(*args, **kwargs):
    del args, kwargs # ignore for reason
    pass

# TODO not be lazy and write logging properly
log = log_with_thread # NOLOG
#  = do_nothing

# TODO implement thread tracing (maybe in a database?) based on threading.setprofile

