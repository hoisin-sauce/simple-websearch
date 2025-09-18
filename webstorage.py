import sqlite3
import threading
import inspect
import config
from typing import Callable, Iterable, Any
import os
import hashlib
import log
import queue

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

class Query:
    def __init__(self, function: Callable, *args, **kwargs):
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.result = queue.Queue()
        self.logging_stack = inspect.stack()[2:]

    def get_result(self):
        return self.result.get()

class Database:
    def __init__(self, database: str, init_script: str) -> None:
        self.init_script = init_script
        self.database = database

        # allow connection to be NoneType for initialisation within the daemon
        self.conn : sqlite3.Connection | None = None

        db_exists = self.database_exists()

        if config.Config.THREADED_SERVER_HANDLING.value:
            self.command_queue = queue.Queue()
            self.command_thread = threading.Thread(
                target=self.handle_queries, daemon=True)
            self.command_thread.name = f"{database}-thread"
            self.command_thread.start()
        else:
            self.conn = sqlite3.connect(database)
            self.conn.row_factory = dict_factory
            if config.Config.PRINT_SQL_COMMANDS.value:
                self.conn.set_trace_callback(log.log)

        if not db_exists:
            self.reset_database()

        if config.Config.AUTO_RESET_ON_DB_INIT_CHANGES.value:
            self.check_hash()

        # TODO automatic click implementation of reset command?

    def database_exists(self) -> bool:
        return os.path.isfile(self.database)

    def handle_queries(self):
        self.conn = sqlite3.connect(self.database)
        self.conn.row_factory = dict_factory

        if config.Config.PRINT_SQL_COMMANDS.value:
            self.conn.set_trace_callback(log.log)

        while True:
            query = self.command_queue.get()
            try:
                return_value = query.function(*query.args, **query.kwargs)
            except Exception as e:
                log.log(
                    f"Exception: {e} occured whilst processing "
                    f"{query.logging_stack[0]} with args "
                    f"{query.args} and kwargs {query.kwargs}")
                raise
            query.result.put(return_value)

    def get_hash(self) -> str:
        with open(self.init_script, 'rb') as f:
            sql_script = f.read()
        sql_hash = hashlib.sha256(sql_script).hexdigest()
        return sql_hash

    def check_hash(self) -> None:
        sql_hash = self.get_hash()
        try:
            rows = self.execute(config.Config.HASH_CHECK.value, params=(sql_hash,), is_file=True)
        except sqlite3.OperationalError:
            self.reset_database()
            return
        if len(rows) != 1:
            log.log("DATABASE RESET INIT HAS CHANGED")
            self.reset_database()


    def cursor_wrapper(self, func: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            cursor = self.conn.cursor()
            func(cursor, *args, **kwargs)
            self.conn.commit()
        return wrapper

    def execute_script(self, script: str,
                       params: dict[str, str] | None = None) -> None:

        if config.Config.THREADED_SERVER_HANDLING.value:
            if threading.current_thread() != self.command_thread:
                query = Query(self.execute_script, script, params=params)
                self.command_queue.put(query)
                query.get_result()
                return

        with open(script, 'r') as f:
            sql_script = f.read()

        # This is unsafe however I am lazy
        if params is not None:
            sql_script = sql_script.format(**params)

        cursor = self.conn.cursor()

        try:
            cursor.executescript(sql_script)
        except sqlite3.OperationalError:
            log.log(sql_script)
            raise

        self.conn.commit()

    def execute(self, script: str,
                params=None, is_file=False) -> list[dict[str, Any]]:

        if config.Config.THREADED_SERVER_HANDLING.value:
            if threading.current_thread() != self.command_thread:
                query = Query(self.execute, script,
                              params=params, is_file=is_file)
                self.command_queue.put(query)
                return query.get_result()

        if params is None:
            params = ()
        if is_file:
            with open(script, 'r') as f:
                sql_script = f.read()
        else:
            sql_script = script
        cursor = self.conn.cursor()
        cursor.execute(sql_script, params)
        return_value = cursor.fetchall()
        self.conn.commit()
        return return_value

    def reset_database(self):
        self.execute_script(self.init_script)
        self.execute_script(config.Config.HASH_SCRIPT.value)
        self.execute(
            config.Config.HASH_INSERT.value,
            params=(self.get_hash(),), is_file=True
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

if __name__ == '__main__':
    # Testing
    db = Database("testing.db", "webdbinit.sql")
    db.reset_database()

    @db.cursor_wrapper
    def get_shit(cursor: sqlite3.Cursor):
        cursor.execute("""INSERT INTO Website (url) VALUES (?)""", ("http://google.com",))

    @db.cursor_wrapper
    def do_shit(cursor: sqlite3.Cursor):
        cursor.execute("SELECT * FROM Website")
        log.log(cursor.fetchall())

    get_shit()
    do_shit()
