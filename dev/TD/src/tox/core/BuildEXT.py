"""
Extension classes enhance TouchDesigner components with python. An
extension is accessed via ext.ExtensionClassName from any operator
within the extended component. If the extension is promoted via its
Promote Extension parameter, all its attributes with capitalized names
can be accessed externally, e.g. op('yourComp').PromotedFunction().

Help: search "Extensions" in wiki
"""

from TDStoreTools import StorageManager
import TDFunctions as TDF

from datetime import datetime as dt

import re
# uses regex to extract functions and structs
# requires pretty strict formatting to properly handle nested scopes
# more work could probably be done here. 
def extractFunctsAndStructs(inputText):
	function_pattern = r'(\b\w+\s+\w+)\s*\(([^)]*)\)\s*^{\n([\s\S]*?)^}'
	struct_pattern = r'\bstruct\s+(\w+)\s*{([^}]+)}'
	functions = re.findall(function_pattern, inputText, re.MULTILINE | re.DOTALL)
	structs = re.findall(struct_pattern, inputText, re.MULTILINE | re.DOTALL)
	return functions, structs

def replace_strings(text, search_list, replacement_list):
    for search, replacement in zip(search_list, replacement_list):
        text = text.replace(search, replacement)
    return text


class BuildEXT:
	"""
	BuildEXT description
	"""
	def __init__(self, ownerComp):
		# The component to which this extension is attached
		self.ownerComp = ownerComp

		# properties
		# TDF.createProperty(self, 'MyProperty', value=0, dependable=True,
		# 				   readOnly=False)

		# attributes:
		self.Shaders = tdu.Dependency({})
		self.B = 1 # promoted attribute

		# stored items (persistent across saves and re-initialization):
		storedItems = [
			# Only 'name' is required...
			{'name': 'StoredProperty', 'default': None, 'readOnly': False,
			 						'property': True, 'dependable': True},
		]
		# Uncomment the line below to store StoredProperty. To clear stored
		# 	items, use the Storage section of the Component Editor
		
		# self.stored = StorageManager(self, ownerComp, storedItems)

	def BuildShaderCatalog(self):	
		for t in self.ownerComp.op('shaders').findChildren(type=textDAT):
			shader_class = self.Shaders.val[t.name] = {}
			functions, structs = extractFunctsAndStructs(t.text)

			#debug("getting defines from ", t.name)
			shader_class['defines'] = []
			lines = t.text.split("\n")
			for l in lines:
				if l[:7] == "#define":
					shader_class['defines'].append(l)
		
			#debug("getting functions from ", t.name)
			shader_class['functions'] = {}
			for func in functions:
				#debug(func)
				signature, params, body  = func
				f = shader_class['functions'][signature.split()[1]] = {}
				f['body'] = body
				f['sig'] = signature + '(' + params + ')'
				#debug(f['sig'])

			#debug("getting structs from ", t.name)
			shader_class['structs'] = {}
			for stru in structs:
				name, body = stru
				#debug(stru)
				shader_class['structs'][name] = body
				#debug(name)
	
	def WriteShader( self, tocDat: tableDAT, outDat: str = 'build_out', saveFile: bool = False, prependPath: str = './' ):
		#debug("rebuilding shader catalog...\n\n")
		self.BuildShaderCatalog()

		if [c.val for c in tocDat.row(0)][:3] == ['type', 'id', 'class']:
			out = tocDat.parent().op( outDat )
			if not out:
					out = tocDat.parent().create( textDAT, outDat )
					out.color = ( 0.1, 0.1, 1.0 )
			
			out.clear()

			out.write('// Astra ColorTK: ' + tocDat.name + '\n')
			out.write('// AUTOGENERATED by Shader Build System\n')
			out.write('// DATE: ' + dt.now().strftime('%Y%m%d_%H%M%S')+'\n')
			localPath = tocDat.parent().path
			for r in range( 1, tocDat.numRows ):
				ctype,id,sclass,srcTxt,dstTxt = [ c.val for c in tocDat.row( r ) ]
				write_buf = ''
				if ctype == 'text':
					write_buf =  op( localPath + '/' + id ).text 
					
				elif ctype == 'struct':
					write_buf = 'struct ' + id + "\n{\n" + self.Shaders[sclass]['structs'][id] + "\n};"
				
				elif ctype == 'function':
					write_buf =	self.Shaders[sclass]['functions'][id]['sig'] + "\n{\n" + self.Shaders[sclass]['functions'][id]['body'] + "\n}"
				
				elif ctype == 'defines':
					for d in self.Shaders[sclass]['defines']:
						write_buf += d+'\n'

				elif ctype == '':
					write_buf = "\n"
				
				if not srcTxt == '':
					src = srcTxt.split(';')
					dst = dstTxt.split(';')
					write_buf = replace_strings(write_buf, src, dst)

				out.write(write_buf)

				out.write("\n")

			if saveFile:
				out.save( prependPath + tocDat.name + '.glsl' )


			
