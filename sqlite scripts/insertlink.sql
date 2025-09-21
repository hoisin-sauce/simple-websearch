INSERT OR IGNORE INTO Website
(url)
VALUES
('{url}');

INSERT OR REPLACE INTO Subdomain
(extension, url, checked)
VALUES
('{extension}', '{url}', '{checked}')