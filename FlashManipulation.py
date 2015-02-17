import sys
import dircache
import os
import pprint
from copy import *

from Graphs import *
import FlowGrapher

class ASASM:
	def __init__(self,dir=''):
		self.Assemblies={}
		self.RetrieveAssembly(dir)

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
		ret=self.ParseNameNotation(line)
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

	DebugWriteToFile=0
	def WriteLinesToFile(self,fd,parsed_lines):
		for [prefix,keyword,parameter,comment] in parsed_lines:
			line=prefix+keyword
			if parameter:
				line+=" "+parameter

			if comment:
				line+=" ;"+comment
			line+='\n'
			fd.write(line)

	def WriteToFile(self,filename,parsed_lines,methods,update_code=True):
		if self.DebugWriteToFile>0:
			print filename, methods.keys()

		fd=open(filename,'w')
		refid=''
		parents=[]
		for [prefix,keyword,parameter,comment] in parsed_lines:
			if keyword in self.BlockKeywords:
				if parameter[-3:]!='end':
					parents.append([keyword,parameter])

				if self.DebugWriteToFile>0:
					print '* parents:',parents
					
			elif keyword=='end':
				if self.DebugWriteToFile>0:
					print '- end:',refid
					print prefix,keyword,parameter,comment
					pprint.pprint(parents)

				if len(parents)>0:
					del parents[-1]
				else:
					print '* Error parsing', refid
					print prefix,keyword,parameter,comment

			elif keyword=='refid':
				refid=parameter[1:-1]
				if methods.has_key(refid):
					(blocks,maps,labels,method_parents,body_parameters)=methods[refid]
				else:
					blocks=maps=labels=body_parameters={}
					method_parents=[]
					
				if self.DebugWriteToFile>0:
					print '*'*80
					print 'refid:', refid

			elif len(parents)>0:
				if parents[-1][0]=='body' and body_parameters.has_key(keyword):
					if self.DebugWriteToFile>0:
						print '> Updaing %s with %s' % (keyword, body_parameters[keyword])
					parameter=body_parameters[keyword]

				elif update_code and parents[-1][0]=='code':
					continue

			line=prefix+keyword
			if parameter:
				line+=" "+parameter

			if comment:
				line+=" ; "+comment
			line+='\n'
			fd.write(line)

			if update_code and keyword=='code':
				code_parsed_lines=self.ConstructCode(blocks,labels)
				self.WriteLinesToFile(fd,code_parsed_lines)

		fd.close()

	def WriteToFiles(self,target_root_dir='',target_dir='',update_code=True):
		for root_dir in self.Assemblies.keys():
			if target_root_dir:
				target_dir=os.path.join(target_root_dir,os.path.basename(root_dir))

			if self.DebugWriteToFile>0:
				print 'root_dir:',root_dir
				print 'target_dir:',target_dir
				print ''

			if not os.path.isdir(target_dir):
				try:
					os.makedirs(target_dir)
				except:
					pass

			for (file,(parsed_lines,methods)) in self.Assemblies[root_dir].items():
				if self.DebugWriteToFile>0:
					print '* WriteToFiles:', file

				new_filename=os.path.join(target_dir,file)

				new_folder=os.path.dirname(new_filename)
				if not os.path.isdir(new_folder):
					try:
						os.makedirs(new_folder)
					except:
						pass

				self.WriteToFile(new_filename, parsed_lines, methods,update_code=update_code)

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

	DebugReplaceParsedLines=1
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
			print 'Replacing %s %d - %d ' % (target_refid, start_index,end_index)
			if self.DebugReplaceParsedLines>1:
				pprint.pprint(parsed_lines[start_index:end_index])
				pprint.pprint(code_parsed_lines)
			print ''

		parsed_lines[start_index:end_index]=code_parsed_lines

		return parsed_lines

	DebugParsedLines=0
	def GetParsedLines(self,parsed_lines,target_refid,type):
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

		if self.DebugParsedLines>0:
			print 'GetParsedLines %d - %d ' % (start_index,end_index)
			pprint.pprint(parsed_lines[start_index:end_index])
			print ''

		return parsed_lines[start_index:end_index]

	def ConstructCode(self,blocks,labels):
		ids=blocks.keys()
		ids.sort()

		parsed_lines=[]
		label={}
		for id in ids:
			for (keyword,parameter) in blocks[id]:
				if keyword[0:2]=='if' or keyword=='jump': #TODO: support lookupswitch
					label[int(parameter[1:])]=1

		for id in ids:
			if labels.has_key(id):
				parsed_lines.append(['',labels[id]+':','',''])
			elif label.has_key(id):
				parsed_lines.append(['','L%d:' % id,'',''])

			for (keyword,parameter) in blocks[id]:
				if parameter:
					parameter=' '*(19-len(keyword)) + parameter
				parsed_lines.append([' '*5,keyword,parameter,''])

		return parsed_lines

	DebugUpdateParsedLines=0
	def UpdateParsedLines(self,update_code=True):
		for root_dir in self.Assemblies.keys():
			for file in self.Assemblies[root_dir].keys():
				(parsed_lines,methods)=self.Assemblies[root_dir][file]
				for (refid,(blocks,maps,labels,parents,body_parameters)) in methods.items():
					body_parameter_lines=[]
					for (key,value) in body_parameters.items():
						if key!='try':
							body_parameter_lines.append(['',key,value,''])

					body_parameter_lines.append(['','code','',''])
					code_parsed_lines=[]
					if update_code:
						code_parsed_lines=self.ConstructCode(blocks,labels)
					else:
						code_parsed_lines=self.GetParsedLines(parsed_lines,refid,'code')

					body_parameter_lines+=code_parsed_lines
					body_parameter_lines.append(['','end','','code'])

					if body_parameters.has_key('try'):
						body_parameter_lines.append(['','try',body_parameters['try'],''])

					parsed_lines=self.ReplaceParsedLines(parsed_lines,refid,body_parameter_lines,'body')

				self.Assemblies[root_dir][file][0]=parsed_lines

	DebugMethods=0
	def ParseMethod(self,parsed_lines,target_method=''):
		if self.DebugMethods>0:
			print '-' * 80

		parents=[]
		new_parsed_lines=[]
		in_code=False
		methods={}
		refid=''

		body_parameters={}
		instructions=[]
		last_block_name=''
		is_last_instruction_jmp=False
		maps={}
		block_name=''
		instruction_count=0
		blocks={}
		lables={}
		labels={}

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

					label_map={}
					for (block_id,label) in labels.items():
						label_map[label]=block_id

					new_maps={}
					for [src,dsts] in maps.items():
						new_maps[src]=[]
						for dst in dsts:
							if isinstance(dst, basestring):
								if new_maps.has_key(src):
									new_maps[src].append(label_map[dst])
							else:
								new_maps[src].append(dst)

					methods[refid]=[blocks,new_maps,labels,deepcopy(parents),body_parameters]

					if self.DebugMethods>0:
						print '='*80
						pprint.pprint(blocks)
						pprint.pprint(maps)
						pprint.pprint(new_maps)
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
					labels[block_name]=keyword[0:-1]

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
					if keyword[0:2]=='if' or keyword=='jump' or keyword=='lookupswitch':
						if self.DebugMethods>0:
							print '* New block %s (end of a block)' % block_name

						if len(instructions)>0:
							jmp_labels=[]
							if keyword=='lookupswitch':
								for label in parameter.split(','):
									label=label.strip()
									if label[0]=='[':
										label=label[1:]
									if label[-1]==']':
										label=label[0:-1]

									jmp_labels.append(label)
							else:
								jmp_labels.append(parameter)
								
							blocks[block_name]=instructions

							for label in jmp_labels:
								if not maps.has_key(block_name):
									maps[block_name]=[label]
								else:
									if not label in maps[block_name]:
										maps[block_name].append(label)						

								if self.DebugMethods>0:
									print '%s -> %s (if/jmp)' % (block_name,label)
									print ''

						last_block_name=block_name
						block_name=instruction_count
						instructions=[]

					if keyword=='jump' or keyword=='lookupswitch':
						is_last_instruction_jmp=True
					else:
						is_last_instruction_jmp=False

		return methods

	def RetrieveFile(self,file,target_method=''):
		parsed_lines=self.ReadFile(file)
		methods=self.ParseMethod(parsed_lines,target_method)
		return [parsed_lines,methods]

	def RetrieveAssembly(self,root_dir,target_file='',target_method=''):
		self.Assemblies[root_dir]={}
		for relative_file in self.EnumDir(root_dir):
			if target_file=='' or target_file==relative_file:
				file=os.path.join(root_dir, relative_file)

				[parsed_lines,methods]=self.RetrieveFile(file,target_method)
				if self.DebugMethods>0:
					pprint.pprint(methods)
				self.Assemblies[root_dir][relative_file]=[parsed_lines,methods]

		return self.Assemblies

	def RetrieveAssemblies(self,dirs):
		self.Assemblies={}
		for dir in dirs:
			self.RetrieveAssembly(dir)
		return self.Assemblies

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

	DebugBasicBlockTrace=0
	def AddBasicBlockTrace(self,methods,type='block',filename='',use_buffered_trace=True):
		for refid in methods.keys():
			(blocks,maps,labels,parents,body_parameters)=methods[refid]
			for block_id in blocks.keys():
				if self.DebugBasicBlockTrace >0:
					print "="*80
					print ' %d' % block_id
					for line in blocks[block_id]:
						print line
					print ''

				if self.DebugBasicBlockTrace >0:
					print 'Instrumenting',refid,parents

				if type=='block':
					if parents[-3][0]=='method' and labels.has_key(block_id) and blocks[block_id][0][0]!='label':
						trace_code=[]

						if labels.has_key(block_id):
							message=labels[block_id]
						else:
							message='enter function'

						if use_buffered_trace:
							trace_code.append(['getlex','QName(PackageNamespace(""), "Util")'])
							trace_code.append(['pushstring','"    Label: %s"' % (message)])
							trace_code.append(['callpropvoid','QName(PackageNamespace(""), "DumpMessage"), 1'])
						else:
							trace_code.append(['findpropstrict','QName(PackageNamespace(""), "trace")'])
							trace_code.append(['pushstring','"    Label: %s"' % (message)])
							trace_code.append(['callpropvoid','QName(PackageNamespace(""), "trace"), 1'])

						blocks[block_id][0:0]=trace_code
				
				if parents[-3][0]=='method':
					if block_id==0:
						trace_code=[]

						if use_buffered_trace:
							trace_code.append(['getlex','QName(PackageNamespace(""), "Util")'])
							trace_code.append(['pushstring','"Enter: %s"' % (refid)])
							trace_code.append(['callpropvoid','QName(PackageNamespace(""), "DumpMessage"), 1'])
						else:
							trace_code.append(['findpropstrict','QName(PackageNamespace(""), "trace")'])
							trace_code.append(['pushstring','"Enter: %s"' % (refid)])
							trace_code.append(['callpropvoid','QName(PackageNamespace(""), "trace"), 1'])
						blocks[block_id][0:0]=trace_code

					new_block=[]
					for [op,operand] in blocks[block_id]:
						if op.startswith('return'):
							if use_buffered_trace:
								new_block.append(['getlex','QName(PackageNamespace(""), "Util")'])
								new_block.append(['pushstring','"Return: %s"' % (refid)])
								new_block.append(['callpropvoid','QName(PackageNamespace(""), "DumpMessage"), 1'])
							else:
								new_block.append(['findpropstrict','QName(PackageNamespace(""), "trace")'])
								new_block.append(['pushstring','"Return: %s"' % (refid)])
								new_block.append(['callpropvoid','QName(PackageNamespace(""), "trace"), 1'])
						new_block.append([op,operand])

					if len(new_block)>0:
						blocks[block_id]=new_block

					body_parameters=self.AdjustParameter(body_parameters,'maxstack',5)

			methods[refid]=(blocks,maps,labels,parents,body_parameters)
		return methods

	DebugAddAPITrace=0
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

	def AdjustParameter(self,body_parameters={},key='',value=''):
		body_parameters[key]=str(int(body_parameters[key])+value)
		return body_parameters

	def HasPattern(self,patterns,parameter):
		if len(patterns)==0:
			return True

		for pattern in patterns:
			if parameter.find(pattern)>=0:
				return True

		return False

	def AddAPITrace(self,methods,filename='',locator={},api_names={},patterns=[]):
		for refid in methods.keys():
			if len(locator)>0 and not locator.has_key(refid):
				continue

			(blocks,maps,labels,parents,body_parameters)=methods[refid]
			for block_id in blocks.keys():
				if len(locator)>0 and not locator[refid].has_key(block_id):
					continue

				if self.DebugAddAPITrace>1:
					print "="*80
					print ' %d' % block_id
					for line in blocks[block_id]:
						print line
					print ''

				if self.DebugAddAPITrace >0:
					print '* AddAPITrace',refid,parents

				if parents[-3][0]=='method':
					max_stack_count=0

					line_no=0
					for (keyword,parameter) in blocks[block_id]:
						if len(locator)>0 and not locator[refid][block_id].has_key(line_no):
							continue

						if keyword[0:4]=='call' and (api_names.has_key(self.ParseArray(parameter)[0]) or parameter.startswith('Multiname')) and self.HasPattern(patterns,parameter):
							stack_count=self.GetCallStackCount(keyword,parameter)
							if self.DebugAddAPITrace >0:
								print '* ',type,refid
								print keyword, parameter,stack_count
							if stack_count>max_stack_count:
								max_stack_count=stack_count

						line_no+=1

					orig_localcount=0
					if max_stack_count>0:
						orig_localcount=int(body_parameters['localcount'])
						new_localcount=str(orig_localcount+max_stack_count+1)

						if self.DebugAddAPITrace >0:
							print 'Increasing localcount %s -> %s' % (body_parameters['localcount'], new_localcount)

						body_parameters['localcount']=new_localcount

						if self.DebugAddAPITrace >0:
							print "Max stack count:", type, refid, max_stack_count

						body_parameters=self.AdjustParameter(body_parameters,'maxstack',5)

					new_blocks=[]
					line_no=0
					for (keyword,parameter) in blocks[block_id]:
						if self.DebugAddAPITrace>1:
							print refid,block_id
							print 'Line no:',line_no
							pprint.pprint(locator[refid][block_id])

						if len(locator)>0 and not locator[refid][block_id].has_key(line_no):
							pass

						elif keyword[0:4]=='call' and (len(locator)>0 or (api_names.has_key(self.ParseArray(parameter)[0]) or parameter.startswith('Multiname')) and self.HasPattern(patterns,parameter)):
							if self.DebugAddAPITrace >-1:
								print "Hooking %s %s (at %s/%d/%d)" % (keyword,parameter,refid,block_id,line_no)

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
								new_blocks.append(['callpropvoid','QName(PackageNamespace(""), "DumpAPI"), 4'])

								for i in range(0,stack_count,1):
									new_blocks.append(['getlocal','%d' % (current_local_count-1-i) ])

						new_blocks.append([keyword,parameter])
						line_no+=1

					blocks[block_id]=new_blocks

			methods[refid]=(blocks,maps,labels,parents,body_parameters)
		return methods

	DebugInstrument=0
	def Instrument(self,operations=[],target_refids=[]):
		[local_names,api_names,multi_names,multi_namels]=self.GetNames()

		for root_dir in self.Assemblies.keys():
			for file in self.Assemblies[root_dir].keys():
				for (operation,options) in operations:
					if self.DebugInstrument>0:
						print '* Instrumenting', file, operation, options

					if operation=="AddBasicBlockTrace":
						self.Assemblies[root_dir][file][1]=self.AddBasicBlockTrace(self.Assemblies[root_dir][file][1],filename=file)

					if operation=="AddAPITrace":
						patterns=[]
						if options.has_key('Patterns'):
							patterns=options['Patterns']

						if options.has_key('Locator'):
							locator=options['Locator']

						self.Assemblies[root_dir][file][1]=self.AddAPITrace(self.Assemblies[root_dir][file][1],filename=file,locator=locator,api_names=api_names,patterns=patterns)

					if operation=="Replace":
						for [orig,replace] in options:
							parsed_lines=self.ReplaceSymbol(parsed_lines,orig,replace)
							"""
							if not filename_replaced and basename.find(orig)>=0:
								new_filename=os.path.join(new_folder,basename.replace(orig,replace))
								filename_replaced=True
							"""

					if operation=="AddMethodTrace":
						self.Assemblies[root_dir][file][1]=self.AddBasicBlockTrace(self.Assemblies[root_dir][file][1],type='function',filename=file)

					if operation=="Include":
						if file[-1*len('.main.asasm'):]=='.main.asasm':
							if self.DebugInstrument>0:
								print 'Updating', file
							[process_lines,methods]=self.Assemblies[root_dir][file]
							for index in range(0,len(process_lines),1):
								(prefix,keyword,parameter,comment)=process_lines[index]
								if keyword=='end':
									if self.DebugInstrument>0:
										print 'Inserting #include statement:', options
									include_lines=[]
									for include_file in options:
										include_lines.append([' ',"#include",'"%s"' % include_file,''])
									process_lines[index:index]=include_lines
									break

							if self.DebugInstrument>1:
								pprint.pprint(process_lines)

							self.Assemblies[root_dir][file][0]=process_lines

	def Save(self,target_root_dir='',target_dir=''):
		if target_root_dir or target_dir:
			if self.DebugInstrument>0:
				if target_root_dir:
					print 'Write to files:', target_root_dir
				else:
					print 'Write to files:', target_dir
			self.WriteToFiles(target_root_dir=target_root_dir,target_dir=target_dir)

	DebugParse=0
	def ParseTraitLine(self,line):
		if self.DebugParse>0:
			print line
		element=''
		body=''
		inside_body=False
		parents=[]
		elements=[]
		last_ch=''
		for ch in line:
			if len(parents)>0:
				if self.DebugParse>0:
					print ch,
				if inside_string:
					if ch=='"' and last_ch!='\\':
						inside_string=False
				else:
					if ch=='"':
						inside_string=True

				if not inside_string:
					if ch=='(':
						parents.append(ch)
						if self.DebugParse>0:
							print '\n\t+',parents

					elif ch==')':
						del parents[-1]
						if self.DebugParse>0:
							print '\n\t-',parents
				element+=ch
			else:
				if self.DebugParse>0:
					print ch,

				if element:
					if ch=='(':
						parents.append(ch)
						if self.DebugParse>0:
							print '\n+',parents
						inside_string=False
						element+=ch
					elif ch==' ':
						elements.append(element)
						if self.DebugParse>0:
							print '\nFound:',element
							print ''
						element=''
					else:
						element+=ch
				else:
					element+=ch

			last_ch=ch

		if element:
			elements.append(element)
			if self.DebugParse>0:
				print '\nFound:',element
				print ''

		if self.DebugParse>0:
			print elements
		return elements

	def ParseNameBody(self,line):
		name=''
		body=''
		inside_body=False
		parents=[]
		last_ch=''
		for ch in line:
			if len(parents)>0:
				if self.DebugParse>0:
					print '*', ch
				if inside_string:
					if ch=='"' and last_ch!='\\':
						inside_string=False
				else:
					if ch=='"':
						inside_string=True
				if not inside_string:
					if ch in ('[','('):
						parents.append(ch)
						if self.DebugParse>0:
							print parents
					elif ch in (']',')'):
						del parents[-1]
						if self.DebugParse>0:
							print parents
						if len(parents)==0:
							break
				body+=ch
			else:
				if name and ch=='(':
					parents.append(ch)
					inside_string=False
				else:
					name+=ch
			last_ch=ch
		return [name,body]

	def ParseArray(self,line):
		parents=[]
		last_ch=''
		inside_string=False
		current_element=''
		array=[]
		for ch in line:
			if self.DebugParse>0:
				print ch,

			if inside_string:
				if ch=='"' and last_ch!='\\':
					inside_string=False
			else:
				if ch=='"':
					inside_string=True

			if not inside_string:
				if ch in ('[','('):
					parents.append(ch)
					if self.DebugParse>0:
						print '\n* opening:',parents
						print ''
				elif ch in (']',')'):
					del parents[-1]
					if self.DebugParse>0:
						print '\n* closing:',parents
						print ''
				if len(parents)==0 and ch==',':
					if self.DebugParse>0:
						print '\n* current_element:',current_element
						print ''
					array.append(current_element)
					current_element=''
				else:
					if not current_element and (ch==' ' or ch=='\t'):
						pass
					else:
						current_element+=ch
			else:
				current_element+=ch

			last_ch=ch

		if current_element:
			array.append(current_element)
		return array

	def ParseQName(self,qname):
		if self.DebugParse>0:
			print ''
			print '* ParseQName:', qname

		[name_type,body]=self.ParseNameBody(qname)
		body_elements=self.ParseArray(body)

		if self.DebugParse>0:
			print 'Name:',name_type
			print 'Body:',body
			print 'Body elements:',body_elements

		[first_arg_name, first_arg_param]=self.ParseNameBody(body_elements[0])
		first_arg_elements=self.ParseArray(first_arg_param)
		body_elements[0]=[first_arg_name,first_arg_elements]

		if self.DebugParse>0:
			print '1st Arg Name:', first_arg_name
			print '1st Arg Element:', first_arg_elements
			print 'Body elements:',body_elements

		return [name_type, body_elements]

	def AsmQName(self,(name_type, body_elements),remove_ns_arg=False):
		[first_arg_name,first_arg_elements]=body_elements[0]

		if remove_ns_arg and len(first_arg_elements)>1:
			del first_arg_elements[1]
		new_body_elements=deepcopy(body_elements)
		new_body_elements[0]='%s(%s)' % (first_arg_name,', '.join(first_arg_elements))
		body=', '.join(new_body_elements)
		return '%s(%s)' % (name_type,body)

	def ParseMultiname(self,multiname):
		[name_type,body]=self.ParseNameBody(multiname)

		if self.DebugParse>0:
			print name_type
			print ''
			print body
			print ''

		elements=[]
		for element in self.ParseArray(body[1:-1]):
			if self.DebugParse>0:
				print '* Parsing:', element
			[name,param]=self.ParseNameBody(element)
			param_elements=self.ParseArray(param)

			if self.DebugParse>0:
				print 'Name:', name
				print 'Param:', param
				print ''
				print param_elements
				print ''
				print ''

			elements.append([name,param_elements])

		return [name_type,elements]

	DebugNames=0
	def GetAPINames(self):
		[local_names,api_names,multi_names,multi_namels]=self.GetNames()

		ret=[]
		for [api_name,callers] in api_names.items():
			found_call=False
			for [op,root_dir,class_name,refid,block_id,block_line_no] in callers:
				if op.startswith('call'):
					found_call=True
					break
			if found_call:
				ret.append(api_name)
		return ret

	def GetNames(self):
		local_namespaces={}
		refids={}
		for root_dir in self.Assemblies.keys():
			for [class_name,[parsed_lines,methods]] in self.Assemblies[root_dir].items():
				for [refid,[blocks,maps,labels,parents,body_parameters]] in methods.items():
					refids[refid]=1

				for [prefix,keyword,parameter,comment] in parsed_lines:
					if keyword=='instance':
						local_namespaces[parameter]=1

					elif keyword=='trait':
						trait_elements=self.ParseTraitLine(parameter)
						if len(trait_elements)>1:
							local_namespaces[trait_elements[1]]=1
						else:
							if self.DebugNames>0:
								print parameter

		if self.DebugNames>0:
			print refids.keys()
			print local_namespaces.keys()

		local_names={}
		api_names={}
		multi_names={}
		multi_namels={}

		for root_dir in self.Assemblies.keys():
			for [class_name,[parsed_lines,methods]] in self.Assemblies[root_dir].items():
				for [refid,[blocks,maps,labels,parents,body_parameters]] in methods.items():
					for [block_id,block] in blocks.items():
						block_line_no=0
						for [op,operand] in block:
							if not op:
								continue

							if not operand or operand.startswith('"'):
								pass
							elif operand.startswith('QName('):
								if self.DebugNames>0:
									print '*', operand
							
								qnames=self.ParseArray(operand)
								qname=qnames[0]

								if local_namespaces.has_key(qname):
									if self.DebugNames>0:
										print 'Local Name:', qname, op, refid, block_id, block_line_no

									if not local_names.has_key(qname):
										local_names[qname]=[]
									local_names[qname].append([op, root_dir, refid, block_id, block_line_no])
								else:
									qname_parts=self.ParseQName(qname)
									qname=self.AsmQName(qname_parts,remove_ns_arg=True)
									if local_namespaces.has_key(qname):
										if self.DebugNames>0:
											print 'Local Name:', qname, op, refid, block_id, block_line_no

											if not local_names.has_key(qname):
												local_names[qname]=[]
											local_names[qname].append([op, root_dir, class_name, refid, block_id, block_line_no])
									else:
										if self.DebugNames>0:
											print 'API Name:', qname, op, refid, block_id, block_line_no
									
										if not api_names.has_key(qname):
												api_names[qname]=[]
										api_names[qname].append([op, root_dir, class_name, refid, block_id, block_line_no])

								ret=self.ParseQName(qname)
								if len(ret[1])>0:
									[namespace_note,arg]=ret[1]
									[namespace,param]=namespace_note

									if self.DebugNames>0:
										print namespace
										print param
									arg=arg[1:-1]

									if refids.has_key(arg):
										print 'Local arg:', arg

							elif operand.startswith('MultinameL'):
								name=self.ParseArray(operand)[0]
								if not multi_namels.has_key(name):
									multi_namels[name]=[]
								multi_namels[name].append([op, root_dir, class_name, refid, block_id, block_line_no])

								if self.DebugNames>0:
									print '*', operand
									pprint.pprint(self.ParseMultiname(operand))
									print ''

							elif operand.startswith('Multiname'):
								name=self.ParseArray(operand)[0]
								if not multi_names.has_key(name):
									multi_names[name]=[]
								multi_names[name].append([op, root_dir, class_name, refid, block_id, block_line_no])

								if self.DebugNames>0:
									print '*', operand
									pprint.pprint(self.ParseMultiname(operand))
									print ''

							elif operand.startswith('TypeName'):
								if self.DebugNames>0:
									print '*', operand
									print ''

							elif operand=='null':
								pass
							elif operand[0]=='L':
								pass
							elif ord(operand[0])>=ord('0') and ord(operand[0])<=ord('9') or operand[0]=='-':
								pass
							else:
								print operand

							block_line_no+=1

		if self.DebugNames>0:
			pprint.pprint(local_names)
			pprint.pprint(api_names)

		return [local_names,api_names,multi_names,multi_namels]

	DebugLoadLogFile=0
	def LoadLogFile(self,log_filename):
		if self.DebugLoadLogFile>0:
			print 'Opening', log_filename

		fd=open(log_filename,'r')

		callstack_list=[]
		methods_callstack=[]
		while True:
			line=fd.readline()
			if not line:
				break
			line=line.strip()

			func_name=''
			if line.startswith('Enter: '):
				func_name=line[len('Enter: '):]
				methods_callstack.append(func_name)
				callstack_list.append(deepcopy(methods_callstack))
				if self.DebugLoadLogFile>0:
					print 'Enter ', func_name
					print '\t',methods_callstack

			elif line.startswith('Return: '):
				func_name=line[len('Return: '):]

				if len(methods_callstack)>0:
					for i in range(len(methods_callstack)-1,-1,-1):
						if methods_callstack[i]==func_name:
							if i!=len(methods_callstack)-1:
								print 'Skip Return', methods_callstack

							if self.DebugLoadLogFile>0:
								print 'Return', func_name
								print '\t',methods_callstack

							methods_callstack=methods_callstack[0:i]

							if self.DebugLoadLogFile>0:
								print '\t',methods_callstack
							break

		if self.DebugLoadLogFile>0:
			pprint.pprint(callstack_list)

		non_repetition_start=0
		last_repeated_n=0
		repeat_info={}
		repeat_info_list=[]
		for i in range(1,len(callstack_list)+1,1):
			if self.DebugLoadLogFile>0:
				print ''
				print 'Line:',i-1,callstack_list[i-1]

			found_repetition=False
			for n in range(1,4,1):
				if self.DebugLoadLogFile>1:
					print '\tComparing:'
					print '\t\t %d-%d %s' % (i-n*2, i-n, str(callstack_list[i-n*2:i-n]))
					print '\t\t %d-%d %s' % (i-n, i, str(callstack_list[i-n:i]))

				if str(callstack_list[i-n*2:i-n])==str(callstack_list[i-n:i]):
					if last_repeated_n==n:
						repeat_info['repeated']+=1

						if self.DebugLoadLogFile>0:
							print '\t+Repetition continuation %d repeated' % (repeat_info['repeated'])
						non_repetition_start=i
					else:
						if self.DebugLoadLogFile>0:
							print '\t> New repetition started: (%d:%d == %d:%d) %s' % (i-n*2,i-n, i-n,i, callstack_list[i-n:i])
							print '\t> Save non-repetitions (%d-%d)' % (non_repetition_start,i-n*2)
							print '\t\t', pprint.pformat(callstack_list[non_repetition_start:i-n*2])

						repeat_info_list.append({'callstack': callstack_list[non_repetition_start:i-n*2], 'repeated': 1})
						non_repetition_start=i
						repeat_info['callstack']=callstack_list[i-n:i]
						repeat_info['repeated']=2

						if self.DebugLoadLogFile>0:
							print '\t> New repeat_info:',repeat_info['callstack'], "repeated\t", repeat_info['repeated']

					found_repetition=True
					last_repeated_n=n
					break

			if not found_repetition:
				if len(repeat_info):
					if self.DebugLoadLogFile>0:
						print '\t> Save repetition:',repeat_info['callstack'], "repeated\t", repeat_info['repeated']

					repeat_info_list.append(deepcopy(repeat_info))
					repeat_info={}
				
					non_repetition_start=i-1

					if self.DebugLoadLogFile>0:
						print '\t> New non-repetition starts:',non_repetition_start

				last_repeated_n=0
		
		if non_repetition_start!=len(callstack_list)-1:
			repeat_info_list.append({'callstack': callstack_list[non_repetition_start:], 'repeated': 1})

		if len(repeat_info)>0:
			if self.DebugLoadLogFile>0:
				print repeat_info['callstack'], "repeated\t", repeat_info['repeated']

			repeat_info_list.append(deepcopy(repeat_info))

		if self.DebugLoadLogFile>0:
			pprint.pprint(repeat_info_list)

		if self.DebugLoadLogFile>0:
			last_call_stack=[]
			for repeat_info in repeat_info_list:
				print 'New Repeat Info:'
				for call_stack in repeat_info['callstack']:
					for call_stack_line in call_stack:
						print '\t',call_stack_line

					j=0
					while j<min(len(call_stack),len(last_call_stack)):
						if call_stack[j]!=last_call_stack[j]:
							break
						j+=1

					print '\tCommon stack list:',j,call_stack[0:j]
					print ''

					last_call_stack=deepcopy(call_stack)
										
				print '\t',repeat_info['repeated']
				print ''

		return repeat_info_list

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
	parser.add_option("-D","--dump",dest="dump",action="store_true",default=False)
	parser.add_option("-m","--method",dest="method",action="store_true",default=False)
	parser.add_option("-b","--basic_blocks",dest="basic_blocks",action="store_true",default=False)
	parser.add_option("-a","--api",dest="api",action="store_true",default=False)
	parser.add_option("-T","--test",dest="test",help="Perform basic tests",default='',metavar="TEST")
	parser.add_option("-d","--asasm_dir",dest="asasm_dir",help="",default='',metavar="ASASM_DIR")
	parser.add_option("-t","--target_dir",dest="target_dir",help="",default='',metavar="ASASM_SAVE_DIR")

	(options,args)=parser.parse_args()
	if options.graph:
		app=QApplication(sys.argv)
		frame=MainWindow()
		frame.Draw(options.asasm_dir)
		frame.setGeometry(100,100,800,500)
		frame.show()
		sys.exit(app.exec_())

	elif options.test:
		if options.test.lower()=='names':
			asasm=ASASM(options.target_dir)
			[local_names,api_names,multi_names,multi_namels]=asasm.GetNames()
			pprint.pprint(local_names)
			pprint.pprint(api_names)

		elif options.test.lower()=='include':
			asasm=ASASM(options.target_dir)
			asasm.Instrument(operations=[["Include",["../Util-0/Util.script.asasm"]]])

		elif options.test.lower()=='reconstruct':
			asasm.DebugMethods=0
			asasm.WriteToFiles()

		elif options.test.lower()=='name':
			asasm=ASASM()

			multinames=[]
			multinames.append("""MultinameL([PrivateNamespace("*", "_a_-_---/class#0"), PackageNamespace(""), PrivateNamespace("*", "_a_-_---/class#1"), PackageInternalNs(""), Namespace("http://adobe.com/AS3/2006/builtin"), ProtectedNamespace("_a_-_---"), StaticProtectedNs("_a_-_---"), StaticProtectedNs("flash.display:Sprite"), StaticProtectedNs("flash.display:DisplayObjectContainer"), StaticProtectedNs("flash.display:InteractiveObject"), StaticProtectedNs("flash.display:DisplayObject"), StaticProtectedNs("flash.events:EventDispatcher"), StaticProtectedNs("Object")])""")
			multinames.append(""""Multiname("IFlexAsset", [PackageNamespace("mx.core")])""")
			multinames.append("""Multiname("Vector", [PrivateNamespace("*", "catch for/instance#0"), PackageNamespace("flash.system"), PackageNamespace("", "#0"), Namespace("http://adobe.com/AS3/2006/builtin"), PrivateNamespace("*", "catch for/instance#1"), PackageInternalNs(""), PackageNamespace("flash.display"), PackageNamespace("flash.events"), PackageNamespace("flash.utils"), ProtectedNamespace("catch for"), StaticProtectedNs("catch for"), StaticProtectedNs("flash.display:MovieClip"), StaticProtectedNs("flash.display:Sprite"), StaticProtectedNs("flash.display:DisplayObjectContainer"), StaticProtectedNs("flash.display:InteractiveObject"), StaticProtectedNs("flash.display:DisplayObject"), StaticProtectedNs("flash.events:EventDispatcher"), PackageNamespace("__AS3__.vec")])""")
			for multiname in multinames:
				print '*', multiname
				ret=asasm.ParseMultiname(multiname)
				pprint.pprint(ret)
				print ''

			qname="""QName(PrivateNamespace("*", "catch for/instance#0"), "521423832396123423632234")"""
			print '*',qname
			pprint.pprint(asasm.ParseQName(qname))
			print ''

			qname='QName(Namespace("http://www.adobe.com/2006/flex/mx/internal"), "VERSION")'
			print '*',qname
			pprint.pprint(asasm.ParseArray(qname))
			print ''

			qname='QName(PrivateNamespace("*", "catch for/instance#0"), "52142332316123423632234"), 1'
			print '*',qname
			pprint.pprint(asasm.ParseArray(qname))
			print ''

			qname='QName(PackageNamespace("", "#3"), "_a_-_---")'
			print '*',qname
			qname_parts=asasm.ParseQName(qname)
			pprint.pprint(qname_parts)
			print asasm.AsmQName(qname_parts,remove_ns_arg=True)
			print ''

		elif options.test.lower()=="trait":
			trait="""trait method QName(PrivateNamespace("*", "_a_-_---/class#0"), "_a_--__") flag FINAL dispid 4"""
			asasm=ASASM()
			print asasm.ParseTraitLine(trait)

		elif options.test.lower()=="loadlogfile":
			asasm=ASASM()
			asasm.LoadLogFile(args[0])

	else:
		asasm=ASASM(options.asasm_dir)

		if options.dump:
			pprint.pprint(asasm.Assemblies)

		if options.replace:
			replace_patterns=[]

			replace_patterns.append(["_a_--__-","class02"])
			replace_patterns.append(["_a_-_---","class04"])
			replace_patterns.append(["_a_-_-__","class06"])
			replace_patterns.append(["_a_---","class01"])
			replace_patterns.append(["_a_-_-_","class05"])
			replace_patterns.append(["_a_-_","class03"])

			new_folder=r"..\payload-0.mod"
		
			print asasm.GetName(r'QName(PackageNamespace(""), "class03")')
			asasm.RetrieveAssemblies(['payload-0'])
			asasm.Instrument()

			asasm.RetrieveAssemblies(['payload-1'])
			asasm.Instrument()

		if options.api:
			asasm.Instrument(operations=[["AddAPITrace",{'Patterns':['MultinameL']}], ["Include",["../Util-0/Util.script.asasm"]]], target_refids=args)

		if options.method:
			asasm.Instrument(operations=[["AddMethodTrace",'']])

		if options.basic_blocks:
			asasm.Instrument(operations=[["AddBasicBlockTrace",'']])

		if options.target_dir:
			asasm.Save(target_dir=options.target_dir)
