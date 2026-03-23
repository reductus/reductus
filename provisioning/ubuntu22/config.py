#############################################################
# rename or copy this file to config.py if you make changes #
#############################################################

# change this to your fully-qualified domain name to run a 
# remote server.  The default value of localhost will
# only allow connections from the same computer.
#jsonrpc_servername = "h3.umd.edu"

message = """\
You are accessing a U.S. Government information system, \
which includes: 1) this computer, 2) this computer network, \
3) all Government-furnished computers connected to this network, \
and 4) all Government-furnished devices and storage media \
attached to this network or to a computer on this network. \
You understand and consent to the following: you may access \
this information system for authorized use only; \
unauthorized use of the system is prohibited and subject to \
criminal and civil penalties; you have no reasonable \
expectation of privacy regarding any communication or data \
transiting or stored on this information system at any time \
and for any lawful Government purpose, the Government may monitor, \
intercept, audit, and search and seize any communication or data \
transiting or stored on this information system; and any \
communications or data transiting or stored on this information \
system may be disclosed or used for any lawful Government purpose. \
This information system may contain Controlled Unclassified \
Information (CUI) that is subject to safeguarding or \
dissemination controls in accordance with law, regulation, or \
Government-wide policy. Accessing and using this system indicates \
your understanding of this warning.
"""

config = {

    "cache": {
        "engine": "diskcache",
        "params": {"size_limit": int(4*2**30), "shards": 5},
        "compression": True
    },
    "data_sources": [
        {
            "name": "ncnr",
            "url": "https://www.ncnr.nist.gov/pub/",
            "start_path": "ncnrdata",
            "file_helper_url": "http://10.201.1.148/ncnrdata/listftpfiles_pg.php"
        },
    ],
    "startup_banner": {
        "title": "Disclaimer",
        "message": message,
    },
    "instruments": ["refl", "ospec", "sans", "dcs", "usans"],
}
