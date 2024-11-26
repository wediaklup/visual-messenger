import datetime as dt
import psql

SERVERNAME = "hector"
SCHEMA = "visual_messenger"


class CommonSQLObject(psql.SQLObject):
    SERVER_NAME = SERVERNAME
    SCHEMA_NAME = SCHEMA


class Message(CommonSQLObject):
    TABLE_NAME = "message"
    SQL_KEYS = ["id", "content", "tone", "authorid", "roomid", "sent", "sound", "mime"]
    PRIMARY_KEY = SQL_KEYS[0]

    def __init__(self, _id: int, content: str, tone: str, authorid: int, roomid: int, sent: dt.datetime,
                 sound: bytes, mime: str) -> None:
        super().__init__()
        self.id = _id
        self.content = content
        self.tone = tone
        self.authorid = authorid
        self.roomid = roomid
        self.sent = sent
        self.sound = sound
        self.mime = mime

    @staticmethod
    def construct(response) -> list:
        return [Message(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for x in response] 


class Room(CommonSQLObject):
    TABLE_NAME = "rooms"
    SQL_KEYS = ["id", "name", "created", "creator", "background_music", "background_music_mime",
                "background_image", "background_image_mime"]
    PRIMARY_KEY = SQL_KEYS[0]

    def __init__(self, id: int, name: str, created: dt.datetime, creator: int, background_music: bytes,
                 background_music_mime: str, background_image: bytes, background_image_mime: str) -> None:
        super().__init__()
        self.id = id
        self.name = name
        self.created = created
        self.creator = creator
        self.background_music = background_music
        self.background_music_mime = background_music_mime
        self.background_image = background_image
        self.background_image_mime = background_image_mime

    @staticmethod
    def construct(response):
        return [Room(x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]) for x in response]

    def get_permitted_users(self) -> list:
        return [x[0] for x in self._db().query("SELECT userid FROM room_link WHERE roomid = %s", (self.id,))]

    def is_available_for_user(self, userid: int) -> bool:
        return userid in self.get_permitted_users()
