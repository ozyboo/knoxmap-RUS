# Using your own map data server

KnoxMap downloads map data from public Overpass servers. They are shared, and
ask for roughly under 10,000 requests and 1 GB a day each (see
[LEGAL.md](LEGAL.md#overpass-api-map-data-downloads)). Big or repeated
downloads should come from a server of your own. KnoxMap needs nothing else
changed: it sends the same queries, to your address.

The **Map data server** panel can do all of this for you if Docker Desktop is
installed: paste a Geofabrik `.osm.bz2` address, press Start, and press Use it
when it says ready. The steps below are the same thing by hand.

## 1. Run an Overpass server for your region

The simplest way is the community Docker image
[`wiktorn/overpass-api`](https://github.com/wiktorn/Overpass-API). Pick an
extract that covers your map from [Geofabrik](https://download.geofabrik.de/)
(a state or country, not the whole planet) and start it once to load the data:

```bash
docker run -d --name overpass -p 12345:80 -v overpass_db:/db \
  -e OVERPASS_MODE=init \
  -e OVERPASS_PLANET_URL=https://download.geofabrik.de/north-america/us/tennessee-latest.osm.bz2 \
  -e OVERPASS_RULES_LOAD=10 \
  wiktorn/overpass-api
```

Loading takes from minutes to hours depending on the extract. Check
`docker logs overpass` until it says it is serving. The image's own page lists
the current options (updates, metadata); follow it if they differ from the above.

Test it in a browser or with curl before going on:

```bash
curl "http://localhost:12345/api/interpreter?data=[out:json];node(1);out;"
```

## 2. Tell KnoxMap

Open **Map data server** in the window, enter

```
http://localhost:12345/api/interpreter
```

and press Save. It is used at once, and kept for the next start. One address per
line; several are tried in turn. Empty goes back to the public servers.

The same thing can be set by hand in `knoxmap_config.json` (next to the
program; updates leave it alone):

```json
{ "overpass_endpoints": ["http://localhost:12345/api/interpreter"] }
```

## Notes

* Only the area your extract covers has data: a map outside it will come out
  empty. Pick the extract with room to spare around the places you want.
* Data is as old as the extract unless you set up the image's updates.
* Use `https://` if the server is not on your own PC.
* Reading a `.pbf` file directly is not supported; Overpass does the work of
  assembling multipolygons and filtering tags, and KnoxMap relies on it.
