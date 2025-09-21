SELECT
    url,
    extension,
    checked,
    checked < datetime('now') AS needsChecking
FROM
    Subdomain
WHERE
    url=?
AND
    extension=?