#!/usr/bin/env python
# -*- coding: utf-8 -*-
#===============================================================================
# m3u2hts.py - Generate TVHeadend 3.x channel/tag configuration files from
# IPTV M3U playlist
#
# (c) 2012 Gregor Rudolf
# Licensed under the MIT license:
# http://www.opensource.org/licenses/mit-license.php
#===============================================================================
from optparse import OptionParser
import codecs
import re
import os

try:
    import json
except ImportError:
    # old python? easy_install simplejson
    import simplejson as json

PROGNUM = re.compile(r"(\d+) - (.*)")  # #EXTINF:0,1 - SLO 1 -> #1 - num, 2 - ime

CHAN_NUMBERING_GENERATE = 0
CHAN_NUMBERING_DURATION = 1
CHAN_NUMBERING_NAMES = 2

channels = dict()
tags = dict()


def readm3u(infile, removenum, channumbering, inputcodec):
    """
    Read IPTV channels from .M3U file
    @param infile: input file
    @param removenum: try to remove channel numbers from names
    @param channumbering: how to get channel number
    @param inputcodec: encoding of input file
    """

    instream = codecs.open(infile, "Ur", encoding=inputcodec)
    
    urlRegex = re.compile(r"^((?P<schema>.+?)://@?)?(?P<host>.*?)(:(?P<port>\d+?))?$")
    chancnt = 0
    tagcnt = 0
    chname = ''
    chtags = None
    chlanguage = None
    chnumber = None
    chxmltv = None
    chicon = None
    for line in instream.readlines():
        line = line.strip()
        if line.startswith("#EXTINF:"):
            #EXTINF:duration,channel number - channel name
            buff = line[8:].split(',')
            m = PROGNUM.search(buff[1])
            if removenum and m:
                chname = m.group(2)
            else:
                chname = buff[1]
            if m and channumbering == CHAN_NUMBERING_NAMES:
                chnumber = m.group(1)
            elif channumbering == CHAN_NUMBERING_DURATION:
                chnumber = buff[0]
        elif line.startswith('#EXTTV:'):
            #EXTTV:tag[,tag,tag...];language;XMLTV id[;icon URL]
            buff = line[7:].split(';')
            chtags = buff[0].split(',')
            for t in chtags:
                if not t in tags:
                    tagcnt += 1
                    tags[t] = {'num': tagcnt, 'name': t}
            chlanguage = buff[1]
            if chlanguage:
                if not chlanguage in tags:
                    tagcnt += 1
                    tags[chlanguage] = {'num': tagcnt, 'name': chlanguage}
                chtags.append(chlanguage)
            chxmltv = buff[2]
            chicon = buff[3] if len(buff) > 3 else None
        else:
            chgroup = re.search(urlRegex, line).groupdict()
            if not chgroup or not chgroup["schema"]:
                continue
            chancnt += 1
            if channumbering == CHAN_NUMBERING_GENERATE: chnumber = chancnt
            if chname in channels:
                print "%s already exists" % chname
                chname = chname + '.'
            channels[chname] = {'num': chancnt, 'number': chnumber, 'name': chname, 'tags': chtags, 'lang': chlanguage,
                                'ip': chgroup["host"], 'port': chgroup["port"], 'xmltv': chxmltv, 'icon': chicon}
            chname = ''
            chtags = None
            chlanguage = None
            chnumber = None
            chxmltv = None
            chicon = None


def writechannels():
    svcpath = 'iptvservices'
    chnpath = 'channels'
    xmltvpath = "epggrab/xmltv/channels"
    if not os.path.exists(svcpath):
        os.mkdir(svcpath)
    if not os.path.exists(chnpath):
        os.mkdir(chnpath)
    if not os.path.exists(xmltvpath):
        os.makedirs(xmltvpath)
    for channel in channels.values():
        #iptvservices/iptv_?
        jssvc = {'pmt': 0,
                 'channelname': channel['name'],
                 'port': channel['port'],
                 'interface': 'eth1',
                 'group': channel['ip'],
                 'mapped': 1,
                 'pcr': 0,
                 'disabled': 0}
        writejson(os.path.join(svcpath, "iptv_" + str(channel['num'])), jssvc)

        #channels/?
        jschan = {'name': channel['name'],
                  'dvr_extra_time_pre': 0,
                  'dvr_extra_time_post': 0}
        if channel['number'] is not None:
            jschan['channel_number'] = channel['number']
        if channel['xmltv'] is not None:
            jschan['xmltv-channel'] = channel['xmltv']
        if channel['tags'] is not None:
            jschan['tags'] = list(tags[x]['num'] for x in channel['tags'])
        if channel['icon'] is not None:
            jschan['icon'] = channel['icon']
        writejson(os.path.join(chnpath, str(channel['num'])), jschan)

        #epg, if defined
        #epggrab/xmltv/channels/?
        if channel['xmltv']:
            xmlid = channel['xmltv']
            jsepg = {
                'name': xmlid,
                'channels': [channel['number']]
            }
            writejson(os.path.join(xmltvpath, xmlid), jsepg)



def uuid():
    import uuid

    return uuid.uuid4().hex


def writechannels39():
    xmltvpath = "epggrab/xmltv/channels"
    if not os.path.exists(xmltvpath):
        os.makedirs(xmltvpath)

    chnpath = 'channel/config'
    if not os.path.exists(chnpath):
        os.makedirs(chnpath)

    #input/iptv
    path = os.path.join('input', 'iptv')
    if not os.path.exists(path):
        os.makedirs(path)
    #input/iptv/config
    writejson(os.path.join(path, 'config'), {
        'uuid': uuid(),
        'skipinitscan': 1,
        'autodiscovery': 0
    })
    #input/iptv/networks/uuid()
    path = os.path.join(path, 'networks', uuid())
    if not os.path.exists(path):
        os.makedirs(path)
    writejson(os.path.join(path, 'config'), {
        'networkname': 'IPTV network',
        'skipinitscan': 1,
        'autodiscovery': 0
    })
    #input/iptv/networks/uuid()/muxes
    path = os.path.join(path, 'muxes')
    if not os.path.exists(path):
        os.mkdir(path)
    #one mux and service for each channel
    for channel in channels.values():
        muxid = uuid()
        muxpath = os.path.join(path, muxid)
        if not os.path.exists(muxpath):
            os.mkdir(muxpath)
        jsmux = {
            'iptv_url': "udp://@%s:%s" % (channel['ip'], channel['port']),
            'iptv_interface': 'eth1',
            'iptv_atsc': 0,
            'iptv_svcname': channel['name'],
            'enabled': 1,
            'initscan': 1  # mark mux as scanned
        }
        #input/iptv/networks/uuid()/muxes/uuid()/config file
        writejson(os.path.join(muxpath, 'config'), jsmux)
        #input/iptv/networks/uuid()/muxes/uuid()/services/uuid()
        svcpath = os.path.join(muxpath, 'services')
        if not os.path.exists(svcpath):
            os.mkdir(svcpath)
        svcid = uuid()
        jssvc = {
            'sid': 1,   # guess service id
            'svcname': channel['name'],
            'name': channel['name'],
            'dvb_servicetype': 1,
            'enabled': 1
        }
        writejson(os.path.join(svcpath, svcid), jssvc)

        #channel/config
        chanid = uuid()
        jschan = {
            'name': channel['name'],
            'dvr_pre_time': 0,
            'dvr_pst_time': 0,
            'services': [svcid]
        }
        if channel['number'] is not None:
            jschan['number'] = int(channel['number'])
        if channel['tags'] is not None:
            jschan['tags'] = list(tags[x]['num'] for x in channel['tags'])
        if channel['icon'] is not None:
            jschan['icon'] = channel['icon']
        writejson(os.path.join(chnpath, chanid), jschan)

        #epg
        #epggrab/xmltv/channels/#
        if channel['xmltv'] is not None:
            xmlid = channel['xmltv']
        else:
            xmlid = channel['name']
        jsepg = {
            'name': xmlid,
            'channels': [chanid]
        }
        writejson(os.path.join(xmltvpath, chanid), jsepg)


def writetags():
    path = 'channeltags'
    if not os.path.exists(path):
        os.mkdir(path)
    for tag in tags.values():
        #channeltags/?
        jstag = {'enabled': 1,
                 'internal': 0,
                 'titledIcon': 0,
                 'name': tag['name'],
                 'comment': '', 'icon': '',
                 'id': tag['num']}
        writejson(os.path.join(path, str(tag['num'])), jstag)


def writejson(filename, obj):
    """
    Export obj to filename in JSON format
    @param filename: output file
    @param obj: object to export
    """
    outstream = codecs.open(filename, "w", encoding='utf-8')
    json.dump(obj, outstream, indent=4, ensure_ascii=False)
    outstream.close()


def main():
    par = OptionParser(usage="%prog [options] inputfile",
                       description="Generate TVHeadend 3.x channel/tag configuration files from IPTV M3U playlist")
    par.add_option('-r', '--removenum', action='store_true', help=u'remove program numbers from names')
    par.add_option('-n', '--numbering', type='int', default=0,
                   help=u'program numbers are generated(0), determined from duration(1) or extracted from program names(2)')
    par.add_option('-c', '--codec', action='store', dest='codec', default='cp1250',
                   help=u'input file encoding [default: %default]')
    par.add_option('--newformat', action='store_true',
                   help=u'generate TVHeadend 3.9+ compatible configuration files (experimental)')
    opt, args = par.parse_args()
    if len(args) == 1:
        readm3u(args[0], opt.removenum, opt.numbering, opt.codec)
        writechannels39() if opt.newformat else writechannels()
        writetags()
        print("OK")
    else:
        par.print_help()


if __name__ == '__main__':
    main()
