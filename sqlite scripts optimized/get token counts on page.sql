SELECT
    t.text AS token,
    top.occurrences AS occurrences
FROM
    Token t
INNER JOIN
    TokenOnPage top
ON
    t.token = top.token
WHERE
    page = (
    SELECT
        id
    FROM
        Subdomain s
    WHERE
        s.site_id = (SELECT id FROM WEBSITE WHERE url=:url)
    AND
        s.extension = :extension)