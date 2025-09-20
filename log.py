import threading

def log_with_thread(message):
    print(f"{threading.current_thread().name}: {message}")

def do_nothing(*args, **kwargs):
    del args, kwargs # ignore for reason
    pass

# TODO not be lazy and write logging properly
log = log_with_thread # NOLOG
#  = do_nothing

# TODO implement thread tracing (maybe in a database?) based on threading.setprofile

