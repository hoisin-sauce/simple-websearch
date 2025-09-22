DELETE FROM TokenSubdomainLink
WHERE url=? AND extension=? AND token NOT IN (
    SELECT token
    FROM Token
    WHERE text IN ({new_tokens})
)