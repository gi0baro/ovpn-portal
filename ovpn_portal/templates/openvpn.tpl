dev tun
persist-tun
persist-key
client
float
resolv-retry infinite
remote {{ =remote }} {{ =port }} udp
{{ if domain: }}
verify-x509-name "{{ =domain }}" name
{{ pass }}
remote-cert-tls server
cipher {{ =cipher }}
{{ for key, val in extras.items(): }}
{{ =key }} {{ =val }}
{{ pass }}

<ca>
{{ =ca }}
</ca>
<cert>
{{ =cert }}
</cert>
<key>
{{ =private_key }}
</key>
