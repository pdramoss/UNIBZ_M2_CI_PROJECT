CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY,
    type VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    password VARCHAR(100) NULL,
    id_registration INT NULL,
    id_event INT NULL
);

CREATE TABLE IF NOT EXISTS events (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    capacity INT NOT NULL
);

CREATE TABLE IF NOT EXISTS registrations (
    id INT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    user_name VARCHAR(100) NOT NULL,
    FOREIGN KEY (event_id) REFERENCES events(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS session (
    id TINYINT PRIMARY KEY,
    user_id INT NULL
);
