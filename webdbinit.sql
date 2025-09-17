DROP TABLE IF EXISTS Token;
DROP TABLE IF EXISTS Website;
DROP TABLE IF EXISTS Subdomain;
DROP TABLE IF EXISTS TokenSubdomainLink;

CREATE TABLE Token(
    token INTEGER PRIMARY KEY AUTOINCREMENT,
    text VARCHAR(20)
);

CREATE TABLE Website(
    url TEXT PRIMARY KEY NOT NULL UNIQUE
);

CREATE TABLE Subdomain(
    extension TEXT NOT NULL,
    url TEXT NOT NULL,
    checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (url) REFERENCES Website(url)
    PRIMARY KEY (url, extension)
);

CREATE TABLE TokenSubdomainLink(
    id INTEGER NOT NULL,
    token INTEGER NOT NULL,
    occurrences INTEGER NOT NULL,
    FOREIGN KEY (id) REFERENCES Subdomain(id),
    FOREIGN KEY (token) REFERENCES Token(token),
    PRIMARY KEY (id, token)
);
