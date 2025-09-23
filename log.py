import threading
import config

if config.Config.ENABLE_LOGGING_PROFILER.value:
    import profiler as p
    profiler = p.ProfilerHandler(
        filename=config.Config.LOG_FILE_PATH.value,
        only_relative_files=config.Config.ONLY_LOG_RELATIVE_CALLS.value,
        ignore_internal_methods=config.Config.IGNORE_INTERNAL_CALLS.value,
        auto_log_time=config.Config.LOGGING_INTERVAL.value,
        ignored_names=config.Config.IGNORE_NAMES.value,)

def log_with_thread(message):
    if threading.current_thread() == threading.main_thread():
        print(f"{threading.current_thread().name}: {message}")
        return

    if threading.current_thread().name.split("(")[1][:-1] in config.Config.ALLOWED_THREADS.value:
        print(f"{threading.current_thread().name}: {message}")
        return

    if config.Config.ALLOWED_THREADS.value == "all":
        print(f"{threading.current_thread().name}: {message}")

def do_nothing(*args, **kwargs):
    del args, kwargs # ignore for reason
    pass

log = log_with_thread


