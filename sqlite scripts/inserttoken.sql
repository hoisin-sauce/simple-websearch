INSERT OR IGNORE INTO Token
(text)
VALUES
('{token}');

INSERT OR REPLACE INTO TokenSubdomainLink
(extension, url, token, occurrences)
VALUES
('{extension}',
'{url}',
(SELECT token FROM Token WHERE text='{token}'),
'{occurrences}')