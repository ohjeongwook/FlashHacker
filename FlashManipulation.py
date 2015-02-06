import sys
import dircache
import os
import pprint
from copy import *

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

	DebugParseNameNotation=0
	def ParseNameNotation(self,line,depth=0):
		main_str=''
		parameters=[]
		parameter=''
		level=0
		index=0
		end_of_data=False
		for ch in line:
			if level==0 and main_str=='' and ( ch==' ' or ch=='\t'):
				continue

			if ch==')':
				level-=1

				if depth==0 and level==0:
					index+=1
					break

			if level>0:
				if level==1 and ch==',':
					parameters.append(self.ParseNameNotation(parameter,depth+1))
					parameter=''
				else:
					parameter+=ch

			if ch=='(':
				level+=1

			if level==0 and ch!=')':
				main_str+=ch

			index+=1

		if parameter:
			parameters.append(self.ParseNameNotation(parameter,depth+1))


		if len(parameters)>0:
			ret={'type':main_str,'parameters':parameters}
		else:
			ret={'constant':main_str}


		if depth==0:
			leftover=line[index:]
			if leftover:
				if self.DebugParseNameNotation>0:
					print 'leftover', line[index:]

				arg_count_str=''
				found_separator=False
				for ch in line[index:]:
					if ch==',':
						found_separator=True
					elif found_separator and ch!=' ' and ch!='\t' and ch!='\n' and ch!='\r':
						arg_count_str+=ch

				ret['arg_count']=int(arg_count_str)

		return ret

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

	def WriteToFile(self,filename, parsed_lines):
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

	def WriteToFiles(self,assemblies,target_dir):
		for (file,(parsed_lines,methods)) in assemblies.items():
			new_filename=os.path.join(target_dir,file)

			new_folder=os.path.dirname(new_filename)
			if not os.path.isdir(new_folder):
				try:
					os.makedirs(new_folder)
				except:
					pass
			asasm.WriteToFile(new_filename, parsed_lines)

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

	def ConvertMapsToPrintable(self,(blocks,maps,labels,parents,body_parameters)):
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

	DebugReplaceParsedLines=0
	def ReplaceParsedLines(self,parsed_lines,target_refid,code_parsed_lines,type):
		start_index=0
		start_level=0
		end_index=0
		index=0
		level=0
		for [prefix,keyword,parameter,comment] in parsed_lines:
			if keyword=='refid':
				refid=parameter[1:-1]
			elif keyword in self.BlockKeywords:
				if keyword==type:
					if refid==target_refid:
						start_index=index+1
						start_level=level

				level+=1
			elif keyword=='end':
				if start_index>0 and start_level==level:
					end_index=index-1
					break

				level-=1

			index+=1

		if self.DebugReplaceParsedLines>0:
			print 'Replacing %d - %d ' % (start_index,end_index)
			pprint.pprint(parsed_lines[start_index:end_index])
			pprint.pprint(code_parsed_lines)
			print ''
		parsed_lines[start_index:end_index]=code_parsed_lines

		return parsed_lines

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

	def UpdateParsedLines(self,assemblies):
		for file in assemblies.keys():
			(parsed_lines,methods)=assemblies[file]
			for (refid,(blocks,maps,labels,parents,body_parameters)) in methods.items():
				code_parsed_lines=asasm.ConstructCode(blocks,labels)
				body_parameter_lines=[]
				for (key,value) in body_parameters.items():
					if key!='try':
						body_parameter_lines.append(['',key,value,''])

				body_parameter_lines.append(['','code','',''])
				body_parameter_lines+=code_parsed_lines
				body_parameter_lines.append(['','end','','code'])

				if body_parameters.has_key('try'):
					body_parameter_lines.append(['','try',body_parameters['try'],''])

				parsed_lines=asasm.ReplaceParsedLines(parsed_lines,refid,body_parameter_lines,'body')

			assemblies[file][0]=parsed_lines
		return assemblies

	DebugMethods=0
	def ParseMethod(self,parsed_lines,target_method=''):
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

					if target_method=='' or target_method==refid:
						if keyword=='body':
							body_parameters={}

						if keyword=='code':
							if self.DebugMethods>0:
								print refid
							instructions=[]
							instruction_count=0
							blocks={}
							maps={}
							labels={}

							block_name=0
							last_block_name=None
							is_last_instruction_jmp=False
				continue

			elif keyword=='end':
				parent_name=parents[-1][0]
				if parent_name=='code' and (target_method=='' or target_method==refid):
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

					if self.DebugMethods>0:
						print refid
						pprint.pprint(blocks)
						pprint.pprint(maps)
						print ''

					methods[refid]=[blocks,maps,labels,deepcopy(parents),body_parameters]

					if self.DebugMethods>0:
						print '='*80
						pprint.pprint(blocks)
						pprint.pprint(maps)
						print ''

					blocks={}
					maps={}
					labels={}
					code_parsed_line=[]

				del parents[-1]
				continue

			if len(parents)==0:
				continue

			parent_name=parents[-1][0]
			if keyword=='refid':
				refid=parameter[1:-1]
				continue
				
			if parent_name=='body':
				body_parameters[keyword]=parameter

			elif parent_name=='code':
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

		return methods

	def RetrieveFile(self,file,target_method=''):
		parsed_lines=self.ReadFile(file)
		methods=self.ParseMethod(parsed_lines,target_method)
		return [parsed_lines,methods]

	def RetrieveAssembly(self,folder,target_file='',target_method=''):
		assemblies={}
		for relative_file in self.EnumDir(folder):
			if target_file=='' or target_file==relative_file:
				file=os.path.join(folder, relative_file)

				[parsed_lines,methods]=self.RetrieveFile(file,target_method)
				if self.DebugMethods>0:
					pprint.pprint(methods)
				assemblies[relative_file]=[parsed_lines,methods]

		return assemblies

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

	DebugMethodTrace=1
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
					if self.DebugMethodTrace>0:
						print 'Adding trace', description
					new_parsed_lines.append([prefix + ' ','findpropstrict','QName(PackageNamespace(""), "trace")',''])
					new_parsed_lines.append([prefix + ' ','pushstring','"%s"' % description,''])
					new_parsed_lines.append([prefix + ' ','callpropvoid','QName(PackageNamespace(""), "trace"), 1',''])
			else:
				new_parsed_lines.append([prefix,keyword,parameter,comment])
		return new_parsed_lines

	DebugBasicBlockTrace=0
	def AddBasicBlockTrace(self,methods,filename=''):
		for refid in methods.keys():
			(blocks,maps,labels,parents,body_parameters)=methods[refid]
			for block_id in blocks.keys():
				if self.DebugBasicBlockTrace >0:
					print "="*80
					print ' %d' % block_id
					for line in blocks[block_id]:
						print line
					print ''

				if self.DebugBasicBlockTrace >-1:
					print 'Instrumenting',refid,parents

				if parents[-3][0]=='method' and labels.has_key(block_id) and blocks[block_id][0][0]!='label':
					trace_code=[]
					trace_code.append(['findpropstrict','QName(PackageNamespace(""), "trace")'])
					trace_code.append(['pushstring','"%s\t%s\t%s"' % (filename,refid,labels[block_id])])
					trace_code.append(['callpropvoid','QName(PackageNamespace(""), "trace"), 1'])
					blocks[block_id][0:0]=trace_code

			methods[refid]=(blocks,maps,labels,parents,body_parameters)
		return methods

	DebugAddAPITrace=1
	def GetCallStackCount(self,keyword,parameter):
		stack_count=0
		if keyword in ['call']:
			pass
		elif keyword in ['callmethod', 'callproperty', 'callproplex', 'callpropvoid', 'callstatic', 'callsuper', 'callsupervoid']:
			stack_count+=1

		parsed_notation=self.ParseNameNotation(parameter)
		if parsed_notation.has_key('arg_count'):
			stack_count+=parsed_notation['arg_count']
		return stack_count

	def AddAPITrace(self,methods,filename=''):
		for refid in methods.keys():
			(blocks,maps,labels,parents,body_parameters)=methods[refid]
			for block_id in blocks.keys():
				if self.DebugAddAPITrace>1:
					print "="*80
					print ' %d' % block_id
					for line in blocks[block_id]:
						print line
					print ''

				if self.DebugAddAPITrace >-1:
					print '* Instrumenting',refid,parents

				if parents[-3][0]=='method':
					max_stack_count=0

					for (keyword,parameter) in blocks[block_id]:
						if keyword[0:4]=='call':
							stack_count=self.GetCallStackCount(keyword,parameter)
							if self.DebugAddAPITrace >0:
								print '* ',type,refid
								print keyword, parameter,stack_count
							if stack_count>max_stack_count:
								max_stack_count=stack_count

					orig_localcount=0
					if max_stack_count>0:
						orig_localcount=int(body_parameters['localcount'])
						new_localcount=str(orig_localcount+max_stack_count+1)
						print 'Increasing localcount %s -> %s' % (body_parameters['localcount'], new_localcount)
						body_parameters['localcount']=new_localcount
						if self.DebugAddAPITrace >0:
							print "Max stack count:", type, refid, max_stack_count

						body_parameters['maxstack']=str(int(body_parameters['maxstack'])+5)

					new_blocks=[]
					for (keyword,parameter) in blocks[block_id]:
						if keyword[0:4]=='call':
							escaped_parameter=parameter.replace('"','\\"')

							stack_count=self.GetCallStackCount(keyword,parameter)
							
							if stack_count>0:
								current_local_count=orig_localcount

								array_ns='QName(PackageNamespace(""), "Array")'
								new_blocks.append(['findpropstrict',array_ns])
								new_blocks.append(['constructprop',array_ns +', 0'])
								new_blocks.append(['coerce',array_ns])
								array_reg=current_local_count
								new_blocks.append(['setlocal','%d' % array_reg])
								current_local_count+=1

								for i in range(0,stack_count,1):
									new_blocks.append(['setlocal','%d' % current_local_count])
									current_local_count+=1

								for i in range(0,stack_count,1):
									new_blocks.append(['getlocal','%d' % array_reg])
									new_blocks.append(['getlocal','%d' % (current_local_count-1-i)])
									new_blocks.append(['callpropvoid','QName(Namespace("http://adobe.com/AS3/2006/builtin"), "push"), 1'])
								         
								new_blocks.append(['getlex','QName(PackageNamespace(""), "Util")'])
								new_blocks.append(['pushstring','"%s"' % filename])
								new_blocks.append(['pushstring','"%s"' % refid])
								new_blocks.append(['pushstring','"%s %s"' % (keyword,escaped_parameter)])
								new_blocks.append(['getlocal','%d' % array_reg])
								new_blocks.append(['callpropvoid','QName(PackageNamespace(""), "DumpArray"), 4'])

								for i in range(0,stack_count,1):
									new_blocks.append(['getlocal','%d' % (current_local_count-1-i) ])

							"""
							new_blocks.append(['findpropstrict','QName(PackageNamespace(""), "trace")'])
							new_blocks.append(['pushstring','"%s\t%s -> %s %s"' % (filename,refid,keyword,escaped_parameter)])
							new_blocks.append(['callpropvoid','QName(PackageNamespace(""), "trace"), 1'])	
							"""
									
						new_blocks.append([keyword,parameter])	

					blocks[block_id]=new_blocks

			methods[refid]=(blocks,maps,labels,parents,body_parameters)
		return methods

	def Instrument(self,dir,target_dir,operations=[]):
		assemblies=asasm.RetrieveAssembly(dir)
		for file in assemblies.keys():
			for (operation,options) in operations:
				if operation=="AddBasicBlockTraces":
					assemblies[file][1]=self.AddBasicBlockTrace(assemblies[file][1],filename=file)
					assemblies=self.UpdateParsedLines(assemblies)

				if operation=="AddAPITraces":
					assemblies[file][1]=self.AddAPITrace(assemblies[file][1],filename=file)
					assemblies=self.UpdateParsedLines(assemblies)

				if operation=="Replace":
					for [orig,replace] in options:
						parsed_lines=self.ReplaceSymbol(parsed_lines,orig,replace)
						"""
						if not filename_replaced and basename.find(orig)>=0:
							new_filename=os.path.join(new_folder,basename.replace(orig,replace))
							filename_replaced=True
						"""

				if operation=="AddMethodTraces":
					assemblies[file][0]=self.AddMethodTrace(assemblies[file][0])

					if self.DebugMethodTrace>0:
						print '='*80
						pprint.pprint(assemblies[file][0])
						print ''

				if operation=="Include":
					if file[-1*len('.main.asasm'):]=='.main.asasm':
						print file
						[process_lines,methods]=assemblies[file]
						for index in range(0,len(process_lines),1):
							(prefix,keyword,parameter,comment)=process_lines[index]
							if keyword=='end':
								print 'Inserting', options
								include_lines=[]
								for include_file in options:
									include_lines.append([' ',"#include",'"%s"' % include_file,''])
								process_lines[index:index]=include_lines
								break
						pprint.pprint(process_lines)
						assemblies[file][0]=process_lines

		asasm.WriteToFiles(assemblies,target_dir)

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
			assemblies=asasm.RetrieveAssembly(dir,file,method)

			[disasms,links,address2name]=asasm.ConvertMapsToPrintable(assemblies[file][1][method])
			self.graph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)


	parser=OptionParser()
	parser.add_option("-g","--graph",dest="graph",action="store_true",default=False)
	parser.add_option("-r","--replace",dest="replace",action="store_true",default=False)
	parser.add_option("-c","--reconstruct",dest="reconstruct",action="store_true",default=False)
	parser.add_option("-d","--dump",dest="dump",action="store_true",default=False)
	parser.add_option("-m","--method",dest="method",action="store_true",default=False)
	parser.add_option("-b","--basic_blocks",dest="basic_blocks",action="store_true",default=False)
	parser.add_option("-a","--api",dest="api",action="store_true",default=False)
	parser.add_option("-i","--include",dest="include",action="store_true",default=False)
	(options,args)=parser.parse_args()

	dir=''
	target_dir=''
	if len(args)>0:
		dir=args[0]
		if len(args)>1:
			target_dir=args[1]

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
		assemblies=asasm.RetrieveAssembly(dir)
		pprint.pprint(assemblies)
		#asasm.RetrieveFile(os.path.join(dir,'.\\_a_-_-_.class.asasm'))

	elif options.reconstruct:
		asasm=ASASM()
		asasm.DebugMethods=0
		
		assemblies=asasm.RetrieveAssembly(dir)
		asasm.WriteToFiles(assemblies,target_dir)

	elif options.method:
		asasm=ASASM()
		asasm.Instrument(dir,target_dir,[["AddMethodTraces",'']])

	elif options.basic_blocks:
		asasm=ASASM()
		asasm.Instrument(dir,target_dir,[["AddBasicBlockTraces",'']])

	elif options.api:
		asasm=ASASM()
		print 'APITrace'
		asasm.Instrument(dir,target_dir,[["AddAPITraces",''], ["Include",["Util.script.asasm"]]])

	elif options.include:
		asasm=ASASM()
		asasm.Instrument(dir,target_dir,["Include"],["../Util-0/Util.script.asasm"])
