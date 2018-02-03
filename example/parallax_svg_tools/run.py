from svg import * 

compile_svg('animation.svg', 'processed_animation.svg', 
{
	'process_layer_names': True,
	'namespace': 'example'
})

inline_svg('animation.html', 'output/animation.html')