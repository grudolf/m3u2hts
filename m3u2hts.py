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
    #old python? easy_install simplejson
    import simplejson as json

PROGNUM = re.compile(r"(\d+) - (.*)")  # #EXTINF:0,1 - SLO 1 -> #1 - num, 2 - ime

#output directories
IPTVSERVICES = "iptvservices"
CHANNELS = "channels"
CHANNELTAGS = "channeltags"

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
        elif line.startswith('udp://@'):
            chancnt += 1
            if channumbering == CHAN_NUMBERING_GENERATE: chnumber = chancnt
            chip, chport = line[7:].rsplit(':', 1)
            if chname in channels:
                print "%s already exists" % chname
                chname = chname + '.'
            channels[chname] = {'num': chancnt, 'number': chnumber, 'name': chname, 'tags': chtags, 'lang': chlanguage,
                                 'ip': chip, 'port': chport, 'xmltv': chxmltv, 'icon': chicon}
            chname = ''
            chtags = None
            chlanguage = None
            chnumber = None
            chxmltv = None
            chicon = None
        else:
            continue


def writechannels():
    if not os.path.exists(IPTVSERVICES):
        os.mkdir(IPTVSERVICES)
    if not os.path.exists(CHANNELS):
        os.mkdir(CHANNELS)
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
        writejson(os.path.join(IPTVSERVICES, "iptv_" + str(channel['num'])), jssvc)

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
        writejson(os.path.join(CHANNELS, str(channel['num'])), jschan)


def writetags():
    if not os.path.exists(CHANNELTAGS):
        os.mkdir(CHANNELTAGS)
    for tag in tags.values():
        #channetags/?
        jstag = {'enabled': 1,
                 'internal': 0,
                 'titledIcon': 0,
                 'name': tag['name'],
                 'comment': '', 'icon': '',
                 'id': tag['num']}
        writejson(os.path.join(CHANNELTAGS, str(tag['num'])), jstag)


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
    opt, args = par.parse_args()
    if len(args) == 1:
        readm3u(args[0], opt.removenum, opt.numbering, opt.codec)
        writechannels()
        writetags()
        print("OK")
    else:
        par.print_help()

if __name__ == '__main__':
    main()
