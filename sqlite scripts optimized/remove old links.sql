DELETE FROM Link
WHERE
source=(SELECT
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
))