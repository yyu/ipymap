import json
from string import Template

import ipyleaflet as leaflet
import ipywidgets as widgets
from IPython.display import display
from cloudict import WebDict, WebTSV


class USMap:
    def __init__(self, data_url_prefix='https://raw.githubusercontent.com/yyu/GeoJSON-US/master'):
        self.zipcodes = WebDict(
            url_maker=lambda z: f'{data_url_prefix}/perZIPgeojson/{z[0]}/{z[1]}/{z[2]}/{z}.json',
            response_processor=json.loads
        )
        self.gazetteer = WebTSV(f'{data_url_prefix}/ZIPCodesGazetteer.tsv')
        self.zipcode_set = set(self.gazetteer.keys())

        self.center = [47.621795, -122.334958]
        self.zoom = 8
        self.height = '500px'
        self.progress_bar_width = '500px'
        self.area_style = {'color': '#0000ff', 'weight': .5, 'fillColor': '#000077', 'fillOpacity': 0.2}

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
        """mouse interaction handling"""
        if kwargs.get('type') == 'mousemove':
            self.label.value = str(kwargs.get('coordinates'))

    def fetch_zipcode(self, zipcode):
        return self.zipcodes[zipcode]

    def add_point(self, lat, lng, name='', popup=None):
        feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [lng, lat]}}
        self.add_geojson(feature, name, popup)

    def add_geojson(self, geojson, name='', popup=None):
        g = leaflet.GeoJSON(data=geojson, hover_style={'fillColor': '#00aaff'}, name=name)

        if popup is not None:
            g.popup = popup

        self.map += g

    def add_geojsons(self, geojsons, name=''):
        for geojson in geojsons:
            geojson['properties']['style'] = self.area_style

        d = {"type": "FeatureCollection", "features": list(geojsons), 'properties': {}}

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

    def progressive_iter(self, iterable, n=None, label_on_finish=''):
        display(self.info_box)

        if n is None:
            n = len(iterable)

        self.progress_bar.value = self.progress_bar.min
        self.progress_bar.max = n

        for v in iterable:
            yield v
            self.progress_label.value = v
            self.progress_bar.value += 1

        self.progress_label.value = label_on_finish

    def add_zipcodes_no_check(self, zipcodes, show_progress=False):
        zipcode_gen = self.progressive_iter(zipcodes) if show_progress else zipcodes

        for z in zipcode_gen:
            self.add_zipcode(z)

        return zipcodes

    def add_zipcode_batch_no_check(self, zipcodes, show_progress=False):
        zipcode_gen = self.progressive_iter(zipcodes) if show_progress else zipcodes

        geojsons = [self.zipcodes[z] for z in zipcode_gen]
        name = '%d geojsons' % len(geojsons)

        self.add_geojsons(geojsons, name)

        return zipcodes

    def add_zipcodes(self, zipcodes, show_progress=False):
        zipcodes = set(zipcodes)
        available_zipcodes = list(zipcodes & self.zipcode_set)
        available_zipcodes.sort()

        return self.add_zipcodes_no_check(available_zipcodes, show_progress)

    def add_zipcode_batch(self, zipcodes, show_progress=False):
        zipcodes = set(zipcodes)
        available_zipcodes = list(zipcodes & self.zipcode_set)
        available_zipcodes.sort()

        return self.add_zipcode_batch_no_check(available_zipcodes, show_progress)

    def display(self):
        if self.map is None:
            self.map = leaflet.Map(center=self.center, zoom=self.zoom, basemap=self.basemap, layout=self.map_layout)
            self.map.on_interaction(self.handle_interaction)
            self.map.add_control(self.layers_control)

        display(self.map)
        display(self.label)
