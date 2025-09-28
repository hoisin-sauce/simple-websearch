INSERT OR IGNORE INTO Token
(text)
VALUES
('{token}');

INSERT OR REPLACE INTO TokenOnPage
(page, token, occurrences)
VALUES
((SELECT
        id
    FROM
        Subdomain
    WHERE
        extension='{extension}'
    AND
        site_id=
            (SELECT
                id
            FROM
                Website
            WHERE
                url=:'{url}'
            )
    )
(SELECT token FROM Token WHERE text='{token}'),
'{occurrences}')