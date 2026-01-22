from OpenSSL import crypto
import os

# Create src directory if not exists
if not os.path.exists("src"):
    os.makedirs("src")

k = crypto.PKey()
k.generate_key(crypto.TYPE_RSA, 2048)

cert = crypto.X509()
cert.get_subject().C = 'VN'
cert.get_subject().ST = 'HCM'
cert.get_subject().L = 'HCM'
cert.get_subject().O = 'ChatAppNhom15'
cert.get_subject().OU = 'Dev'
cert.get_subject().CN = 'localhost'
cert.set_serial_number(1000)
cert.gmtime_adj_notBefore(0)
cert.gmtime_adj_notAfter(10*365*24*60*60)
cert.set_issuer(cert.get_subject())
cert.set_pubkey(k)
cert.sign(k, 'sha256')

with open('src/server.crt', 'wb') as f:
    f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert))
with open('src/server.key', 'wb') as f:
    f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k))

print('Certificates generated successfully in src/ folder.')
