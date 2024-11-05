import dbconnect
from hashlib import sha256, scrypt
import random
from datetime import datetime, timedelta
import psql
from typing import Optional
import enum
import secrets


class LoginResponse:
    def __init__(self, valid: bool, data: str):
        self.valid = valid
        self.data = data


class User(psql.SQLObject):
    SERVER_NAME = "hector"
    SCHEMA_NAME = "visual_messenger"
    TABLE_NAME = "users"
    SQL_KEYS = ["id", "name", "sha256", "validator", "validation_time", "salt"]
    PRIMARY_KEY = SQL_KEYS[0]

    def __init__(self, _id: int, name: str, sha256: str, validator: Optional[str], validation_time: datetime, salt: str):
        self.id = _id
        self.name = name
        self.sha256 = sha256
        self.validator = validator
        self.validation_time = validation_time
        self.salt = salt

    @staticmethod
    def construct(response) -> list:
        return [User(x[0], x[1], x[2], x[3], x[4], x[5]) for x in response]


def login(username, password, register=False) -> LoginResponse:
    """:param password is raw"""
    db = dbconnect.Adapter("belzig", "users")

    if register:
        res = db.query(f"SELECT COUNT(`name`) FROM `users` WHERE `name` = '{dbconnect.escape(username)}';")
        if res[0][0] == 1 or len(username) < 3:
            return LoginResponse(False, "Name already in use or invalid")
        salt = secrets.token_hex()
        password_hash = scrypt(password.encode("utf-8"), salt=salt.encode("utf-8"), n=4096, r=32, p=2).hex()
        db.query(f"INSERT INTO `users` (`name`, `sha256`, `salt`) VALUES ('{dbconnect.escape(username)}', '{password_hash}', '{salt}');")

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
    db = dbconnect.Adapter("belzig", "users")
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

