import sqlite3


class DbApi:

    def __init__(self, db_path) -> None:
        self.con = sqlite3.connect(db_path)
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        pass

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.con.commit()
        self.con.close()
