UPDATE Subdomain
SET pagerank=(
    SELECT pagerank
    FROM TemporarySubdomainRank
    WHERE Subdomain.url=TemporarySubdomainRank.url
    AND Subdomain.extension=TemporarySubdomainRank.extension
)
WHERE EXISTS (
    SELECT 1
    FROM TemporarySubdomainRank
    WHERE Subdomain.url=TemporarySubdomainRank.url
    AND Subdomain.extension=TemporarySubdomainRank.extension
)
