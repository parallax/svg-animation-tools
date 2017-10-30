# Super simple Illustrator SVG processor for animations. Uses the BeautifulSoup python xml library. 

import os
import errno
from bs4 import BeautifulSoup

def create_file(path, mode):
	directory = os.path.dirname(path)
	if directory != '' and not os.path.exists(directory):
		try:
			os.makedirs(directory)
		except OSError as e:
		    if e.errno != errno.EEXIST:
		        raise
	
	file = open(path, mode)
	return file

def parse_svg(path, namespace, options):
	#print(path)
	file = open(path,'r')
	file_string = file.read().decode('utf8')
	file.close();

	if namespace == None:
		namespace = ''
	else:
		namespace = namespace + '-'

	# BeautifulSoup can't parse attributes with dashes so we replace them with underscores instead		
	file_string = file_string.replace('data-name', 'data_name')

	# Expand origin to data-svg-origin as its a pain in the ass to type
	if 'expand_origin' in options and options['expand_origin'] == True:
		file_string = file_string.replace('origin=', 'data-svg-origin=')
	
	# Add namespaces to ids
	if namespace:
		file_string = file_string.replace('id="', 'id="' + namespace)
		file_string = file_string.replace('url(#', 'url(#' + namespace)

	svg = BeautifulSoup(file_string, 'html.parser')

	# namespace symbols
	symbol_elements = svg.select('symbol')
	for element in symbol_elements:
		del element['data_name']

	use_elements = svg.select('use')
	for element in use_elements:
		if namespace:
			href = element['xlink:href']
			element['xlink:href'] = href.replace('#', '#' + namespace)

		del element['id']


	# remove titles
	if 'title' in options and options['title'] == False:
		titles = svg.select('title')
		for t in titles: t.extract()

	# remove description
	if 'description' in options and options['description'] == False:
		descriptions = svg.select('desc')
		for d in descriptions: d.extract()

	foreign_tags_to_add = []
	if 'convert_svg_text_to_html' in options and options['convert_svg_text_to_html'] == True:
		text_elements = svg.select('[data_name="#TEXT"]')
		for element in text_elements:

			area = element.rect
			if not area: 
				print('WARNING: Text areas require a rectangle to be in the same group as the text element')
				continue

			text_element = element.select('text')[0]
			if not text_element:
				print('WARNING: No text element found in text area')
				continue

			x = area['x']
			y = area['y']
			width = area['width']
			height = area['height']

			text_content = text_element.getText()
			text_tag = BeautifulSoup(text_content, 'html.parser')
			
			data_name = None
			if area.has_attr('data_name'): data_name = area['data_name']
			#print(data_name)
						
			area.extract()
			text_element.extract()
			
			foreign_object_tag = svg.new_tag('foreignObject')
			foreign_object_tag['requiredFeatures'] = "http://www.w3.org/TR/SVG11/feature#Extensibility"
			foreign_object_tag['transform'] = 'translate(' + x + ' ' + y + ')'
			foreign_object_tag['width'] = width + 'px'
			foreign_object_tag['height'] = height + 'px'

			if 'dont_overflow_text_areas' in options and options['dont_overflow_text_areas'] == True:
				foreign_object_tag['style'] = 'overflow:hidden'

			if data_name:
				val = data_name
				if not val.startswith('#'): continue
				val = val.replace('#', '')
				
				attributes = str.split(str(val), ',')
				for a in attributes:
					split = str.split(a.strip(), '=')
					if (len(split) < 2): continue
					key = split[0]
					value = split[1]
					if key == 'id': key = namespace + key
					foreign_object_tag[key] = value
			
			foreign_object_tag.append(text_tag)

			# modyfing the tree affects searches so we need to defer it until the end
			foreign_tags_to_add.append({'element':element, 'tag':foreign_object_tag})
			

	if (not 'process_layer_names' in options or ('process_layer_names' in options and options['process_layer_names'] == True)):
		elements_with_data_names = svg.select('[data_name]')
		for element in elements_with_data_names:

			# remove any existing id tag as we'll be making our own
			if element.has_attr('id'): del element.attrs['id']
			
			val = element['data_name']
			#print(val)
			del element['data_name']

			if not val.startswith('#'): continue
			val = val.replace('#', '')
			
			attributes = str.split(str(val), ',')
			for a in attributes:
				split = str.split(a.strip(), '=')
				if (len(split) < 2): continue
				key = split[0]
				value = split[1]
				if key == 'id' or key == 'class': value = namespace + value
				element[key] = value
	
	
	if 'remove_text_attributes' in options and options['remove_text_attributes'] == True:
		#Remove attributes from text tags
		text_elements = svg.select('text')
		for element in text_elements:
			if element.has_attr('font-size'): del element.attrs['font-size']
			if element.has_attr('font-family'): del element.attrs['font-family']
			if element.has_attr('font-weight'): del element.attrs['font-weight']
			if element.has_attr('fill'): del element.attrs['fill']

	# Do tree modifications here
	if 'convert_svg_text_to_html' in options and options['convert_svg_text_to_html'] == True:
		for t in foreign_tags_to_add:
			t['element'].append(t['tag'])
	

	return svg


def write_svg(svg, dst_path, options):
	
	result = str(svg)
	result = unicode(result, "utf8")	
	#Remove self closing tags
	result = result.replace('></circle>','/>') 
	result = result.replace('></rect>','/>') 
	result = result.replace('></path>','/>') 
	result = result.replace('></polygon>','/>')

	if 'nowhitespace' in options and options['nowhitespace'] == True:
		result = result.replace('\n','')
	#else:
	#	result = svg.prettify()

	# bs4 incorrectly outputs clippath instead of clipPath 
	result = result.replace('clippath', 'clipPath')
	result = result.encode('UTF8')

	result_file = create_file(dst_path, 'wb')
	result_file.write(result)
	result_file.close()



def compile_svg(src_path, dst_path, options):
	namespace = None

	if 'namespace' in options: 
		namespace = options['namespace']
	svg = parse_svg(src_path, namespace, options)

	if 'attributes' in options: 
		attrs = options['attributes']
		for k in attrs:
			svg.svg[k] = attrs[k]

	if 'description' in options:
		current_desc = svg.select('description')
		if current_desc:
			current_desc[0].string = options['description']
		else:
			desc_tag = svg.new_tag('description');
			desc_tag.string = options['description']
			svg.svg.append(desc_tag)
		
	write_svg(svg, dst_path, options)



def compile_master_svg(src_path, dst_path, options):
	print('\n')
	print(src_path)
	file = open(src_path)
	svg = BeautifulSoup(file, 'html.parser')
	file.close()

	master_viewbox = svg.svg.attrs['viewbox']

	import_tags = svg.select('[path]')
	for tag in import_tags:

		component_path = str(tag['path'])
		
		namespace = None
		if tag.has_attr('namespace'): namespace = tag['namespace']

		component = parse_svg(component_path, namespace, options)

		component_viewbox = component.svg.attrs['viewbox']
		if master_viewbox != component_viewbox:
			print('WARNING: Master viewbox: [' + master_viewbox + '] does not match component viewbox [' + component_viewbox + ']')
	
		# Moves the contents of the component svg file into the master svg
		for child in component.svg: tag.contents.append(child)

		# Remove redundant path and namespace attributes from the import element
		del tag.attrs['path']
		if namespace: del tag.attrs['namespace']


	if 'attributes' in options: 
		attrs = options['attributes']
		for k in attrs:
			print(k + ' = ' + attrs[k])
			svg.svg[k] = attrs[k]


	if 'title' in options and options['title'] is not False:
		current_title = svg.select('title')
		if current_title:
			current_title[0].string = options['title']
		else:
			title_tag = svg.new_tag('title');
			title_tag.string = options['title']
			svg.svg.append(title_tag)


	if 'description' in options:
		current_desc = svg.select('description')
		if current_desc:
			current_desc[0].string = options['description']
		else:
			desc_tag = svg.new_tag('description');
			desc_tag.string = options['description']
			svg.svg.append(desc_tag)


	write_svg(svg, dst_path, options)


# Super dumb / simple function that inlines svgs into html source files

def parse_markup(src_path, output):
	print(src_path)
	read_state = 0
	file = open(src_path, 'r')
	for line in file:
		if line.startswith('//import'):
			path = line.split('//import ')[1].rstrip('\n').rstrip('\r')
			parse_markup(path, output)
		else:
			output.append(line)

	file.close()

def inline_svg(src_path, dst_path):
	output = [];

	file = create_file(dst_path, 'w')
	parse_markup(src_path, output)
	for line in output: file.write(line)
	file.close()
	print('')	