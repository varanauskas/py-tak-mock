from cryptography.hazmat.primitives import serialization, hashes

def auth_request(url, username, password, method="GET", data=None, content_type=None, ssl_context=None):
    from urllib import request
    from urllib.request import Request, urlopen

    req = Request(url, data=data, method=method)
    req.add_header("Authorization", f"Basic {request.base64.b64encode(f'{username}:{password}'.encode()).decode()}")
    if content_type:
        req.add_header("Content-Type", content_type)
    return urlopen(req, context=ssl_context)

def create_and_enroll_client_certificate(domain, enrollment_port, username, password, ssl_context=None):
    from xml.etree import ElementTree as ET
    from cryptography import x509
    from cryptography.hazmat.primitives.asymmetric import rsa
    import json

    tls_config = ET.fromstring(auth_request(
        f"https://{domain}:{enrollment_port}/Marti/api/tls/config",
        username,
        password,
        ssl_context=ssl_context
    ).read())

    rfc_4514_string = f"CN={username}"
    for elem in tls_config.iter():
        if (elem.tag.endswith("nameEntry")):
            name = elem.get("name", False)
            value = elem.get("value", False)
            if name and value:
                rfc_4514_string += f",{name}={value}" #TODO: Handle escaping of special characters in value

    subject = x509.Name.from_rfc4514_string(rfc_4514_string)

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)

    csr = x509.CertificateSigningRequestBuilder().subject_name(subject).sign(private_key, hashes.SHA256()).public_bytes(serialization.Encoding.PEM)

    with auth_request(
        f"https://{domain}:{enrollment_port}/Marti/api/tls/signClient/v2",
        username,
        password,
        method="POST",
        data=csr,
        content_type="application/pkcs10",
        ssl_context=ssl_context
    ) as response:
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
    import argparse
    parser = argparse.ArgumentParser(
        prog="enroll.py",
        description="Enroll client certificate and save it to client_cert.pem and client_key.pem",
    )
    parser.add_argument("host", nargs=1, help="Domain or IP address of the server to enroll with")
    parser.add_argument("-port", "-p", nargs="?", type=int, default=8446, help="Enrollment port of the server (default: 8446)")
    parser.add_argument("--unverified-ssl", action="store_true", help="Don't verify SSL certificate of the server (not recommended)")
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