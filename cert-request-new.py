#!/usr/bin/python
# -*- coding: utf-8 -*-

# $Id: HostCertRequest.py 15033 2012-06-18 18:21:54Z jeremy $

"""
This script is used to request a certificate and the intended user for this script is a registered user with OIM.

"""

import urllib
import httplib
import sys
import ConfigParser
import argparse
import json
import OpenSSL
from OpenSSL import crypto
from certgen import *
import os

# Set up Option Parser
#

parser = argparse.ArgumentParser()
parser.add_argument(
    '-c',
    '--csr',
    action='store',
    dest='csr',
    default='gennew.csr',
    help='Specify CSR name (default = gennew.csr)',
    metavar='CSR',
    )
parser.add_argument(
    '-k',
    '--key',
    action='store',
    dest='prikey',
    default='genprivate.key',
    help='Specify Private Key Name (default=genprivate.key) optional',
    metavar='PRIKEY',
    )
parser.add_argument(
    '-pk',
    '--pkey',
    action='store',
    dest='userprivkey',
    required=False,
    help="Specify Requestor's private key (PEM Format). If not specified will take the value of X509_USER_KEY or $HOME/.globus/userkey.pem"
        ,
    metavar='PKEY',
    default='',
    )
parser.add_argument(
    '-ce',
    '--cert',
    action='store',
    dest='usercert',
    required=False,
    help="Specify Requestor's certificate (PEM Format). If not specified will take the value of X509_USER_KEY or $HOME/.globus/userkey.pem"
        ,
    metavar='CERT',
    default='',
    )
parser.add_argument(
    '-t',
    '--hostname',
    action='store',
    dest='hostname',
    required=True,
    help='Specify hostname for CSR (FQDN)',
    metavar='CN',
    )
parser.add_argument(
    '-e',
    '--email',
    action='store',
    dest='email',
    required=True,
    help='Email address to receive certificate',
    metavar='EMAIL',
    )
parser.add_argument(
    '-n',
    '--name',
    action='store',
    dest='name',
    required=True,
    help='Name of user receiving certificate',
    metavar='NAME',
    )
parser.add_argument(
    '-p',
    '--phone',
    action='store',
    dest='phone',
    required=True,
    help='Phone number of user receiving certificate',
    metavar='PHONE',
    )
parser.add_argument(
    '-q',
    '--quiet',
    action='store_false',
    dest='verbose',
    default=True,
    help="don't print status messages to stdout",
    )
args = parser.parse_args()

################# Config items for key file write#########

ext = 'pem'
kname = 'hostkeyfile'

##########################################################

global csr, prikey, hostname, email, name, phone
csr = args.csr

if args.userprivkey == '':
    try:
        userprivkey = os.environ('X509_USER_KEY')
    except:
        userprivkey = str(os.environ('HOME')) + '/.globus/userkey.pem'
else:
    userprivkey = args.userprivkey

if os.path.exists(userprivkey):
    pass
else:
    sys.exit('Unable to locate the private key file:' + userprivkey)

if args.usercert == '':
    try:
        usercert = os.environ('X509_USER_CERT')
    except:
        usercert = str(os.environ('HOME')) + '/.globus/usercert.pem'
else:
    usercert = args.usercert

if os.path.exists(usercert):
    pass
else:
    sys.exit('Unable to locate the user certificate file:' + usercert)

prikey = args.prikey

hostname = args.hostname
email = args.email
name = args.name
phone = args.phone

# Build the dictionary to feed into the CSR creation

config_items = {'CN': hostname, 'emailAddress': email}

#
# Read from the ini file (OSGTools.ini)
# We get the actual host url and whether it's http or https from there as well
# as the URL for the request
#

Config = ConfigParser.ConfigParser()
Config.read('OSGTools.ini')
host = Config.get('OIMData', 'hostsec')
requrl = Config.get('OIMData', 'requrl')
content_type = Config.get('OIMData', 'content_type')


# Build the connection to the web server - the request header, the parameters
# needed and then pass them into the server
#
# The data returned is in JSON format so to make it a little more human
# readable we pass it through the json module to pretty print it
#

def connect():
    print '\nConnecting to server...'
    params = urllib.urlencode({
        'name': name,
        'email': email,
        'phone': phone,
        'csrs': csr,
        })
    headers = {'Content-type': content_type,
               'User-Agent': 'OIMGridAPIClient/0.1 (OIM Grid API)'}
    conn = httplib.HTTPSConnection(host, key_file=userprivkey,
                                   cert_file=usercert)
    try:
        conn.request('POST', requrl, params, headers)
        response = conn.getresponse()
    except httplib.HTTPException, e:
        print 'Connection to %s failed: %s' % (requrl, e)
        raise e
    if not 'OK' in response.reason:
        print response.status, response.reason
        sys.exit(1)
    data = response.read()
    conn.close()
    print json.dumps(json.loads(data), sort_keys=True, indent=2)


if __name__ == '__main__':

        #
        # Three options for the CSR request
        # 1. User provides neither private key nor CSR
        # 2. User provides private key but need to create the CSR
        # 3. User provides both private key and CSR and we just need to
        #    dump it and strip the text lines for the server
        #

    if prikey == 'genprivate.key' and csr == 'gennew.csr':
        genprivate = createKeyPair(TYPE_RSA, 2048)
        keyname = kname + '.' + ext

      # #### Writing private key####

        privkey = open(keyname, 'wb')
        key = \
            OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                genprivate)
        privkey.write(key)
        privkey.close()
        new_csr = createCertRequest(genprivate, digest='sha1',
                                    **config_items)
        csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM,
                new_csr)
        csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n', ''
                          ).replace('-----END CERTIFICATE REQUEST-----\n'
                                    , '')
        connect()
    elif prikey != 'genprivate.key':
        private_key = crypto.load_privatekey(crypto.FILETYPE_PEM,
                open(prikey, 'r').read())
        new_csr = createCertRequest(private_key, digest='sha1',
                                    **config_items)
        csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM,
                new_csr)
        csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n', ''
                          ).replace('-----END CERTIFICATE REQUEST-----\n'
                                    , '')
        connect()
    else:
        new_csr = crypto.load_certificate_request(crypto.FILETYPE_PEM,
                open(csr, 'r').read())
        csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM,
                new_csr)
        csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n', ''
                          ).replace('-----END CERTIFICATE REQUEST-----\n'
                                    , '')
        connect()
    sys.exit(0)
