INSERT OR IGNORE INTO Subdomain
(site_id, extension)
VALUES
((SELECT id FROM Website WHERE url=:url), :extension)