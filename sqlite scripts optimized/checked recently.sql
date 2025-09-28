SELECT
    next_check > datetime('now') as checked_recently
FROM
    Subdomain
WHERE
    site_id=(SELECT id FROM Website WHERE url=?)
AND
    extension=?