import sys
import dircache
import os
import pprint

from Graphs import *
import FlowGrapher

class ASASM:
	def ParseLine(self,line):
		prefix=''
		keyword=''
		parameter=''
		comment=''
		state='keyword'
		for ch in line:
			if state=='keyword':
				if ch==' ' or ch=='\t':
					if keyword!='':
						state='parameter'
					else:
						prefix+=ch
				elif ch=='\r' or ch=='\n':
					break
				else:
					keyword+=ch

			elif state=='parameter':
				if ch=='\r' or ch=='\n':
					break
				elif ch==';':
					state='comment'
				elif parameter=="" and (ch==' ' or ch=='\t'):
					pass
				else:
					parameter+=ch

			else:
				if ch=='\r' or ch=='\n':
					break

				comment+=ch

		return [prefix,keyword,parameter,comment]

	def ParseNameNotation(self,line):
		main_str=''
		parameters=[]
		parameter=''
		level=0
		for ch in line:
			if level==0 and main_str=='' and ( ch==' ' or ch=='\t'):
				continue

			if ch==')':
				level-=1

			if level>0:
				if level==1 and ch==',':
					parameters.append(self.ParseNameNotation(parameter))
					parameter=''
				else:
					parameter+=ch

			if ch=='(':
				level+=1

			if level==0 and ch!=')':
				main_str+=ch

		if parameter:
			parameters.append(self.ParseNameNotation(parameter))


		if len(parameters)>0:
			return {'type':main_str,'parameters':parameters}
		else:
			return {'constant':main_str}

	def GetName(self,line):
		ret=asasm.ParseNameNotation(line)
		return ret['parameters'][1]['constant'][1:-1]

	BlockKeywords=['body',
					'class',
					'code',
					'instance',
					'iinit',
					'cinit',
					'sinit',
					'method',
					'program',
					'script',
					'trait']

	DebugKeyword=0

	def ReadFile(self,filename):
		if self.DebugKeyword>0:
			print '* ReadFile:', filename
		parsed_lines=[]
		fd=open(filename,'r')
		position=[]
		while True:
			line=fd.readline()
			if not line:
				break
			[prefix,keyword,parameter,comment]=self.ParseLine(line)
			parsed_lines.append([prefix,keyword,parameter,comment])
			if keyword:
				if keyword[0]=='#':
					if self.DebugKeyword>1:
						print 'Meta:', keyword, parameter

				elif keyword[-1]==':':
					if self.DebugKeyword>1:
						print 'Label:', keyword, parameter
				else:
					if self.DebugKeyword>1:
						print keyword, parameter

					if keyword in self.BlockKeywords:
						position.append(keyword)
					elif keyword=='end':
						del position[-1]
		fd.close()
		return parsed_lines

	def WriteFile(self,filename, parsed_lines):
		fd=open(filename,'w')
		for [prefix,keyword,parameter,comment] in parsed_lines:
			line=prefix+keyword
			if parameter:
				line+=" "+parameter

			if comment:
				line+=" ; "+comment
			line+='\n'
			fd.write(line)
		fd.close()

	DebugReplace=0
	def ReplaceSymbol(self,parsed_lines,orig,replace):
		index=0
		for [prefix,keyword,parameter,comment] in parsed_lines:
			if parameter.find(orig)>=0:
				new_parameter=parameter.replace(orig,replace)
				if self.DebugReplace>0:
					print "Replacing:", keyword
					print " ",parameter
					print " ",new_parameter
				parsed_lines[index][2]=new_parameter
			index+=1
		return parsed_lines

	def ConvertMapsToPrintable(self,(blocks,maps,labels)):
		#Convert blocks,maps
		name2id_maps={}
		id2name_maps={}

		blocks_by_id={}
		for (block_name,instructions) in blocks.items():
			id=block_name
			name2id_maps[block_name]=id
			id2name_maps[id]="%d" % id
			diasm_lines=''
			for (keyword,parameter) in instructions:
				if keyword:
					parameter_line=''
					current_line_length=0
					for ch in parameter:
						parameter_line+=ch
						current_line_length+=1
						if current_line_length>10 and ch==',':
							parameter_line+='\n\ \ \ \ \ \ \ \ '
							current_line_length=0

					diasm_lines+='%s %s\n' % (keyword,parameter_line)

			blocks_by_id[id]=[0,diasm_lines]

		maps_by_id={}
		for (src_block_name,target_block_names) in maps.items():
			target_ids=[]
			for target_block_name in target_block_names:
				target_ids.append(name2id_maps[target_block_name])
			maps_by_id[name2id_maps[src_block_name]]=target_ids

		if self.DebugMethods>0:
			pprint.pprint(blocks_by_id)
			pprint.pprint(maps_by_id)
			pprint.pprint(id2name_maps)
			print ''
		return [blocks_by_id,maps_by_id,id2name_maps]

	def ReplaceCode(self,parsed_lines,target_refid,code_parsed_lines):
		start_index=0
		end_index=0
		index=0
		for [prefix,keyword,parameter,comment] in parsed_lines:
			if keyword=='refid':
				refid=parameter[1:-1]

			if keyword=='code':
				if refid==target_refid:
					start_index=index+1

			elif keyword=='end':
				if start_index>0:
					end_index=index-1
					break

			index+=1

		parsed_lines[start_index:end_index]=code_parsed_lines

		return parsed_lines

	DebugMethods=0
	def RetrieveMethod(self,parsed_lines,target_method=''):
		if self.DebugMethods>0:
			print '-' * 80
		parents=[]
		new_parsed_lines=[]
		in_code=False
		methods={}

		for [prefix,keyword,parameter,comment] in parsed_lines:
			if keyword in self.BlockKeywords:
				if parameter[-3:]!='end':
					parents.append([keyword,parameter])
			elif keyword=='end':
				del parents[-1]

			if keyword=='refid':
				refid=parameter[1:-1]

			if keyword=='end' and in_code:
				if self.DebugMethods>0:
					print '* New block %s (end of code)' % block_name

				if len(instructions)>0:
					if last_block_name and not is_last_instruction_jmp:
						if self.DebugMethods>0:
							print '%s -> %s' % (last_block_name,block_name)
						if not maps.has_key(last_block_name):
							maps[last_block_name]=[block_name]
						else:
							if not block_name in maps[last_block_name]:
								maps[last_block_name].append(block_name)

					blocks[block_name]=instructions
					if self.DebugMethods>0:
						pprint.pprint(instructions)
						print ''
					instructions=[]
					is_last_instruction_jmp=False

				in_code=False

				if self.DebugMethods>0:
					print refid
					pprint.pprint(blocks)
					pprint.pprint(maps)
					print ''

				methods[refid]=[blocks,maps,labels]

				if self.DebugMethods>0:
					print '='*80
					pprint.pprint(blocks)
					pprint.pprint(maps)
					print ''

				blocks={}
				maps={}
				labels={}

			if in_code:
				if keyword[-1:]==":":
					if len(instructions)>0:
						if self.DebugMethods>0:
							print '* New block %s (start of block)' % block_name
						if last_block_name and not is_last_instruction_jmp:
							if self.DebugMethods>0:
								print '%s -> %s (Label)' % (last_block_name,block_name)
							if not maps.has_key(last_block_name):
								maps[last_block_name]=[block_name]
							else:
								if not block_name in maps[last_block_name]:
									maps[last_block_name].append(block_name)

						blocks[block_name]=instructions

						if self.DebugMethods>0:
							pprint.pprint(instructions)
							print ''

						last_block_name=block_name

						instructions=[]
						is_last_instruction_jmp=False
					block_name=instruction_count
					labels[block_name]=keyword

				elif keyword:
					if len(instructions)==0 and last_block_name!=None and not is_last_instruction_jmp:
						if self.DebugMethods>0:
							print '%s -> %s (Flow)' % (last_block_name,block_name)

						if not maps.has_key(last_block_name):
							maps[last_block_name]=[block_name]
						else:
							if not block_name in maps[last_block_name]:
								maps[last_block_name].append(block_name)

					instructions.append([keyword,parameter])
					instruction_count+=1
					if keyword[0:2]=='if' or keyword=='jump':
						if self.DebugMethods>0:
							print '* New block %s (end of a block)' % block_name

						if len(instructions)>0:
							blocks[block_name]=instructions
							jump_location=int(parameter[1:])
							if not maps.has_key(block_name):
								maps[block_name]=[jump_location]
							else:
								if not jump_location in maps[block_name]:
									maps[block_name].append(jump_location)						

							if self.DebugMethods>0:
								print '%s -> %s (if/jmp)' % (block_name,jump_location)
								print ''

						last_block_name=block_name
						block_name=instruction_count
						instructions=[]

					if keyword=='jump':
						is_last_instruction_jmp=True
					else:
						is_last_instruction_jmp=False

			if keyword=='code' and (target_method=='' or target_method==refid):
				if self.DebugMethods>0:
					print refid
				in_code=True
				instructions=[]
				instruction_count=0
				blocks={}
				maps={}
				labels={}

				block_name=0
				last_block_name=None
				is_last_instruction_jmp=False

		return methods

	def RetrieveFile(self,file,target_method=''):
		parsed_lines=self.ReadFile(file)
		methods=self.RetrieveMethod(parsed_lines,target_method)
		return [parsed_lines,methods]

	def RetrieveAssembly(self,folder,target_file='',target_method=''):
		files={}
		for relative_file in self.EnumDir(folder):
			if target_file=='' or target_file==relative_file:
				file=os.path.join(folder, relative_file)

				[parsed_lines,methods]=self.RetrieveFile(file,target_method)
				if self.DebugMethods>0:
					pprint.pprint(methods)
				files[relative_file]=[parsed_lines,methods]

		return files

	def ConstructCode(self,blocks,labels):
		ids=blocks.keys()
		ids.sort()

		parsed_lines=[]
		label={}
		for id in ids:
			for (keyword,parameter) in blocks[id]:
				if keyword[0:2]=='if' or keyword=='jump':
					label[int(parameter[1:])]=1

		for id in ids:
			if labels.has_key(id):
				parsed_lines.append(['',labels[id],'',''])
			elif label.has_key(id):
				parsed_lines.append(['','L%d:' % id,'',''])

			for (keyword,parameter) in blocks[id]:
				parsed_lines.append(['      ',keyword,parameter,''])

		return parsed_lines

	def AddMethodTrace(self,parsed_lines):
		parents=[]
		new_parsed_lines=[]
		for [prefix,keyword,parameter,comment] in parsed_lines:
			if keyword in self.BlockKeywords:
				if parameter[-3:]!='end':
					parents.append([keyword,parameter])
			elif keyword=='end':
				del parents[-1]

			if keyword=='refid':
				refid=parameter[1:-1]
			if keyword=='code':
				type=''
				description=''

				if refid:
					description=refid
				else:
					for [keyword,parameter] in parents:
						if keyword=='instance':
							description+='instance: ' + self.GetName(parameter)
						elif keyword=='trait':
							description+=' trait: ' + self.GetName(parameter)

					description+=' type: ' + parents[-3][0]

				new_parsed_lines.append([prefix,keyword,parameter,comment])
				if parents[-3][0]=='method':
					new_parsed_lines.append([prefix + ' ','findpropstrict','QName(PackageNamespace(""), "trace")',''])
					new_parsed_lines.append([prefix + ' ','pushstring','%s' % description,''])
					new_parsed_lines.append([prefix + ' ','callpropvoid','QName(PackageNamespace(""), "trace"), 1',''])
			else:
				new_parsed_lines.append([prefix,keyword,parameter,comment])
		return new_parsed_lines

	def EnumDir(self,root_dir,dir='.'):
		files=dircache.listdir(os.path.join(root_dir,dir))
		asasm_files=[]
		for file in files:
			relative_path=os.path.join(dir,file)
			full_path=os.path.join(root_dir,relative_path)
			if file[-6:]=='.asasm':
				asasm_files.append(relative_path)
			if os.path.isdir(full_path):
				asasm_files+=self.EnumDir(root_dir,relative_path)

		return asasm_files

	def Instrument(self,folder,new_root_folder):
		if not os.path.isdir(new_root_folder):
			try:
				os.makedirs(new_root_folder)
			except:
				pass

		for relative_file in self.EnumDir(folder):
			file=os.path.join(folder, relative_file)

			parsed_lines=self.ReadFile(file)

			new_folder=os.path.join(new_root_folder, os.path.dirname(relative_file))

			if not os.path.isdir(new_folder):
				try:
					os.makedirs(new_folder)
				except:
					pass

			basename=os.path.basename(file)
			new_filename=os.path.join(new_folder,basename)
			filename_replaced=False

			"""
			for [orig,replace] in replace_patterns:
				parsed_lines=self.ReplaceSymbol(parsed_lines,orig,replace)

				if not filename_replaced and basename.find(orig)>=0:
					new_filename=os.path.join(new_folder,basename.replace(orig,replace))
					filename_replaced=True
			"""

			parsed_lines=self.AddMethodTrace(parsed_lines)
			self.WriteFile(new_filename, parsed_lines)

	def WriteFiles(self,files,target_dir):
		for (file,(parsed_lines,methods)) in files.items():
			for (refid,(blocks,maps,labels)) in methods.items():
				code_parsed_lines=asasm.ConstructCode(blocks,labels)
				parsed_lines=asasm.ReplaceCode(parsed_lines,refid,code_parsed_lines)
			new_filename=os.path.join(target_dir,file)

			new_folder=os.path.dirname(new_filename)
			if not os.path.isdir(new_folder):
				try:
					os.makedirs(new_folder)
				except:
					pass
			asasm.WriteFile(new_filename, parsed_lines)

if __name__=='__main__':
	from optparse import OptionParser
	import sys
	class MainWindow(QMainWindow):
		def __init__(self):
			QMainWindow.__init__(self)
			
			self.graph=MyGraphicsView()
			self.graph.setRenderHints(QPainter.Antialiasing)

			layout=QHBoxLayout()
			layout.addWidget(self.graph)

			self.widget=QWidget()
			self.widget.setLayout(layout)

			self.setCentralWidget(self.widget)
			self.setWindowTitle("Graph")
			self.setWindowIcon(QIcon('DarunGrim.png'))

		def Draw(self,dir):
			asasm=ASASM()

			file='.\\_a_-_-_.class.asasm'
			method='_a_-_-_/instance/_a_-_-_/instance/_a_-__-'
			files=asasm.RetrieveAssembly(dir,file,method)

			[disasms,links,address2name]=asasm.ConvertMapsToPrintable(files[file][1][method])
			self.graph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)


	parser=OptionParser()
	parser.add_option("-g","--graph",dest="graph",action="store_true",default=False)
	parser.add_option("-r","--replace",dest="replace",action="store_true",default=False)
	parser.add_option("-c","--reconstruct",dest="reconstruct",action="store_true",default=False)
	parser.add_option("-d","--dump",dest="dump",action="store_true",default=False)
	(options,args)=parser.parse_args()

	dir=''
	if len(sys.argv)>1:
		dir=args[0]

	if options.graph:
		app=QApplication(sys.argv)
		frame=MainWindow()
		frame.Draw(dir)
		frame.setGeometry(100,100,800,500)
		frame.show()
		sys.exit(app.exec_())

	elif options.replace:
		replace_patterns=[]

		replace_patterns.append(["_a_--__-","class02"])
		replace_patterns.append(["_a_-_---","class04"])
		replace_patterns.append(["_a_-_-__","class06"])
		replace_patterns.append(["_a_---","class01"])
		replace_patterns.append(["_a_-_-_","class05"])
		replace_patterns.append(["_a_-_","class03"])

		new_folder=r"..\payload-0.mod"


		asasm=ASASM()
		print asasm.GetName(r'QName(PackageNamespace(""), "class03")')
		asasm.Instrument('payload-0','payload-0.mod')
		asasm.Instrument('payload-1','payload-1.mod')

	elif options.dump:
		asasm=ASASM()
		asasm.DebugMethods=0
		files=asasm.RetrieveAssembly(dir)
		pprint.pprint(files)
		#asasm.RetrieveFile(os.path.join(dir,'.\\_a_-_-_.class.asasm'))

	elif options.reconstruct:
		target_dir=''
		if len(sys.argv)>2:
			target_dir=args[1]
		asasm=ASASM()
		asasm.DebugMethods=0
		
		files=asasm.RetrieveAssembly(dir)
		asasm.WriteFiles(files,target_dir)

