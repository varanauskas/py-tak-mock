# Python TAK mock

A simplified example of how to mock CoT points can be broadcast to a TLS (SSL) TAK server using python

## Running

Enter domain, username and password when required
1. Run `enroll.py` to generate `client_cert.pem` and `client_key.pem`
2. Run `mock.py` to send mock CoT points to a TAK server

## Notes

Tested with OpenTakServer 1.7.7

Not production ready, errors unhandled, just a simple sample

A lof of assumptions have been made (for example Marti api being available on port 8446, or a TLS CoT server being available at port 8089)

Based on: https://github.com/snstac/pytak
License: Apache-2.0

