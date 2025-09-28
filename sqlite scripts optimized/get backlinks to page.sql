SELECT
    SSL.occurrences,
    (SELECT
        pagerank
    FROM
        Subdomain
    WHERE
        id=SSL.source) AS origin_pagerank,
    (SELECT
        SUM(occurrences)
    FROM
        Link
    WHERE
        source=SSL.source
    ) AS forward_links
FROM
    Link as SSL
WHERE
    target=(
        SELECT
            id
        FROM
            Subdomain
        WHERE
            site_id=(SELECT id FROM Website WHERE url=?)
        AND
            extension=?
    )