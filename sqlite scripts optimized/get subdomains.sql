SELECT
    *,
    (SELECT url FROM Website WHERE id=site_id) AS url
FROM
    Subdomain
WHERE
    next_check <> '1970-01-01'
ORDER BY site_id, extension ASC
LIMIT
    ?
OFFSET
    ?