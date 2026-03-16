from cryptography.hazmat.primitives import serialization, hashes

def create_and_enroll_client_certificate(domain, enrollment_port, username, password, ssl_verify=True):
    import ssl
    from urllib import request
    from urllib.request import Request, urlopen
    from xml.etree import ElementTree as ET
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa
    import json

    ssl_context = None if ssl_verify else ssl._create_unverified_context()
    tls_config_opener = request.build_opener(request.HTTPSHandler(context=ssl_context))
    tlsConfig = ET.parse(tls_config_opener.open(f"https://{domain}:{enrollment_port}/Marti/api/tls/config"))

    rfc_4514_string = f"CN={username}"
    for elem in tlsConfig.getroot().iter():
        if (elem.tag.endswith("nameEntry")):
            name = elem.get("name", False)
            value = elem.get("value", False)
            if name and value:
                rfc_4514_string += f",{name}={value}" #TODO: Handle escaping of special characters in value

    subject = x509.Name.from_rfc4514_string(rfc_4514_string)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(private_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)

    req = Request(f"https://{domain}:{enrollment_port}/Marti/api/tls/signClient/v2", data=csr, method="POST")
    req.add_header("Content-Type", "application/pkcs10")
    req.add_header("Authorization", f"Basic {request.base64.b64encode(f'{username}:{password}'.encode()).decode()}")
    with urlopen(req, context=ssl_context) as response:
        data = json.load(response)
        signed_cert_pem = f"-----BEGIN CERTIFICATE-----\n{data.get('signedCert').replace('\\n', '\n')}\n-----END CERTIFICATE-----"
        ca_pems = []
        i = 0
        while f"ca{i}" in data:
            ca_pems.append(f"-----BEGIN CERTIFICATE-----\n{data[f'ca{i}'].replace('\\n', '\n')}\n-----END CERTIFICATE-----")
            i += 1

        certificate = x509.load_pem_x509_certificate(signed_cert_pem.encode("utf-8"))

        ca_certificates = []
        for i, ca_pem in enumerate(ca_pems):
            ca_cert = x509.load_pem_x509_certificate(ca_pem.encode("utf-8"))
            ca_certificates.append(ca_cert)

        return private_key, certificate, ca_certificates
    
if __name__ == "__main__":
    enrollment_port = 8446
    domain = input("Domain: ")
    username = input("Username: ")
    password = input("Password: ")
    private_key, certificate, ca_certificates = create_and_enroll_client_certificate(domain, enrollment_port, username, password)
    with open("client_cert.pem", "wb") as f:
        f.write(certificate.public_bytes(serialization.Encoding.PEM) + b"".join(ca_cert.public_bytes(serialization.Encoding.PEM) for ca_cert in ca_certificates))
    with open("client_key.pem", "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(), #TODO: Support encrypted private key
        ))