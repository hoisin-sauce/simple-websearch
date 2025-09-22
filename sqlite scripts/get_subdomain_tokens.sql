SELECT
    t.text AS token,
    tsl.occurrences AS occurrences
FROM
    Token t
INNER JOIN
    TokenSubdomainLink tsl
ON
    t.token = tsl.token
WHERE
    tsl.url = :url
AND
    tsl.extension = :extension