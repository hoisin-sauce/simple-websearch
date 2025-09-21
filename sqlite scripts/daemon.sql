SELECT
    url,
    extension,
    url || extension AS link
FROM
    Subdomain
WHERE
    checked < datetime('now')