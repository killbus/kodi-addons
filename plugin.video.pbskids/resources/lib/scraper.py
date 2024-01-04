# -*- coding: utf-8 -*-
# KodiAddon PBSKids
#
import datetime
import json
from t1mlib import t1mAddon
import xbmc
import xbmcplugin
import xbmcgui
import sys
import requests
from simplecache import SimpleCache, use_cache


class myAddon(t1mAddon):
    def __init__(self, *args):
        t1mAddon.__init__(self, *args)
        # self.addonVersion = self.addon.getAddonInfo("version")
        self.boot_cache_key = f"{self.addonName}.boot"
        self.cache_key_key = f"{self.addonName}.cache_key"
        self.cache = SimpleCache()

    def notificationDialog(
        self, message, header=None, sound=False, time=1000, icon=None
    ):
        header = header or self.addonName
        icon = icon or self.addonIcon
        try:
            return xbmcgui.Dialog().notification(header, message, icon, time, sound)
        except:
            return xbmc.executebuiltin(
                "Notification(%s, %s, %d, %s)" % (header, message, time, icon)
            )

    def save_cache_key(self, cache_key):
        cache_keys = self.cache.get(self.cache_key_key)
        if cache_keys:
            cache_keys = json.loads(cache_keys)
            if cache_key not in cache_keys:
                cache_keys.append(cache_key)
        else:
            cache_keys = [cache_key]
        self.cache.set(self.cache_key_key, json.dumps(cache_keys), expiration=datetime.timedelta(days=1))

    def clear_cache(self):
        cache_keys = self.cache.get(self.cache_key_key)
        if not cache_keys:
            return
        cache_keys = json.loads(cache_keys)
        cache_keys.append(self.cache_key_key)
        for cache_key in cache_keys:
            self.cache.set(
                cache_key,
                '',
                expiration=datetime.timedelta(seconds=1),
            )
        self.notificationDialog("Cleared cache")

    def retrieve_or_set_cache_client_time(self, cache_key, cache_life):
        cache_value = self.cache.get(cache_key)
        if cache_value:
            client_time = cache_value
        else:
            client_time = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            self.cache.set(
                cache_key,
                client_time,
                expiration=datetime.timedelta(seconds=cache_life),
            )
        return client_time

    def getAddonMenu(self, url, ilist):
        # These cache settings are for creating a param passed to getURL
        # cz when the param changes, the cache is invalidated
        cache_life = 28800 / 2
        cache_key = self.boot_cache_key
        self.save_cache_key(cache_key)
        # Make it expired a little early than the response cache
        client_time = self.retrieve_or_set_cache_client_time(cache_key, cache_life - 3)

        a = self.getURL(
            "https://content.services.pbskids.org/v2/kidspbsorg/home/?imgsizes=showLogo:88x88,showLogoSquare:100x100",
            params={"_t": client_time},  # the _t param is used to invalidate the cache
            headers=self.defaultHeaders,
            life=datetime.timedelta(seconds=cache_life),
        )

        # To delete cache while the response is invalid
        if not a.get("collections"):
            self.cache.set(
                cache_key, client_time, expiration=datetime.timedelta(seconds=1)
            )

        a = a["collections"]
        ilist = self.addMenuItem(
            "Live",
            "GS",
            ilist,
            "".join([a["kids-livestream"]["content"][0]["URI"]]),
            self.addonIcon,
            self.addonFanart,
            {},
            isFolder=True,
        )
        b = a.get("kids-show-spotlight", {}).get("content", [])
        b.extend(a["kids-programs-tier-1"]["content"])
        b.extend(a["kids-programs-tier-2"]["content"])
        b.extend(a["kids-programs-tier-3"]["content"])
        for c in b:
            name = c["title"]
            url = c["slug"]
            thumb = c["images"]["mezzanine_16x9"]
            fanart = c["images"]["background"]
            infoList = {
                "mediatype": "tvshow",
                "Title": name,
                "Plot": name,
                "TVShowtitle": name,
                "Studio": "PBS",
            }
            ilist = self.addMenuItem(
                name, "GE", ilist, url, thumb, fanart, infoList, isFolder=True
            )
        return ilist

    def getAddonEpisodes(self, url, ilist):
        a = self.getURL(
            "".join(
                [
                    "https://content.services.pbskids.org/v2/kidspbsorg/programs/",
                    url,
                    "?imgsizes=showLogo:88x88,showLogoSquare:100x100",
                ]
            ),
            headers=self.defaultHeaders,
            life=datetime.timedelta(hours=1),
        )

        a = a["collections"]["episodes"]["content"]
        for b in a:
            url = b.get("mp4")
            if not url is None:
                name = b.get("title", "no title")
                thumb = b.get("images", {"x": None}).get("mezzanine", self.addonIcon)
                fanart = b.get("images", {"x": None}).get("mezzanine", self.addonFanart)
                c = b.get("closedCaptions", [])
                captions = ""
                for d in c:
                    if d.get("format") == "SRT":
                        captions = d.get("URI", "")
                        break
                infoList = {
                    "mediatype": "episode",
                    "Title": name,
                    "TVShowTitle": xbmc.getInfoLabel("ListItem.TVShowTitle"),
                    "Plot": name,
                    "Studio": "PBS",
                }
                ilist = self.addMenuItem(
                    name,
                    "GV",
                    ilist,
                    "".join([url, "|", captions]),
                    thumb,
                    fanart,
                    infoList,
                    isFolder=False,
                )
        return ilist

    def getAddonShows(self, url, ilist):
        url = "".join([url, "|20534|39303%7C10.4"])
        return self.getAddonListing(url, ilist)

    def getAddonVideo(self, url):
        url, captions = url.split("|", 1)
        if not url.endswith(".m3u8"):
            a = requests.get(
                "".join([url, "?format=json"]), headers=self.defaultHeaders
            ).json()
            url = a.get("url")
        if url is not None:
            liz = xbmcgui.ListItem(path=url, offscreen=True)
            if len(captions) > 0:
                liz.setSubtitles([captions])
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, liz)

    def getURL(
        self,
        url,
        params=None,
        headers=None,
        life=datetime.timedelta(minutes=15),
    ):
        self.log("getURL, url = %s, header = %s" % (url, headers))
        params = params or {}
        headers = headers or {
            "User-agent": "Mozilla/5.0 (Windows NT 6.2; rv:24.0) Gecko/20100101 Firefox/24.0"
        }
        cachekey = "%s.getURL, url = %s.%s.%s" % (self.addonName, url, params, headers)
        cacheresponse = self.cache.get(cachekey)
        if not cacheresponse:
            try:
                req = requests.get(url, params, headers=headers)
                req.raise_for_status()
                cacheresponse = req.json()
                req.close()
                self.cache.set(cachekey, json.dumps(cacheresponse), expiration=life)
                self.save_cache_key(cachekey)
            except Exception as e:
                self.log("getURL, Failed! %s" % (e), xbmc.LOGERROR)
                return {}
            return cacheresponse
        return json.loads(cacheresponse)
