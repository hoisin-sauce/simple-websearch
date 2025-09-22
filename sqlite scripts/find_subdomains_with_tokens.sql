SELECT
	url,
	extension,
	(SELECT pagerank
	FROM Subdomain s
	WHERE s.url = url
	AND s.extension = extension) as pagerank
FROM
	TokenSubdomainLink
WHERE
	token IN (
SELECT token
FROM Token
WHERE text in ({token_amount}))