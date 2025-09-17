DROP TABLE IF EXISTS Token;
DROP TABLE IF EXISTS Website;
DROP TABLE IF EXISTS Subdomain;
DROP TABLE IF EXISTS TokenSubdomainLink;

CREATE TABLE Token(
    token INTEGER PRIMARY KEY AUTOINCREMENT,
    text VARCHAR(20) UNIQUE
);

CREATE TABLE Website(
    url TEXT PRIMARY KEY NOT NULL UNIQUE
);

CREATE TABLE Subdomain(
    extension TEXT NOT NULL,
    url TEXT NOT NULL,
    checked DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (url) REFERENCES Website(url)
);

CREATE TABLE TokenSubdomainLink(
    extension TEXT NOT NULL,
    url TEXT NOT NULL,
    token INTEGER NOT NULL,
    occurrences INTEGER NOT NULL,
    FOREIGN KEY (extension, url) REFERENCES Subdomain(extension, url),
    FOREIGN KEY (token) REFERENCES Token(token),
    PRIMARY KEY (extension, url, token)
);
