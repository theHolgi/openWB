#!/usr/bin/env python3
# coding=utf-8
import binascii
import socket

from batriumdecoder import *

ipbind = '0.0.0.0'
BCASTPORT = 18542

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', BCASTPORT))

while True:
   packet = sock.recv(1024)
   parts = decode_batrium(packet)
   if parts:
      print (parts)

# Test-datagram
#packet = \
#b'\x3a\x32\x57\x2c\x47\x23\x8a\x93\x53\x59\x53\x39\x30\x33\x31\x00\x03\x05\x03\x05\x1b\x0f\xfe\x5f\x03\x00\x01\x04\x00\x01\x00\x6c' +\
#b'\x0d\xbf\x0d\xa2\x0d\x2b\x0f\xf1\x01\x31\xf6\x14\x8d\x07\xe3\xc2\x02\x23'

infoasci=binascii.b2a_hex(packet)




print ('----raw-output---')
print (packet)
print ('----asci-output---')
print (infoasci)
print ('Decoded: ')
print (parts)
