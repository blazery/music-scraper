from datetime import datetime


class VideoInfo:
    def __init__(self, item):
        self.id = item["id"]
        self.video_id = item["video_id"]
        self.title = item["title"]
        self.published_at = datetime.strptime(
            item["published_at"], "%Y-%m-%dT%H:%M:%SZ")
        self.has_been_loaded = item.get("has_been_loaded", 0)
        self.file_path = item.get("file_path", "")

        return

    def toDict(self):
        return {
            "id": self.id,
            "video_id": self.video_id,
            "title": self.title,
            "has_been_loaded": self.has_been_loaded,
            "file_path": self.file_path,
        }

    @ staticmethod
    def createTable(db):
        # check existance of tables
        db.cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='tracks'")
        exists = len(db.cur.fetchall()) == 1
        if exists == False:
            db.cur.execute("""CREATE TABLE tracks (
                            id TEXT PRIMARY KEY,
                            video_id TEXT UNIQUE,
                            title TEXT NOT NULL,
                            has_been_loaded BOOLEAN NOT NULL CHECK (has_been_loaded IN (0, 1)),
                            file_path TEXT);""")

    @ staticmethod
    def clearTable(db):
        db.cur.execute(
            """DELETE from tracks""")

    @ staticmethod
    def getModels(db):
        sql = "select * from tracks"
        db.cur.execute(sql)
        return db.cur.fetchall()

    @ staticmethod
    def getModelByIds(db, ids):
        sql = "select * from tracks WHERE id in ({seq})".format(
            seq=','.join(['?']*len(ids)))
        db.cur.execute(sql, ids)
        return db.cur.fetchall()

    @ staticmethod
    def insertModel(db, item):
        db.cur.execute(
            """INSERT into tracks (id, video_id, title, has_been_loaded, file_path)
            VALUES (:id, :video_id, :title, :has_been_loaded, :file_path);""", item.toDict())

    @ staticmethod
    def setModelLoaded(db, id, path):
        db.cur.execute(
            """
            UPDATE tracks
            SET
                has_been_loaded=1,
                file_path=?
            WHERE id=? """, path, id)
