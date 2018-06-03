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

    def fetch_geojson_for_zipcode(self, zipcode):
        return self.zipcodes[zipcode]

    def add_dot(self, lat, lng, name='', radius=2, color='red', popup=None):
        circle_marker = leaflet.CircleMarker()

        circle_marker.location = (lat, lng)
        circle_marker.radius = radius
        circle_marker.fill_color = color

        circle_marker.stroke = False
        # circle_marker.color = "red"

        circle_marker.name = ' • ' + name

        if popup is not None:
            circle_marker.popup = popup

        self.map.add_layer(circle_marker)

    def add_point(self, lat, lng, name='', popup=None):
        feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [lng, lat]}}
        self.add_geojson(feature, name, popup)

    def add_zipcode_as_dot(self, zipcode, radius=2, color='red'):
        detail = self.gazetteer[zipcode]

        popup_value = '%s (land %s mile²)' % (detail['GEOID'], detail['ALAND_SQMI'])
        popup = widgets.HTML(value=popup_value, placeholder='', description='')

        self.add_dot(detail['INTPTLAT'], detail['INTPTLONG'],
                     name=detail['GEOID'], radius=radius, color=color, popup=popup)
        return popup_value

    def add_geojson(self, geojson, name='', popup=None):
        g = leaflet.GeoJSON(data=geojson, hover_style={'fillColor': '#00aaff'}, name=name)

        if popup is not None:
            g.popup = popup

        self.map += g

    def merge_geojsons(self, geojsons, lines_only=False):
        for geojson in geojsons:
            geojson['properties']['style'] = self.area_style

            if lines_only and geojson["geometry"]["type"] == 'Polygon':
                geojson["geometry"]["type"] = 'MultiLineString'

        return {"type": "FeatureCollection", "features": list(geojsons), 'properties': {}}

    def add_geojsons(self, geojsons, name='', lines_only=False):
        d = self.merge_geojsons(geojsons, lines_only)

        self.add_geojson(d, name)

    def add_zipcode(self, zipcode):
        d = self.fetch_geojson_for_zipcode(zipcode)
        if d is None:
            print('failed to add ' + zipcode + '.')
            return 'nope'

        d['properties']['style'] = self.area_style

        text_template = Template('''<div>ZIP Code
                                        <ul class='list-group'>
                                            <li class='list-group-item'>$zipcode</li>
                                        </ul>
                                    </div>''')
        popup_text = text_template.substitute(zipcode=zipcode)
        popup = widgets.HTML(value=popup_text, placeholder='', description='')

        self.add_geojson(d, name=zipcode, popup=popup)
        return 'ok'

    def progressive_iter(self, iterable, n=None, label_on_finish=''):
        objs = (self.info_box,)
        display(*objs)

        if n is None:
            n = len(iterable)

        self.progress_bar.value = self.progress_bar.min
        self.progress_bar.max = n

        for v in iterable:
            yield v
            self.progress_label.value = v
            self.progress_bar.value += 1

        self.progress_label.value = label_on_finish

    def iter_zipcodes_no_check(self, zipcodes, per_zipcode=lambda z: '', show_progress=False):
        """example::

            >>> m = USMap()
            >>> def process_zipcode(zipcode):
            ...     if zipcode.startswith('9'):
            ...         return 'OK'

            >>> zipcodes = ['98109', '98121', 'abcde']
            >>> results = m.iter_zipcodes_no_check(zipcodes, process_zipcode)
            >>> results
            {'98109': 'OK', '98121': 'OK', 'abcde': None}

            >>> list(results.values())
            ['OK', 'OK', None]
        """
        zipcode_gen = self.progressive_iter(zipcodes) if show_progress else zipcodes

        return {z: per_zipcode(z) for z in zipcode_gen}

    def iter_zipcodes(self, zipcodes, per_zipcode=lambda z: '', show_progress=False):
        """example::

            >>> m = USMap()
            >>> def process_zipcode(zipcode):
            ...     return zipcode[:2]

            >>> zipcodes = ['98109', '98121', 'abcde']
            >>> results = m.iter_zipcodes(zipcodes, process_zipcode)
            >>> results
            {'98109': '98', '98121': '98'}

            >>> list(results.keys())
            ['98109', '98121']

            >>> list(results.values())
            ['98', '98']
        """
        zipcodes = set(zipcodes)
        available_zipcodes = list(zipcodes & self.zipcode_set)
        available_zipcodes.sort()

        return self.iter_zipcodes_no_check(available_zipcodes, per_zipcode, show_progress)

    def merge_zipcodes(self, zipcodes, show_progress=False):
        """example::

            >>> m = USMap()
            >>> def process_zipcode(zipcode):
            ...     return zipcode[:2]

            >>> zipcodes = ['98109', '98121', 'abcde']
            >>> merged = m.merge_zipcodes(zipcodes)

            >>> list(merged.keys())
            ['type', 'features', 'properties']

            >>> all(f['geometry']['type'] == 'Polygon' for f in merged['features'])
            True

            >>> [f['properties']['GEOID10'] for f in merged['features']]
            ['98109', '98121']
        """
        geojsons = self.iter_zipcodes(zipcodes, self.fetch_geojson_for_zipcode, show_progress).values()
        return self.merge_geojsons(geojsons)

    def add_zipcodes(self, zipcodes, mode='area', batch=False, show_progress=False):
        def raise_on_error():
            raise RuntimeError('the combination of (mode=%s, batch=%s) is not supported' % (mode, batch))

        supported_modes = ('area', 'boundary', 'dot')
        should_do_one_by_one = not batch

        if mode not in supported_modes:
            raise RuntimeError('%s is not supported. choose from (%s)' % (mode, ', '.join(supported_modes)))

        if should_do_one_by_one:
            if mode == 'dot':
                return self.iter_zipcodes(zipcodes, self.add_zipcode_as_dot, show_progress)
            elif mode == 'area':
                return self.iter_zipcodes(zipcodes, self.add_zipcode, show_progress)
            else:
                raise_on_error()
        else:  # batch mode
            if mode in ('area', 'boundary'):
                results = self.iter_zipcodes(zipcodes, lambda z: self.zipcodes[z], show_progress)

                geojsons = list(results.values())
                self.add_geojsons(geojsons, name='%d geojsons' % len(geojsons), lines_only=(mode == 'boundary'))

                return results
            else:
                raise_on_error()

    def display(self):
        if self.map is None:
            self.map = leaflet.Map(center=self.center, zoom=self.zoom, basemap=self.basemap, layout=self.map_layout)
            self.map.on_interaction(self.handle_interaction)
            # self.map.add_control(self.layers_control)

        objs = (self.map, self.label)
        display(*objs)


if __name__ == '__main__':
    import doctest
    doctest.testmod()
