CREATE TABLE `users` (
    id INT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    sha256 VARCHAR(64) NOT NULL,
    validator VARCHAR(64) NOT NULL,
    validation_time TIMESTAMP NOT NULL,
    salt VARCHAR(64) NOT NULL,
    admin TINYINT(1)
);

CREATE TABLE `rooms` (
    id INT PRIMARY KEY,
    name VARCHAR(256) NOT NULL,
    created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    creator INT NOT NULL,
    background_music BLOB,
    background_music_mime VARCHAR(64),
    background_image BLOB,
    background_image_mime VARCHAR(64),
    FOREIGN KEY (creator) REFERENCES users (id)
);

CREATE TABLE `message` (
    id INT PRIMARY KEY,
    content VARCHAR(1024) NOT NULL,
    tone VARCHAR(16),
    authorid INT NOT NULL,
    roomid INT NOT NULL,
    sent DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sound BLOB,
    mime VARCHAR(64),
    FOREIGN KEY (authorid) REFERENCES users (id),
    FOREIGN KEY (roomid) REFERENCES rooms (id)
);

CREATE TABLE `room_link` (
    roomid INT PRIMARY KEY,
    userid INT PRIMARY KEY,
    FOREIGN KEY (roomid) REFERENCES rooms (id),
    FOREIGN KEY (userid) REFERENCES users (id)
);

