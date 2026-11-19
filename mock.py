import datetime
import argparse
import socket
import random
import uuid
import sys
import ssl

uid = str(uuid.uuid4()).upper()
callsign = "Mock " + uid[-6:] # This can be anything

lat = 55
lon = 24
hae = 125
course = 150
speed = 50
def generate_mock_point():
    global lat, lon, hae, course, speed
    lat += random.uniform(-0.001, 0.001)
    lon += random.uniform(-0.001, 0.001)
    hae += random.uniform(-0.01, 0.1)
    course += random.uniform(-0.5, 0.5)
    speed += random.uniform(-0.5, 0.5)

    print(f"Generated point: lat={lat}, lon={lon}, hae={hae}, course={course}, speed={speed}")

    now = datetime.datetime.now(datetime.timezone.utc)
    start = now.isoformat().replace('+00:00', 'Z')
    stale = (now + datetime.timedelta(seconds=10)).isoformat().replace('+00:00', 'Z')
    return f"""<?xml version="1.0" encoding="utf-8" standalone="yes"?>
    <event version="2.0" uid="{uid}" type="a-f-A-R-U" how="m-g" time="{start}" start="{start}" stale="{stale}">
        <point lat="{lat}" lon="{lon}" hae="{hae}" ce="9999999.0" le="9999999.0"/>
        <detail>
            <contact callsign="{callsign}" phone="" endpoint="*:-1:stcp"/>
            <__group name="Green" role="Team Member"/>
            <takv device="MockDrone" platform="{sys.platform}" os="{sys.api_version}" version="0.0.1"/>
            <track speed="{speed}" course="{course}"/>
            <uid Droid="{callsign}"/>
        </detail>
</event>"""

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("host", nargs="?", help="Domain or IP address of the server to enroll with")
parser.add_argument("-port", "-p", nargs="?", type=int, default=8089, help="CoT TLS port of the server")
args = parser.parse_args()
cot_port = args.port
host = args.host if args.host else input("Host: ")

context = ssl.create_default_context()
context.load_verify_locations(cafile="client_cert.pem")
try:
    context.load_cert_chain(certfile="client_cert.pem", keyfile="client_key.pem")
except FileNotFoundError:
    print("Certificate or key file not found. Please run enroll.py first to create them.")
    sys.exit(1)

server = (host, cot_port)
with socket.create_connection(server) as sock:
    with context.wrap_socket(sock, server_hostname=server[0]) as ssock:
        print(f"Connected to {server[0]}:{server[1]} {ssock.version()} as {callsign} ({uid})")
        while True:
            input("Press Enter to send next point... (Or Ctrl+C to exit)")
            ssock.send(generate_mock_point().encode())
