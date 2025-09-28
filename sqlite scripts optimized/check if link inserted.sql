SELECT *
FROM Link
WHERE
source = (SELECT id FROM Subdomain WHERE extension=:origin_extension AND site_id = (SELECT id FROM Website WHERE url=:origin_url))
AND
target = (SELECT id FROM Subdomain WHERE extension=:target_extension AND site_id = (SELECT id FROM Website WHERE url=:target_url))