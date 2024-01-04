# -*- coding: utf-8 -*-
# KodiAddon 
#
from resources.lib.scraper import myAddon
import re
import sys

# Start of Module

def get_params():
    param = {}
    paramstring = sys.argv[2]
    if len(paramstring) >= 2:
        params = sys.argv[2]
        cleanedparams = params.replace('?', '')
        if (params[len(params) - 1] == '/'):
            params = params[0:len(params) - 2]
        pairsofparams = cleanedparams.split('&')
        param = {}
        for i in range(len(pairsofparams)):
            splitparams = {}
            splitparams = pairsofparams[i].split('=')
            if (len(splitparams)) == 2:
                param[splitparams[0]] = splitparams[1]
    return param


params = get_params()
clear = None

try:
    clear = int(params["clear"])
except:
    pass

addonName = re.search('plugin\://plugin.video.(.+?)/',str(sys.argv[0])).group(1)
ma = myAddon(addonName)

if clear:
    ma.clear_cache()

ma.processAddonEvent()

