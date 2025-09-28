INSERT OR IGNORE INTO Website
(url)
VALUES
('{url}');

INSERT OR REPLACE INTO Subdomain -- TODO rework so that replace does not change ID
(extension, site_id, next_check)
VALUES
('{extension}', (SELECT id FROM Website WHERE url='{url}'), '{checked}')