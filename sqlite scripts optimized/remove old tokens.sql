DELETE FROM TokenOnPage
WHERE page=(SELECT
        id
    FROM
        Subdomain
    WHERE
        site_id=
            (SELECT
                id
            FROM
                Website
            WHERE
                url=?
    AND
        extension=?
)) AND token NOT IN (
    SELECT token
    FROM Token
    WHERE text IN ({new_tokens})
)