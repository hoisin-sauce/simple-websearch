SELECT
    checked > datetime('now') as checked_recently
FROM
    Subdomain
WHERE
    url=?
AND
    extension=?