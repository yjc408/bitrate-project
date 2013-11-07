#!/usr/bin/python
# -*- coding: cp1252 -*-
# <PythonProxy.py>
#
#Copyright (c) <2009> <F�bio Domingues - fnds3000 in gmail.com>
#
#Permission is hereby granted, free of charge, to any person
#obtaining a copy of this software and associated documentation
#files (the "Software"), to deal in the Software without
#restriction, including without limitation the rights to use,
#copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the
#Software is furnished to do so, subject to the following
#conditions:
#
#The above copyright notice and this permission notice shall be
#included in all copies or substantial portions of the Software.
#
#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
#EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
#OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
#NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
#WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
#OTHER DEALINGS IN THE SOFTWARE.

"""\
Copyright (c) <2009> <F�bio Domingues - fnds3000 in gmail.com> <MIT Licence>
"""

import sys
sys.path.append('../dns')
import socket, thread, select, time, random, re
from common import sendDNSQuery


__version__ = '0.1.0 Draft 1'
BUFLEN = 8192
VERSION = 'Python Proxy/'+__version__
HTTPVER = 'HTTP/1.1'
BR = []
AVG = 0
ALPHA = .3

USAGE = '%s <requesting-ip> <listen-port> <dns-ip> <dns-port> <log-file>' % (sys.argv[0])
NAME = 'server.15-441.cs.cmu.edu'
PORT = 8080

INNER_IP = '0.0.0.0'
DNS_IP = '0.0.0.0'
DNS_PORT = -1
RR_ADDR = ''
LOG_FILE = None

def getBR():
    b = BR[0]
    for i in BR:
        if i < AVG:
            b = i
    return b


class ConnectionHandler:
    def __init__(self, connection, address, timeout):
        global AVG
        self.client = connection
        self.client_buffer = ''
        self.timeout = timeout
        self.method, self.path, self.protocol = self.get_base_header()
        self.method_others()
        if 'Seg' in self.path:
            t_new = int(8*float(self.cl)/float(self.req_time)/1000)
            AVG = (1-ALPHA)*AVG + ALPHA*t_new

            t = int(time.time())
            b = getBR()
            s = ' '.join([str(t),str(t_new),str(round(AVG)),str(b),RR_ADDR,self.path])
            print s
            LOG_FILE.write(s+'\n')
            #print self.path + ' --> ' + str(t_new)
            #print AVG
        self.client.close()
        self.target.close()

    def get_base_header(self):
        while 1:
            self.client_buffer += self.client.recv(BUFLEN)
            end = self.client_buffer.find('\n')
            if end!=-1:
                break
        sys.stdout.flush()
        data = (self.client_buffer[:end+1]).split()
        self.client_buffer = self.client_buffer[end+1:]
        return data

    def method_others(self):
        self._connect_target()
        path = self.path
        sys.stdout.flush()
        path = path.replace('big_buck_bunny.f4m','big_buck_bunny_nolist.f4m')
        
        b = getBR()     
        path = path.replace('1000',str(b))
        self.path = path

        self.req_start = time.time()
        self.target.send('%s %s %s\n'%(self.method, path, self.protocol)+
                         self.client_buffer)
        self.client_buffer = ''
        self._read_write()
        self.req_time = time.time() - self.req_start

    def _connect_target(self):
        global RR_ADDR
        # name = self.path.split('http://')[1].split('/')[0].split(':')[0]
        # port = 80
        # try:
        #     port = self.path.split('http://')[1].split('/')[0].split(':')[1]
        # except:
        #     pass
        if not RR_ADDR:
            RR_ADDR = sendDNSQuery(NAME, INNER_IP, DNS_IP, DNS_PORT)
        (soc_family, _, _, _, address) = socket.getaddrinfo(RR_ADDR, PORT)[0]
        self.target = socket.socket(soc_family)
        self.target.bind((INNER_IP,random.randrange(3000,10000)))
        self.target.connect(address)

    def _read_write(self):
        time_out_max = self.timeout/3
        count = 0
        self.left = 0
        while 1:
            count += 1
            (recv, _, error) = select.select([self.target], [], [self.target], 3)
            if error:
                break
            if recv:
                data = self.target.recv(BUFLEN)
                if data:
                    data = data.replace('Connection: Keep-Alive','Connection: Close')
                    try:
                        d = data.split('Content-Length: ')[1]
                        self.cl = d.split('\r\n')[0]
                    except:
                        pass
                    self.client.send(data)
                    count = 0

                    if self.left:
                        self.left = self.left - len(data)
                        if self.left <= 0:
                            return
                    if '\r\n\r\n' in data:
                        self.left = int(float(self.cl)) - len(data.split('\r\n\r\n')[1])

            if count == time_out_max:
                break

def start_server(timeout=5, handler=ConnectionHandler):
    global BR, AVG, INNER_IP, DNS_IP, DNS_PORT, LOG_FILE

    if len(sys.argv) < 6:
        print USAGE
        exit(-1)

    INNER_IP = sys.argv[1]
    DNS_IP = sys.argv[3]
    DNS_PORT = int(float(sys.argv[4]))
    LOG_FILE = open(sys.argv[5], 'w', 0)

    v = open('/var/www/vod/big_buck_bunny.f4m').read()
    vi = [m.start() for m in re.finditer('bitrate=',v)]
    for i in vi:
        BR.append(int(float(v[i+9:].split('"')[0])))
    BR = sorted(BR)
    print BR
    AVG = BR[0]

    port = int(float(sys.argv[2]))
    soc = socket.socket(socket.AF_INET)
    soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    soc.bind(('', port))
    print "Serving on %d."% port#debug
    soc.listen(0)
    while 1:
        thread.start_new_thread(handler, soc.accept()+(timeout,))
    soc.close()

if __name__ == '__main__':
    start_server()
