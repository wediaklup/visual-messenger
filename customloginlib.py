import io
import boto3
import dbconnect
from hashlib import sha256, scrypt
import random
from datetime import datetime, timedelta
import psql
from typing import Optional
import enum
import secrets
from common import BUCKET, S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY, s3_url_for


s3 = boto3.client("s3", aws_access_key_id=S3_ACCESS_KEY, aws_secret_access_key=S3_SECRET_KEY, endpoint_url=S3_ENDPOINT)


class LoginResponse:
    def __init__(self, valid: bool, data: str):
        self.valid = valid
        self.data = data


class User(psql.SQLObject):
    SERVER_NAME = "hector"
    SCHEMA_NAME = "visual_messenger"
    TABLE_NAME = "users"
    SQL_KEYS = ["id", "name", "sha256", "validator", "validation_time", "admin", "salt"]
    PRIMARY_KEY = SQL_KEYS[0]

    def __init__(self, _id: int, name: str, sha256: str, validator: Optional[str], validation_time: datetime, admin: bool, salt: str):
        self.id = _id
        self.name = name
        self.sha256 = sha256
        self.validator = validator
        self.validation_time = validation_time
        self.admin = admin
        self.salt = salt

    @staticmethod
    def construct(response) -> list:
        return [User(x[0], x[1], x[2], x[3], x[4], x[5], x[6]) for x in response]

    def __get_endpoint(self, tone_indicator: str) -> str:
        return s3_url_for(f"sprite-{self.id}-{tone_indicator}")

    def get_mime(self, tone_indicator: str) -> str:
        return self._db().query("SELECT mime_%s FROM user_mime_link WHERE userid = %s", (tone_indicator, self.id))[0][0]

    def get_img(self, tone_indicator: str) -> io.BytesIO:
        buffer = io.BytesIO()
        s3.download_fileobj(BUCKET, self.__get_endpoint(tone_indicator), buffer)
        buffer.seek(0)
        return buffer

    def upload_img(self, tone_indicator: str, buffer, mime: str) -> None:
        self._db().query("UPDATE TABLE user_mime_link SET mime_%s = %s WHERE userid = %s", (tone_indicator, mime, self.id))
        buffer.seek(0)
        s3.upload_fileobj(buffer, BUCKET, self.__get_endpoint(tone_indicator))


def login(username, password, register=False) -> LoginResponse:
    """:param password is raw"""
    db = dbconnect.Adapter("hector", "visual_messenger")

    if register:
        res = db.query(f"SELECT COUNT(`name`) FROM `users` WHERE `name` = '{dbconnect.escape(username)}';")
        if res[0][0] == 1 or len(username) < 3:
            return LoginResponse(False, "Name already in use or invalid")
        salt = secrets.token_hex()
        password_hash = scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=4096, r=32, p=2).hex()
        db.query(f"INSERT INTO `users` (`name`, `sha256`, `salt`) VALUES ('{dbconnect.escape(username)}', '{password_hash}', '{salt}');")

        User._db().query("INSERT INTO user_mime_link (userid) VALUES (%s)", (User.get(name=username).id,))

    # login
    # check username existing
    res = db.query(f"SELECT COUNT(`name`) FROM `users` WHERE `name` = '{dbconnect.escape(username)}';")
    if res[0][0] != 1:
        return LoginResponse(False, "Name does not exist")

    salt = User.get(name=username).salt

    # check passwort correct
    res = db.query(f"SELECT `sha256` FROM `users` WHERE `name` = '{dbconnect.escape(username)}';")
    password_hash = scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=4096, r=32, p=2).hex()
    if res[0][0] != password_hash:
        return LoginResponse(False, "Invalid password")

    # get old validator
    res = db.query(f"SELECT `validator`, `validation_time` FROM `users` WHERE `name` = '{dbconnect.escape(username)}';")
    # if validator is still valid refresh time
    if (datetime.utcnow() - res[0][1]) < timedelta(hours=1):
        db.query(f"UPDATE `users` SET `validation_time` = CURRENT_TIMESTAMP() WHERE `name` = '{dbconnect.escape(username)}';")
        return LoginResponse(True, res[0][0])

    # if no validator exists generate validator
    validator = "0"
    while True: # bis der validator unique ist
        validator = sha256(random.randbytes(256)).hexdigest()
        res = db.query(f"SELECT COUNT(`validator`) FROM `users` WHERE `validator` = '{validator}'")
        if res[0][0] == 0:
            break
    # safe validator and timestamp
    db.query(f"UPDATE `users` SET `validator` = '{validator}', `validation_time` = CURRENT_TIMESTAMP() WHERE `name` = '{dbconnect.escape(username)}'")
    # set cookie validator
    return LoginResponse(True, validator)


def logoff(validator):
    """Removes validator from database"""
    db = dbconnect.Adapter("hector", "visual_messenger")
    db.query(f"UPDATE `users` SET `validator` = Null, `validation_time` = '2000-01-01 00:00:00' WHERE `validator` = '{validator}'")


def get_login(validator):
    """Returns None or the current user. Resets logoff timer"""
    if validator is None:
        return None
    try:
        user = User.get(validator=validator)
    except KeyError:
        return None

    if (datetime.utcnow() - user.validation_time) < timedelta(hours=1):
        user.validation_time = datetime.utcnow()
        user.commit()
        return user

