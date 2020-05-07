#!/usr/bin/env python3
# coding=utf-8
"""
 *
 * by Wenger Florian 2018-01-30
 * wenger@unifox.at
 *
 *  this software is released under GNU General Public License, version 2.
 *  This program is free software;
 *  you can redistribute it and/or modify it under the terms of the GNU General Public License
 *  as published by the Free Software Foundation; version 2 of the License.
 *  This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
 *  without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 *  See the GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License along with this program;
 *  if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
 *
 * 2020-01-04 datenschuft changes to tun with speedwiredecoder
 */
"""
import sys, time,os
from daemon3x import daemon3x
from configparser import ConfigParser
#import smaem
import socket
import struct
from speedwiredecoder import *

#read configuration
parser = ConfigParser()
#alternate config locations
parser.read(['config','config'])
try:
	smaemserials=parser.get('SMA-EM', 'serials')
except:
	print('Cannot find base config entry SMA-EM serials')
	sys.exit(1)

serials=smaemserials.split(' ')
#smavalues=parser.get('SMA-EM', 'values')
#values=smavalues.split(' ')
pidfile=parser.get('DAEMON', 'pidfile')
try:
    ipbind=parser.get('DAEMON', 'ipbind')
except:
    ipbind="0.0.0.0"
try:
    ipout = parser.get('DAEMON', 'ipout1')
except:
    ipout = None
MCAST_GRP = parser.get('DAEMON', 'mcastgrp')
MCAST_PORT = int(parser.get('DAEMON', 'mcastport'))
print("Listening on " + ipbind + " group " + MCAST_GRP)
features=parser.get('SMA-EM', 'features')
features=features.split(' ')
statusdir=''
try:
	statusdir=parser.get('DAEMON','statusdir')
except:
	statusdir="/run/shm/"

if os.path.isdir(statusdir):
	statusfile=statusdir+"em-status"
else:
	statusfile = "em-status"


import importlib

#Check features and load
featurelist = {}
featurecounter=0
for feature in features:
    #print ('import ' + feature + '.py')
    featureitem={}
    featureitem = {'name': feature}
    try:
       featureitem['feature'] = importlib.import_module('features.' + feature)
    except (ImportError, FileNotFoundError, TypeError):
       print('feature '+feature+ ' not found')
       sys.exit()
    try:
        featureitem['config']=dict(parser.items('FEATURE-'+feature))
        #print (featureitem['config'])
    except:
       print('feature '+feature+ ' not configured')
       sys.exit()
    try:
		#run config action, if any
       featureitem['feature'].config(featureitem['config'])
    except:
       pass
    featurelist[featurecounter]=featureitem
    featurecounter += 1

#set defaults
if MCAST_GRP == "":
    MCAST_GRP = '239.12.255.254'
if MCAST_PORT == 0:
    MCAST_PORT = 9522

class MyDaemon(daemon3x):
	def run(self):
		# prepare listen to socket-Multicast
		socketconnected = False
		while not socketconnected:
			#try:
			sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			sock.bind(('', MCAST_PORT))
			sockout = None
			if ipout is not None:
				sockout = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
			try:
				mreq = struct.pack("4s4s", socket.inet_aton(MCAST_GRP), socket.inet_aton(ipbind))
				sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
				with open(statusfile, "w") as f:
					f.write('multicastgroup connected')
				socketconnected = True
			except BaseException:
				print('could not connect to mulicast group... rest a bit and retry')
				file = open(statusfile, "w")
				file.write('could not connect to mulicast group... rest a bit and retry')
				file.close()
				time.sleep(5)
		emparts = {}
		while True:
			#getting sma values
			#try:
				#emparts=smaem.readem(sock)
				emparts=decode_speedwire(sock.recv(608))
				for serial in serials:
					# process only known sma serials
					if serial==format(emparts['serial']):
						# running all enabled features
						for featurenr in featurelist:
							#print('>>> starting '+featurelist[featurenr]['name'])
							featurelist[featurenr]['feature'].run(emparts,featurelist[featurenr]['config'])
						if sockout is not None:
							sockout.sendto(emparts['new_datagram'], (MCAST_GRP, MCAST_PORT))
			#except Exception as e:
			#	print("Daemon: Exception occured")
			#	print(e)
			#	pass
#Daemon - Coding
if __name__ == "__main__":
	daemon = MyDaemon(pidfile)
	if len(sys.argv) == 2:
		if 'start' == sys.argv[1]:
			daemon.start()
		elif 'stop' == sys.argv[1]:
			for featurenr in featurelist:
				print('>>> stopping '+featurelist[featurenr]['name'])
				featurelist[featurenr]['feature'].stopping({},featurelist[featurenr]['config'])
			daemon.stop()
		elif 'restart' == sys.argv[1]:
			daemon.restart()
		elif 'run' == sys.argv[1]:
			daemon.run()
		else:
			print ("Unknown command")
			sys.exit(2)
		sys.exit(0)
	else:
		print ("usage: %s start|stop|restart|run" % sys.argv[0])
		print (pidfile)
		sys.exit(2)
