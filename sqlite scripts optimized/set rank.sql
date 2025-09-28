UPDATE Subdomain
SET temp_pagerank = :new_rank
WHERE
extension = :extension
AND
site_id = (SELECT id FROM Website WHERE url=:url)