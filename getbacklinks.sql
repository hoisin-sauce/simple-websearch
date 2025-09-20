SELECT
    SSL.origin_url,
    SSL.origin_extension,
    SSL.occurrences,
    (SELECT
        pagerank
    FROM
        Subdomain
    WHERE
        url=?
    AND
        extension=?) AS origin_pagerank,
    (SELECT
        Count(*)
    FROM
        SubdomainSubdomainLink
    WHERE
        origin_url=SSL.origin_url
    AND
        origin_extension=SSL.origin_extension
    ) AS forward_links
FROM
    SubdomainSubdomainLink as SSL
WHERE
    target_url=?
AND
    target_extension=?