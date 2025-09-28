SELECT *
FROM Subdomain
WHERE extension=:extension
AND site_id = (
    SELECT id
    FROM Website
    WHERE url=:url)