#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This script submits a host certificate request for an unauthenticated
user.
"""

import urllib
import httplib
import sys
import ConfigParser
import json
import OpenSSL
from OpenSSL import crypto
from OSGPKICertKeygenUtil import *  
from pprint import pprint
import os
from optparse import OptionParser

# Set up Option Parser
#
def parse_args():
    parser = OptionParser()
    parser.add_option(
        '-c',
        '--csr',
        action='store',
        dest='csr',
        default='gennew.csr',
        help='Specify CSR name (default = gennew.csr)',
        metavar='CSR',
        )
    parser.add_option(
        '-k',
        '--key',
        action='store',
        dest='prikey',
        default='genprivate.key',
        help='Specify Private Key Name (default=genprivate.key)',
        metavar='PRIKEY',
        )
    parser.add_option(
        '-o',
        '--outkeyfile',
        action='store',
        dest='keyfile',
        help='Specify the output filename for the retrieved user certificate. Default is ./host-key.pem'
            ,
        metavar='Output Keyfile',
        default='./host-key.pem',
        )
    parser.add_option(
        '-t',
        '--hostname',
        action='store',
        dest='hostname',
        help='Specify hostname for CSR (FQDN)',
        metavar='CN',
        )
    parser.add_option(
        '-e',
        '--email',
        action='store',
        dest='email',
        help='Email address to receive certificate',
        metavar='EMAIL',
        )
    parser.add_option(
        '-n',
        '--name',
        action='store',
        dest='name',
        help='Name of user receiving certificate',
        metavar='NAME',
        )
    parser.add_option(
        '-p',
        '--phone',
        action='store',
        dest='phone',
        help='Phone number of user receiving certificate',
        metavar='PHONE',
        )
    parser.add_option(
        '-q',
        '--quiet',
        action='store_false',
        dest='verbose',
        default=True,
        help="don't print status messages to stdout",
        )
    (args, values) = parser.parse_args()

    if not args.phone:
        parser.error("-p/--phone argument required")
    if not args.name:
        parser.error("-n/--name argument required")
    if not args.email:
        parser.error("-e/--email argument required")
    if not args.hostname:
        parser.error("-t/--hostname argument required")

    global csr, prikey, hostname, email, name, phone, pem_filename

                        # , config_items

    if os.path.exists(args.keyfile):
        opt = \
            raw_input('%s already exists. Do you want to overwrite it? Y/N : \n'
                       % args.keyfile)
        if opt == 'y' or opt == 'Y':
            pem_filename = args.keyfile
        elif opt == 'n' or opt == 'N':
            pem_filename = raw_input('Please enter a different file name\n')
        else:
            sys.exit('Invalid option')
    else:
        pem_filename = args.keyfile

    hostname = args.hostname
    email = args.email
    name = args.name
    phone = args.phone
    csr = args.csr
    prikey = args.prikey

    name_no_space = name.replace(' ', '')
    if not name_no_space.isalpha():
        sys.exit('Name should contain only alphabets\n')

    phone_num = phone.replace('-', '')
    if not phone_num.isdigit():
        sys.exit("Phone number should contain only numbers and/or '-'\n")

    if args.prikey == 'genprivate.key':
        pass
    elif not os.path.exists(args.prikey):
        sys.exit('The file %s does not exist' % args.prikey)

    if args.csr == 'gennew.csr':
        pass
    elif not os.path.exists(args.csr):
        sys.exit('The file %s does not exist' % args.csr)
    
    #
    # Read from the ini file
    #
    global host, requrl, content_type, Config
    Config = ConfigParser.ConfigParser()
    if os.path.exists('OSGPKIClients.ini'):
        Config.read('OSGPKIClients.ini')
    elif os.path.exists('etc/OSGPKIClients.ini'):
        Config.read('etc/OSGPKIClients.ini')
    else:
        sys.exit("Missing config file: OSGPKIClients.ini\n")    
    host = Config.get('OIMData', 'host')
    requrl = Config.get('OIMData', 'requrl')
    content_type = Config.get('OIMData', 'content_type')
    return

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
    conn = httplib.HTTPConnection(host)
    try:
        conn.request('POST', requrl, params, headers)
        response = conn.getresponse()
    except httplib.HTTPException, e:
        print 'Connection to %s failed: %s' % (requrl, repr(e))
        raise e
    except Exception, e:
        print 'Error during request to %s' % (requrl, repr(e))
    data = response.read()
    if 'FAILED' in json.dumps(data):
        reason = json.loads(data)['detail']
        reason = reason.split('--')[1]
        print 'The request failed because : %s' % reason
        sys.exit(1)
    conn.close()
    if '"detail": "Nothing to report"' in data and '"status": "OK"' in data:
        ticket = json.loads(data)['host_request_id']
        print "Succesfully submitted"
        print "Request Id#: %s" % ticket
    return

if __name__ == '__main__':
    try:
        parse_args()
        config_items = {'CN': hostname, 'emailAddress': email}

        #
        # Three options for the CSR request
        # 1. User provides neither private key nor CSR
        # 2. User provides private key but need to create the CSR
        # 3. User provides both private key and CSR and we just need to
        #    dump it and strip the text lines for the server
        #

        if prikey == 'genprivate.key' and csr == 'gennew.csr':
            genprivate = createKeyPair(TYPE_RSA, 2048)

      # #### Writing private key####

            privkey = open(pem_filename, 'wb')
            key = \
                OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                    genprivate)
            try:
                privkey.write(key)
                print 'Wrting private key to: %s' % pem_filename
            except OSError, e:
                sys.exit('Cannot write to %s' % pem_filename)
                raise e
            privkey.close()

      # ##############################

            new_csr = createCertRequest(genprivate, digest='sha1',
                    **config_items)

            csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM,
                    new_csr)
            csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n',
                              ''
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
            csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n',
                              ''
                              ).replace('-----END CERTIFICATE REQUEST-----\n'
                    , '')
            connect()
        else:
            new_csr = \
                crypto.load_certificate_request(crypto.FILETYPE_PEM,
                    open(csr, 'r').read())
            csr = crypto.dump_certificate_request(crypto.FILETYPE_PEM,
                    new_csr)
            csr = csr.replace('-----BEGIN CERTIFICATE REQUEST-----\n',
                              ''
                              ).replace('-----END CERTIFICATE REQUEST-----\n'
                    , '')
            connect()
    except Exception, e:
        sys.exit('''Uncaught Exception %s
Please report the bug to goc@opensciencegrid.org. We would address your issue at the earliest.
''' % e)
    except KeyboardInterrupt, k:
        print k
        sys.exit('''Interrupted by user\n''')
    sys.exit(0)
