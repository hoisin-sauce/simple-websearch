DELETE FROM SubdomainSubdomainLink
WHERE origin_url=? AND origin_extension=? AND Concat(target_url, target_extension) NOT IN ({new_urls})