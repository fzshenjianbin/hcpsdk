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

import threading
import socket
import logging
import dns
import dns.resolver


__all__ = ['IpsError', 'Circle', 'query']

logging.getLogger('hcpsdk.ips').addHandler(logging.NullHandler())


class IpsError(Exception):
    """
    Signal an error in 'ips' - typically a name resolution problem.
    """
    def __init__(self, reason):
        self.args = reason,
        self.reason = reason


# noinspection PyTypeChecker
class Circle(object):
    """
    Resolve an FQDN (through **query()**), cache the acquired IP addresses and
    yield them round-robin.
    """
    __EMPTY_ADDRLIST = []

    def __init__(self, fqdn, port=443):
        '''
        :param fqdn: the FQDN to be resolved
        :param port: the port to be used by the **hcpsdk.target** object
        '''
        self.__authority = fqdn
        self.__port = port
        self._cLock = threading.Lock()
        self.__generator = None
        self._addresses = Circle.__EMPTY_ADDRLIST.copy()
        self.logger = logging.getLogger('hcpsdk.ips.Circle')


        # initial lookup, build the address cache
        self._addr(fqdn=self.__authority)

    def _addr(self, fqdn=None):
        """
        If called with a dnsname (FQDN), query DNS for that name,
        cache the acquired IP addresses.
        If called without dnsname, work as a generator that yields the
        cached IP addresses in a round-robin fashion.

        .. Warning::
            This method is intended to be internal to **hcpsdk** and may be used
            from the outside *without* parameters, only.

        :param fqdn:    the FQDN
        :return:        an IP address (as string)
        """
        def __addr(dnsname):
            '''
            resolve HCPs IP addresses and build a list with all IPs gathered
            '''
            self._addresses = Circle.__EMPTY_ADDRLIST.copy()
            answer = Circle.__EMPTY_ADDRLIST.copy()
            result = query(dnsname, cache=True)
            if result.raised:
                raise IpsError(result.raised)
            self._addresses = result.ips.copy()

            while True:
                for ipadr in self._addresses:
                    yield str(ipadr)

        # acquire a lock to make sure that one request gets serviced at a time
        self._cLock.acquire()
        if fqdn:
            self.__generator = __addr(fqdn)
        myaddr = next(self.__generator)
        self._cLock.release()
        return myaddr


    def refresh(self):
        """
        Force a fresh DNS query and rebuild the cached list of IP addresses
        """
        self._addr(fqdn=self.__authority)


    def __getattr__(self, item):
        """
        Used to make _addresses a read-only attributes
        """
        if item == '_addresses':
            return self._addresses
        else:
            raise AttributeError

    def __str__(self):
        return(self.answer.qname)


class response(object):
    '''
    DNS query response object, returned by the **query()** function.
    '''
    def __init__(self, fqdn, cache):
        '''
        :param fqdn:    the FQDN for the response
        :param cache:   response from a query by-passing the local DNS cache (False)
                        or using the system resolver (True)
        '''
        self.fqdn = fqdn
        self.cache = cache
        self.ips = []
        self.raised = ''


def query(fqdn, cache=False):
    '''
    Submit a DNS query, using *socket.getaddrinfo()* if cache=True, or
    *dns.resolver.query()* if cache=False.

    :param fqdn:    a FQDN to query DNS
    :param cache:   if True, use the system resolver (which might do local caching),
                    else use an internal resolver, bypassing any cache available
    :return:        an **hcpsdk.ips.response** object
    :raises:        should never raise, as Exceptions are signaled through
                    the **response.raised** attribute
    '''
    _response = response(fqdn, cache) # to collect the resolved IP addresses

    if cache:
        try:
            ips = socket.getaddrinfo(fqdn, 443, family=socket.AF_INET, type=socket.SOCK_DGRAM)
        except Exception as e:
            _response.raised = str(e)
        else:
            for a in ips:
                _response.ips.append(a[4][0])
    else:
        try:
            ips = dns.resolver.query(fqdn, raise_on_no_answer=True)
        except dns.resolver.NXDOMAIN:
            _response.raised = 'NXDOMAIN - The query name does not exist.'
        except dns.resolver.YXDOMAIN:
            _response.raised = 'The query name is too long after DNAME substitution.'
        except dns.resolver.Timeout:
            _response.raised = 'The operation timed out.'
        except dns.resolver.NoAnswer:
            _response.raised = 'The response did not contain an answer to the question.'
        except dns.resolver.NoNameservers:
            _response.raised = 'NoNameservers - No non-broken nameservers are available to answer the query.'
        except dns.resolver.NotAbsolute:
            _response.raised = 'Raised if an absolute domain name is required but a relative name was provided.'
        except dns.resolver.NoRootSOA:
            _response.raised = 'Raised if for some reason there is no SOA at the root name. This should never happen!'
        except dns.resolver.NoMetaqueries:
            _response.raised = 'Metaqueries are not allowed.'
        except Exception as e:
            _response.raised = str(e)
        else:
            for i in ips.rrset:
                ip = str(i)
                if ip[1] == '#':
                    hx = ip[-8:]
                    ip='{}.{}.{}.{}'.format(int(hx[:2],16),  int(hx[2:4],16),
                                            int(hx[4:6],16), int(hx[6:],16))
                _response.ips.append(str(ip))
            if not len(_response.ips):
                _response.raised = 'no response'

    return(_response)

