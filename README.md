m3u2hts
=======

Generate TVHeadend 3.x channel/tag configuration files from VLC compatible IPTV M3U playlist.


About
-----

Channel and optional tag definitions are read from a M3U playlist file::

    #EXTINF:duration,[channel number - ]channel name
    #EXTTV:tag[,tag,tag...];language;XMLTV id[;icon URL]
    udp://@ip:port

The #EXTTV line and its contents are optional.

sample.m3u::

    #EXTINF:0,1 - SLO 1
    #EXTTV:nacionalni;slovenski;SLO1
    udp://@239.1.1.115:5000

    #EXTINF:0,SLO 1 HD
    #EXTTV:nacionalni,hd;slovenski;SLO1;http://cdn1.siol.tv/logo/93x78/slo2.png
    udp://@239.10.2.56:5000

The script creates iptvservices, channels, channeltags and epggrab/xmltv/channels directories into which the
following files are written::

    #one file per channel:
    iptvservices/iptv_X
    {
        "pmt": 0,
        "channelname": "SLO 1",
        "port": "5000",
        "interface": "eth1",
        "group": "239.1.1.115",
        "mapped": 1,
        "pcr": 0,
        "disabled": 0
    }

    #one file per channel:
    channels/X
    {
        "name": "SLO 1",
        "xmltv-channel": "SLO1",
        "tags": [
                 1,2
        ],
        "dvr_extra_time_pre": 0,
        "dvr_extra_time_post": 0,
        "channel_number": 1,
        "icon": ""
    }

    #one file per tag:
    channeltags/X
    {
        "enabled": 1,
        "internal": 0,
        "titledIcon": 0,
        "name": "nacionalni",
        "comment": "",
        "icon": "",
        "id": 1
    }
    
    #one file per channel with XMLTV id
    epggrab/xmltv/channels/X
    {
        "channels": [
            1
        ], 
        "name": "SLO1"
    }

Usage
-----

Use ``m3u2hts.py [options] inputfile`` or ``m3u2hts.py -h`` for help.
If you want to import the configuration directly, you should stop the TVHeadend service and delete current config first::

    sudo service tvheadend stop
    sudo su hts
    cd ~/.hts/tvheadend/
    rm iptvservices/* channels/* channeltags/* epggrab/xmltv/channels/*
    m3u2hts.py inputfile.m3u
    exit
    sudo service tvheadend start

Alternatively, run the script somewhere else and transfer the files to TVHeadend config dir when service isn't running.

New file format
---------------

Experimental, use ``--newformat`` switch to create TVHeadend 3.9 compatible configuration.
The file structure is:

    input/iptv/config
    input/iptv/networks/UUID/config                      - one network
    input/iptv/networks/UUID/muxes/UUID/config           - one mux per channel
    input/iptv/networks/UUID/muxes/UUID/services/UUID    - one service per channel
    channel/config/UUID                                  - channel (linked to service)
    channel/tag/UUID                                     - channel tags
    epggrab/xmltv/channels/UUID                          - EPG info (linked to channel)

Licence
-------
Licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
