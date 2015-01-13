# -*- coding: utf-8 -*-
# The MIT License (MIT)
#
# Copyright (c) 2014-2015 Thorsten Simons (sw@snomis.de)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
# FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
# IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import hcpsdk
import xml.etree.ElementTree as ET
from collections import OrderedDict
import logging

__all__ = ['info']

logging.getLogger('hcpsdk.namespace').addHandler(logging.NullHandler())


class info(object):
    '''
    Class to access namespaces metadata information
    '''

    def __init__(self, target, debuglevel=0):
        '''
        :param target:      an **hcpsdk.target** object
        :param debuglevel:  0..9 (propagated to *http.client*)
        '''
        self.target = target
        self.debuglevel = debuglevel
        self.connect_time = 0.0
        self.service_time = 0.0
        self.logger = logging.getLogger('hcpsdk.namespace.info')


    def NSstatistics(self):
        '''
        Query for namespace statistic information

        :return:  a dict holding the stats
        :raises: hcpsdk.HcpsdkError()
        '''
        d = None
        try:
            con = hcpsdk.connection(self.target, debuglevel=self.debuglevel)
        except Exception as e:
            raise hcpsdk.HcpsdkError(str(e))
        else:
            self.connect_time = con.connect_time
            try:
                r = con.request('GET', '/proc/statistics')
            except Exception as e:
                raise hcpsdk.HcpsdkError(str(e))
            else:
                if r.status == 200:
                    # Good status, get and parse the response
                    x = r.read()
                    self.service_time = con.service_time2
                    root = ET.fromstring(x)
                    d = root.attrib
                    tobedel = None
                    for i in d.keys():
                        if i.startswith('{http'):
                            tobedel = i
                        else:
                            d[i] = self._castVar(d[i])
                    if tobedel:
                        del d[tobedel]
                else:
                    raise(hcpsdk.HcpsdkError('{} - {}'.format(r.status, r.reason)))
        finally:
            con.close()
            return d


    def listAccessibleNS(self, all=False):
        '''
        List the settings of the actual (or all accessible namespace(s).

        :param all:     list all accessible namespaces if True, else list the
                        actual one, only.
        :return:        a dict holding a dict per namespace
        '''
        if not all:
            path = '/proc'
        else:
            path = '/proc/?single=true'
        try:
            con = hcpsdk.connection(self.target, debuglevel=self.debuglevel)
        except Exception as e:
            raise hcpsdk.HcpsdkError(str(e))
        else:
            self.connect_time = con.connect_time

            try:
                r = con.request('GET', path)
            except Exception as e:
                raise hcpsdk.HcpsdkError(str(e))
            else:
                if r.status == 200:
                    # Good status, get and parse the response
                    x = r.read()
                    self.service_time = con.service_time2
                    root = ET.fromstring(x)
                    d = OrderedDict()
                    for n in root:
                        d[n.attrib.get('name')] = n.attrib
                        for i in d[n.attrib.get('name')].keys():
                            d[n.attrib.get('name')][i] =\
                                self._castVar(d[n.attrib.get('name')][i])
                        for n1 in n:
                            d[n.attrib['name']]['description'] = n1.text.strip().split('°')
                else:
                    raise(hcpsdk.HcpsdkError('{} - {}'.format(r.status, r.reason)))
        finally:
            con.close()
            return d

    def listRetentionClasses(self):
        '''
        List the Retention Classes available for the actual namespace.

        :return: a dict holding a dict per Retention Class
        '''
        try:
            con = hcpsdk.connection(self.target, debuglevel=self.debuglevel)
        except Exception as e:
            raise hcpsdk.HcpsdkError(str(e))
        else:
            self.connect_time = con.connect_time

            r = con.request('GET', '/proc/retentionClasses')
            if r.status == 200:
                # Good status, get and parse the response
                x = r.read()
                self.service_time = con.service_time2
                root = ET.fromstring(x)
                d = OrderedDict()
                for n in root:
                    d[n.attrib.get('name')] = n.attrib
                    for i in d[n.attrib.get('name')].keys():
                        d[n.attrib.get('name')][i] =\
                            self._castVar(d[n.attrib.get('name')][i])
                    for n1 in n:
                        d[n.attrib.get('name')]['description'] = n1.text.strip()
            else:
                raise(hcpsdk.HcpsdkError('{} - {}'.format(r.status, r.reason)))
        finally:
            con.close()
            return d


    def listPermissions(self):
        '''
        List the namespace and user permissions for the actual namespace.

        :return: a dict holding a dict per permission domain
        '''
        try:
            con = hcpsdk.connection(self.target, debuglevel=self.debuglevel)
        except Exception as e:
            raise hcpsdk.HcpsdkError(str(e))
        else:
            self.connect_time = con.connect_time

            r = con.request('GET', '/proc/permissions')
            if r.status == 200:
                # Good status, get and parse the response
                x = r.read()
                self.service_time = con.service_time2
                root = ET.fromstring(x)
                d = OrderedDict()
                for n in root:
                    d[n.tag] = n.attrib
                    for i in d[n.tag].keys():
                        d[n.tag][i] = self._castVar(d[n.tag][i])
            else:
                raise(hcpsdk.HcpsdkError('{} - {}'.format(r.status, r.reason)))
        finally:
            con.close()
            return d


    def _castVar(self, var):
        '''
        Cast a value to the right type.
        :param var: a string
        :return: the casted value
        '''
        if var == 'true':
            return True
        elif var == 'false':
            return False
        else:
            try:
                return int(var)
            except ValueError:
                return var
