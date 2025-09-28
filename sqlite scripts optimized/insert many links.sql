INSERT INTO Link
(source, target, occurrences)
VALUES
(
    (SELECT
        id
    FROM
        Subdomain
    WHERE
        extension=:origin_extension
    AND
        site_id=
            (SELECT
                id
            FROM
                Website
            WHERE
                url=:origin_url
            )
    ),(SELECT
        id
    FROM
        Subdomain s
    WHERE
        extension=:target_extension
    AND
        site_id=
            (SELECT
                id
            FROM
                Website
            WHERE
                url=:target_url
            )
    ),:occurrences)