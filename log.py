def do_nothing(*args, **kwargs):
    del args, kwargs # ignore for reason
    pass

# TODO not be lazy and write logging properly
# log = print # NOLOG
log = do_nothing

# TODO implement thread tracing (maybe in a database?) based on threading.setprofile

