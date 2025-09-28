SELECT
    (SELECT url FROM Website WHERE id=site_id) AS url,
    extension,
    pagerank
FROM
    Subdomain
WHERE
    id IN (
    SELECT
        page
    FROM
        TokenOnPage
    WHERE
        token IN (
        SELECT
            token
        FROM
            Token
        WHERE
            text in ({token_amount})))