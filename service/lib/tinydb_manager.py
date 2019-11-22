from tinydb import TinyDB, Query

class TinyDBManager:
    def __init__(self, db_file=None, default_table = None):
        if db_file:
            self._db_file = db_file
        else:
            self._db_file = r'D:\Data\TinyDB\db.json'

        self.db = TinyDB(self._db_file)
        if default_table:
            self._default_table = default_table
            self.__isConnected = True
        else:
            self.__isConnected = False
            self._default_table = None

    def connect(self, table):
        self._default_table = table
        self.__isConnected = True

    def disconnect(self):
        self._default_table = None
        self.__isConnected = False

    def getTable(self, table=None):
        if table:
            return self.db.table(table, cache_size=0)
        else:
            return self.db.table(self._default_table, cache_size=0)

    def insert(self):
        pass

    def update(self):
        pass

    def remove(self):
        pass

    def get(self):
        return self.db