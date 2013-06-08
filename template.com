$$ORIGIN $origin
$$TTL $ttl

;
; BIND data file for domain $domain
;
@       IN SOA ${ns1}. ${ns2}. (
                $serial      ; serial
                21600           ; refresh (6h)
                3600            ; retry (1h)
                604800          ; expiry (7d)
                24H ) ; RR TTL (24h)
$main
$subz
