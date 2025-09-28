DROP TABLE IF EXISTS Token;
DROP TABLE IF EXISTS Website;
DROP TABLE IF EXISTS Subdomain;
DROP TABLE IF EXISTS Link;
DROP TABLE IF EXISTS TokenOnPage;

VACUUM;

CREATE TABLE Token(
    token INTEGER PRIMARY KEY AUTOINCREMENT,
    text VARCHAR(20) UNIQUE
);

CREATE TABLE Website(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE
);

CREATE TABLE Subdomain(
    id INTEGER PRIMARY KEY AUTOINCREMENT, -- TODO causes conflicts with INSERT OR REPLACE
    site_id INTEGER NOT NULL,
    extension TEXT NOT NULL,
    next_check DATETIME DEFAULT '1970-01-01',
    pagerank REAL,
    temp_pagerank REAL,
    FOREIGN KEY (site_id) REFERENCES Website(url)
    UNIQUE (site_id, extension)
);

CREATE TABLE Link(
    source INTEGER NOT NULL,
    target INTEGER NOT NULL,
    occurrences INTEGER NOT NULL,
    FOREIGN KEY (source) REFERENCES Subdomain(id)
    FOREIGN KEY (target) REFERENCES Subdomain(id)
    UNIQUE (source, target)
);

CREATE TABLE TokenOnPage(
    page INTEGER NOT NULL,
    token INTEGER NOT NULL,
    occurrences INTEGER NOT NULL,
    FOREIGN KEY (page) REFERENCES Subdomain(id),
    FOREIGN KEY (token) REFERENCES Token(token),
    PRIMARY KEY (page, token)
);
