from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtSql import *
import os
from FlashManipulation import *

class TreeItem(object):
	def __init__(self,data,parent=None,assoc_data=None):
		self.parentItem=parent
		self.itemData=data
		self.assocData=assoc_data
		self.childItems=[]

	def appendChild(self,item):
		self.childItems.append(item)

	def child(self,row):
		return self.childItems[row]

	def childCount(self):
		return len(self.childItems)

	def columnCount(self):
		return len(self.itemData)

	def getAssocData(self):
		return self.assocData

	def data(self,column):
		try:
			return self.itemData[column]
		except:
			pass

	def parent(self):
		return self.parentItem

	def row(self):
		if self.parentItem:
			return self.parentItem.childItems.index(self)
		return 0

class TreeModel(QAbstractItemModel):
	def __init__(self,parent=None):
		super(TreeModel, self).__init__(parent)
		self.DirItems={}
		self.rootItem=TreeItem(("Name",))
		self.setupModelData()

	def addDir(self,dir):
		dir_item=TreeItem((os.path.basename(dir),))
		self.rootItem.appendChild(dir_item)
		self.DirItems[dir]=dir_item

		asasm=ASASM()
		for relative_file in asasm.EnumDir(dir):
			item=TreeItem((relative_file,),dir_item)
			dir_item.appendChild(item)

	def showAsasms(self,assemblies):
		class_names=assemblies.keys()
		class_names.sort()

		for class_name in class_names:
			dir_item=TreeItem((class_name,))
			self.rootItem.appendChild(dir_item)

			[parsed_lines,methods]=assemblies[class_name]
			for [refid,[blocks,maps,labels,parents,body_parameters]] in methods.items():
				item=TreeItem((refid,),dir_item,(class_name, refid))
				dir_item.appendChild(item)

			#for [prefix,keyword,parameter,comment] in parsed_lines:

	def setupModelData(self):
		pass

	def columnCount(self,parent):
		if parent.isValid():
			return parent.internalPointer().columnCount()
		else:
			return self.rootItem.columnCount()

	def getAssocData(self,index):
		if not index.isValid():
			return None

		item=index.internalPointer()
		return item.getAssocData()

	def data(self,index,role):
		if not index.isValid():
			return None

		if role!=Qt.DisplayRole:
			return None

		item=index.internalPointer()
		return item.data(index.column())

	def headerData(self,section,orientation,role):
		if orientation==Qt.Horizontal and role==Qt.DisplayRole:
			return self.rootItem.data(section)

		return None

	def index(self,row,column,parent):
		if not self.hasIndex(row,column,parent):
			return QModelIndex()

		if not parent.isValid():
			parentItem = self.rootItem
		else:
			parentItem=parent.internalPointer()

		childItem=parentItem.child(row)

		if childItem:
			return self.createIndex(row,column,childItem)
		else:
			return QModelIndex()

	def parent(self,index):
		if not index.isValid():
			return QModelIndex()

		childItem=index.internalPointer()
		parentItem=childItem.parent()

		if parentItem!=None:
			if parentItem==self.rootItem:
				return QModelIndex()

			return self.createIndex(parentItem.row(),0,parentItem)
		return QModelIndex()

	def rowCount(self,parent):
		if parent.column()>0:
			return 0

		if not parent.isValid():
			parentItem=self.rootItem
		else:
			parentItem=parent.internalPointer()

		return parentItem.childCount()

	def flags(self,index):
		if not index.isValid():
			return Qt.NoItemFlags

		return Qt.ItemIsEnabled|Qt.ItemIsSelectable

class MainWindow(QMainWindow):
	UseDock=False
	ShowBBMatchTableView=False

	def __init__(self):
		super(MainWindow,self).__init__()
		self.setWindowTitle("Flash Hacker")
		vertical_splitter=QSplitter()

		self.treeView=QTreeView()
		vertical_splitter.addWidget(self.treeView)

		self.graph=MyGraphicsView()
		self.graph.setRenderHints(QPainter.Antialiasing)
		vertical_splitter.addWidget(self.graph)
		vertical_splitter.setStretchFactor(0,0)
		vertical_splitter.setStretchFactor(1,1)

		main_widget=QWidget()
		vlayout=QVBoxLayout()
		vlayout.addWidget(vertical_splitter)
		main_widget.setLayout(vlayout)
		self.setCentralWidget(main_widget)
		
		self.createMenus()
		self.resize(800,600)
		self.show()

	def open(self):
		dialog=QFileDialog()
		dialog.setFileMode(QFileDialog.Directory)
		dialog.setOption(QFileDialog.ShowDirsOnly)
		directory=dialog.getExistingDirectory(self,"Choose Directory",os.getcwd())

		print 'directory',directory
		if directory:
			self.showDir(directory)

	def createMenus(self):
		self.openAct=QAction("&Open...",
									self,
									shortcut=QKeySequence.Open,
									statusTip="Open an existing folder", 
									triggered=self.open)

		self.fileMenu=self.menuBar().addMenu("&File")
		self.fileMenu.addAction(self.openAct)

		self.treeViewMenu=self.menuBar().addMenu("&View")

	def showDir(self,dir):
		asasm=ASASM()	
		self.Assembly=asasm.RetrieveAssembly(dir)

		self.treeModel=TreeModel()
		self.treeModel.showAsasms(self.Assembly)
		self.treeView.setModel(self.treeModel)
		self.treeView.connect(self.treeView.selectionModel(),SIGNAL("selectionChanged(QItemSelection, QItemSelection)"), self.treeSelected)
		self.treeView.expandAll()
		#self.treeView.setSelectionMode(QAbstractItemView.MultiSelection)

	def treeSelected(self, newSelection, oldSelection):
		for index in newSelection.indexes():
			item_data=self.treeModel.getAssocData(index)
			if item_data!=None:
				(class_name,method_name)=item_data
				print class_name,method_name

				[parsed_lines,methods]=self.Assembly[class_name]
				#[blocks,maps,labels,parents,body_parameters]=methods[method_name]

				asasm=ASASM()
				[disasms,links,address2name]=asasm.ConvertMapsToPrintable(methods[method_name])
				self.graph.DrawFunctionGraph("Target", disasms, links, address2name=address2name)

if __name__=='__main__':
	import sys
	import time

	app=QApplication(sys.argv)
	#pixmap=QPixmap('DarunGrimSplash.png')
	#splash=QSplashScreen(pixmap)
	#splash.show()
	app.processEvents()
	window=MainWindow()

	if len(sys.argv)>1:
		window.showDir(sys.argv[1])

	window.show()
	#splash.finish(window)
	sys.exit(app.exec_())
