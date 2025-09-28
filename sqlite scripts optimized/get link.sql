SELECT
    next_check < datetime('now') AS needsChecking
FROM
    Subdomain
WHERE
    site_id = (SELECT id FROM Website WHERE url=?)
AND
    extension=?