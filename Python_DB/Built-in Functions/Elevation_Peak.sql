SELECT
    concat(elevation, ' ', repeat('-', 3), repeat('>', 2), ' ', peak_name)
FROM
    peaks
WHERE
    elevation >= 4884