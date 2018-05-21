from string import Template

import urllib.request
import json
import csv

import ipyleaflet as leaflet
import ipywidgets as widgets


class USZIPCodeRepository:
    CACHE = {}

    def __init__(self, data_url_prefix = 'https://raw.githubusercontent.com/yyu/GeoJSON-US/master'):
        self.data_url_prefix = data_url_prefix
        self.geojson_url_prefix = f'{data_url_prefix}/perZIPgeojson'

        self.refresh_zipcode_latlons(f'{data_url_prefix}/ZIPCodesGazetteer.tsv')
        self.refresh_available_zipcodes(f'{data_url_prefix}/perZIPgeojson/all_zipcodes.txt')


    def refresh_zipcode_latlons(self, url):
        lines = [ line.decode('UTF8').strip() for line in urllib.request.urlopen(url).readlines() ]
        tsv = csv.DictReader(lines, delimiter='\t')
        self.gazetteer = dict((d['GEOID'], {'lat': float(d['INTPTLAT']), 'lon': float(d['INTPTLONG'])}) for d in tsv)


    def refresh_available_zipcodes(self, url):
        lines = [ zipcode.decode('UTF8').strip() for zipcode in urllib.request.urlopen(url).readlines() ]
        self.zipcode_list = lines[1:] # ignore the first line
        self.zipcode_set = set(self.zipcode_list)


    def make_url(self, zipcode):
        return f'{self.data_url_prefix}/perZIPgeojson/{zipcode[0]}/{zipcode[1]}/{zipcode[2]}/{zipcode}.json'


    def fetch_zipcode(self, zipcode):
        '''returns a (dict, err) tuple where err could be a string for error message or None'''

        url = self.make_url(zipcode)

        if url in USZIPCodeRepository.CACHE:
            return (USZIPCodeRepository.CACHE[url], None)

        try:
            s = urllib.request.urlopen(url).read()
        except urllib.error.URLError as e:
            return (None, 'failed to get ' + url, ':', e.reason)

        j = json.loads(s)

        USZIPCodeRepository.CACHE[url] = j

        return (j, None)


    def fetch_zipcodes(self, *zipcodes):
        d = {"type": "FeatureCollection", "features": []}

        available_zipcodes = set(zipcodes) & self.zipcode_set

        for z in available_zipcodes:
            j, err = self.fetch_zipcode(z)

            if j is not None:
                d['features'].append(j)

        return d


class USMap:
    def __init__(self):
        self.us = USZIPCodeRepository()

        self.center = [47.621795, -122.334958]
        self.zoom = 8
        self.height = '500px'
        self.progress_bar_width = '500px'
        self.area_style = {'color':'#0000ff', 'weight': .5, 'fillColor':'#000077', 'fillOpacity':0.2}

        self.progress_bar = widgets.IntProgress(bar_style='info', layout=widgets.Layout(width=self.progress_bar_width))
        self.label = widgets.Label()
        self.progress_label = widgets.Label()
        self.info_box = widgets.HBox([self.progress_label, self.progress_bar])

        self.basemap = leaflet.basemaps.OpenMapSurfer.Roads
        self.basemap['name'] = 'basemap'
        self.heatmap_data = leaflet.basemaps.Strava.All
        self.heatmap_data['name'] = 'heatmap'
        self.heatmap = leaflet.basemap_to_tiles(self.heatmap_data)
        self.layers_control = leaflet.LayersControl()
        self.map_layout = widgets.Layout(height=self.height)

        self.map = None


    def enable_heatmap(self):
        self.map.add_layer(self.heatmap)


    def disable_heatmap(self):
        self.map.remove_layer(self.heatmap)


    def handle_interaction(self, **kwargs):
        '''mouse interaction handling'''
        if kwargs.get('type') == 'mousemove':
            self.label.value = str(kwargs.get('coordinates'))

    def fetch_zipcode(self, zipcode):
        d, err = self.us.fetch_zipcode(zipcode)
        if err is not None:
            print(err)
        return d


    def add_point(self, lat, lng, name='', popup=None):
        feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [lng, lat]}}
        self.add_geojson(feature, name, popup)


    def add_geojson(self, geojson, name='', popup=None):
        g = leaflet.GeoJSON(data=geojson, hover_style={'fillColor': '#00aaff'}, name=name)

        if popup is not None:
            g.popup = popup

        self.map += g


    def add_geojsons(self, geojsons, name=''):
        d = {"type": "FeatureCollection", "features": list(geojsons)}

        self.add_geojson(d, name)


    def add_zipcode(self, zipcode):
        d = self.fetch_zipcode(zipcode)
        if d is None:
            print('failed to add ' + zipcode + '.')
            return

        d['properties']['style'] = self.area_style

        text_template = Template('''<div>ZIP Code
                                        <ul class='list-group'>
                                            <li class='list-group-item'>$zipcode</li>
                                        </ul>
                                    </div>''')
        popup_text = text_template.substitute(zipcode=zipcode)
        popup = widgets.HTML(value=popup_text, placeholder='', description='')

        self.add_geojson(d, name=zipcode, popup=popup)


    def add_zipcodes(self, zipcodes):
        display(self.info_box)

        zipcodes = set(zipcodes)
        available_zipcodes = list(zipcodes & self.us.zipcode_set)
        available_zipcodes.sort()

        self.progress_bar.value = self.progress_bar.min
        self.progress_bar.max = len(available_zipcodes)

        for z in available_zipcodes:
            self.progress_label.value = z
            self.add_zipcode(z)
            self.progress_bar.value += 1
        self.progress_label.value = '%d/%d loaded' % (len(available_zipcodes), len(zipcodes))

        return available_zipcodes


    def display(self):
        if self.map is None:
            self.map = leaflet.Map(center=self.center, zoom=self.zoom, basemap=self.basemap, layout=self.map_layout)
            self.map.on_interaction(self.handle_interaction)
            self.map.add_control(self.layers_control)

        display(self.map)
        display(self.label)
