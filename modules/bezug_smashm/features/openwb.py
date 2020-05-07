"""
 * Feature-Module for SMA-EM daemon
 * Simple measurement to file writer
 * by Wenger Florian 2018-01-30
 *
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
 */
"""

import os,time

basepath="/var/www/html/openWB/ramdisk/"
mapping      = { 'evuhz':   'frequency' }
phasemapping = { 'bezuga%i': { 'from': 'i%i', 'sign': True },
                 'evuv%i':   { 'from': 'u%i'   },
                 'evupf%i':  { 'from': 'cosphi%i' }
               }

def writeToFile(filename, content):
    """Write content to file"""
    with open(filename, 'w') as f:
        f.write(str(content))

def run(emparts, config):
    global basepath
    serial=config['serial']
    if serial == "none" or serial == format(emparts['serial']):
        ts=(format(time.strftime("%H:%M:%S", time.localtime())))
        watt=int(emparts['pconsume'])
        positive = [1] * 4
        if watt < 5:
            watt=-int(emparts['psupply'])
            positive[0] = -1
        writeToFile(basepath + 'wattbezug', watt)
        writeToFile(basepath + 'einspeisungkwh', emparts['psupplycounter'] * 1000)
        writeToFile(basepath + 'bezugkwh', emparts['pconsumecounter'] * 1000)
        for phase in [1,2,3]:
            power = int(emparts['p%iconsume' % phase])
            if power < 5:
                power = -int(emparts['p%isupply' % phase])
                positive[phase] = -1
            writeToFile(basepath + 'bezugw%i' % phase, power)
        for filename, phasemap in phasemapping.items():
            for phase in [1,2,3]:
                if phasemap['from'] % phase in emparts:
                    value = emparts[phasemap['from'] % phase]
                    if 'sign' in phasemap and phasemap['sign']:
                       value *= positive[phase]
                    writeToFile(basepath + filename % phase, value)
        for filename, key in mapping.items():
            if key in emparts:
                writeToFile(basepath + filename, emparts[key])

def stopping(emparts,config):
    print("quitting")
    #close files
def config(config):
    pass
