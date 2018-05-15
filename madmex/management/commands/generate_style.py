'''
Created on Apr 27, 2018

@author: agutierrez
'''

import logging
import os
import struct
from xml.dom.minidom import parse

from madmex.management.base import AntaresBaseCommand
from madmex.models import Tag
from madmex.settings import BASE_DIR, TEMP_DIR

logger = logging.getLogger(__name__)

class Command(AntaresBaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--scheme', nargs=1, help='The name of the raster to process.')
    def handle(self, *args, **options):
        scheme = options['scheme'][0]
        queryset = Tag.objects.filter(scheme=scheme)
        if queryset.count() > 0:
            template_directory = os.path.join(BASE_DIR, 'madmex/templates')
            template = os.path.join(template_directory,'vector_style_template.qml')
            xml_tree = parse(template)
            categories = xml_tree.getElementsByTagName('categories')[0]
            symbols = xml_tree.getElementsByTagName('symbols')[0]
            for tag in queryset:
                new_category = xml_tree.createElement('category')
                new_category.setAttribute('render', 'true')
                new_category.setAttribute('symbol', str(tag.numeric_code))
                new_category.setAttribute('value', tag.value)
                new_category.setAttribute('label', tag.value)
                categories.appendChild(new_category )
                
                symbol = xml_tree.createElement('symbol')
                symbol.setAttribute('alpha', '1')
                symbol.setAttribute('clip_to_extent', '1')
                symbol.setAttribute('type', 'fill')
                symbol.setAttribute('name', str(tag.numeric_code))
                
                layer = xml_tree.createElement('layer')
                layer.setAttribute('pass', '0')
                layer.setAttribute('class', 'SimpleFill')
                layer.setAttribute('locked', '0')
                
                def create_prop(dom, key, value):
                    prop = dom.createElement('prop')
                    prop.setAttribute('k', key)
                    prop.setAttribute('v', value)
                    return prop
                color = tag.color
                
                if color.startswith('#'):
                    color = color[1:]
                
                rgb = struct.unpack('BBB', bytes.fromhex(color))
                layer.appendChild(create_prop(xml_tree, 'border_width_map_unit_scale', '0,0,0,0,0,0'))
                layer.appendChild(create_prop(xml_tree, 'color', '%s,%s,%s,255' % rgb))
                layer.appendChild(create_prop(xml_tree, 'joinstyle', 'bevel'))
                layer.appendChild(create_prop(xml_tree, 'offset', '0,0'))
                layer.appendChild(create_prop(xml_tree, 'keyoffset_map_unit_scale', '0,0,0,0,0,0'))
                layer.appendChild(create_prop(xml_tree, 'offset_unit', 'MM'))
                layer.appendChild(create_prop(xml_tree, 'outline_color', '0,0,0,0'))
                layer.appendChild(create_prop(xml_tree, 'outline_style', 'solid'))
                layer.appendChild(create_prop(xml_tree, 'outline_width', '0.1'))
                layer.appendChild(create_prop(xml_tree, 'outline_width_unit', 'MM'))
                layer.appendChild(create_prop(xml_tree, 'style', 'solid'))
                symbol.appendChild(layer)
                symbols.appendChild(symbol)
            file_handle = open(os.path.join(TEMP_DIR, '%s.qml' % scheme),'w')
            xml_tree.writexml(file_handle)
            file_handle.close()
        else:
            logger.error('The scheme does not exist.')
