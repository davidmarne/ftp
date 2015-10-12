import sys
from PySide import QtCore as core
from PySide import QtGui as qt
from PySide import QtNetwork as qnw
import re

class MainFrame(qt.QMainWindow):
    DIR_TYPE = 1000
    FILE_TYPE = 1001
    
    
    def __init__(self):
        super(MainFrame, self).__init__()
        
        self.initUI()
        
    def initUI(self):
        #layout variables
        cw = qt.QWidget()
        self.setCentralWidget(cw)
        grid = qt.QGridLayout()
        
        #toolbar action
        openAction = qt.QAction(self.style().standardIcon(qt.QStyle.SP_DriveNetIcon), 'Open Connection', self)
        openAction.triggered.connect(self.openConnectionWin)
        #toolbar
        self.toolbar = self.addToolBar('FTP')
        self.toolbar.addAction(openAction)
        
        #init identifiers dictionary
        self.identifiers = {}
        #init ftp
        self.ftp = qnw.QFtp(self)

        #ftp tree
        self.serverTree = qt.QTreeWidget()
        self.serverTree.itemDoubleClicked.connect(self.twDblClicked)
        #self.serverTree.dropEvent.connect(self.itemDropped)
        lbls = ["Name", "Size"]
        self.serverTree.setHeaderLabels(lbls)
        self.serverTree.setColumnWidth(0,200)
        
        #parent directory button is put on toolbar
        icn = self.style().standardIcon(qt.QStyle.SP_FileDialogToParent)
        upBtn = qt.QAction(icn, "Parent dir", self)
        upBtn.triggered.connect(self.upDir)
        self.toolbar.addAction(upBtn)
        
        #layout code
        policy = qt.QSizePolicy(qt.QSizePolicy.Expanding,qt.QSizePolicy.Expanding)
        self.serverTree.setSizePolicy(policy)
        grid.addWidget(self.serverTree,0,0)
        cw.setLayout(grid)
        self.setGeometry(100, 100, 450, 575)
        self.setWindowTitle('FTP')
        self.setWindowIcon(qt.QIcon('icon.png'))     
        self.show()

    def openConnectionWin(self):
        #opens widget to let user enter connection info
        self.connWid = openConnFrame(self)
        self.connWid.show()


    def openConnection(self):
        #if previous ftp connection has been established
        #then close it befor we open a new one
        if self.ftp.state() == qnw.QFtp.Connected:
            self.ftp.close()
        
        #get the login info from the connection form and establish a connection
        host = self.connWid.getUrl()
        self.identifiers[self.ftp.connectToHost(host)] = 'connect'
        usrnm = self.connWid.getUserName()
        pswd = self.connWid.getPassword()
        self.identifiers[self.ftp.login(usrnm,pswd)] = 'login'
        
        #establish event listeners for the ftp object
        self.ftp.listInfo.connect(self.addWidToTree)
        self.ftp.rawCommandReply.connect(self.replyRecieved)
        self.ftp.commandFinished.connect(self.commandFin)
        
        #clear the tree widget and repopulate with current directory
        self.serverTree.clear()
        self.identifiers[self.ftp.list()] = 'list'

        #initializes currentpath class variable
        self.lastCmd = "pwd"
        self.identifiers[self.ftp.rawCommand("pwd")] = 'raw'

        #close the connection frame
        self.connWid.close()

    #called when listInfo() is signaled (whenever list() is called)
    #populates the tree widget
    def addWidToTree(self, qi):
        if qi.isDir():
            item = qt.QTreeWidgetItem(self.DIR_TYPE)
            icn = self.style().standardIcon(qt.QStyle.SP_DirIcon)
        else:
            item = qt.QTreeWidgetItem(self.FILE_TYPE)
            icn = self.style().standardIcon(qt.QStyle.SP_FileIcon)
        item.setIcon(0, icn)
        item.setText(0, qi.name())
        item.setText(1, str(qi.size()))
        self.serverTree.addTopLevelItem(item)
            
    #called when a reply is recieved from a 'raw command'
    def replyRecieved(self, num, text):
        if self.lastCmd == "pwd":
            self.currentPath = re.compile('\"(.*?)\"').search(text).group(1)

    #called when a tree widget item is double clicked
    def twDblClicked(self, itm, clm):
        #if it is a directory open it
        #elif its is a fil download it
        if itm.type() == self.DIR_TYPE:
            self.currentPath = self.currentPath + itm.text(0) + "/"
            self.identifiers[self.ftp.cd(self.currentPath)] = 'cd'
            self.serverTree.clear()   
            self.identifiers[self.ftp.list()] = 'list'
        elif itm.type() == self.FILE_TYPE:
            name = itm.text(0)
            self.fileToSave = core.QFile(name)
            self.fileToSave.open(core.QIODevice.WriteOnly)
            self.identifiers[self.ftp.get(name)] = 'get'
            
    #opens the parent directory
    def upDir(self):
        #cd to the parent folder
        self.identifiers[self.ftp.cd("..")] = 'cd'
        #update currentpath class variable
        self.lastCmd = "pwd"
        self.identifiers[self.ftp.rawCommand("pwd")] = 'raw'
        #clear the tree so it can be populated with the new directory
        self.serverTree.clear()
        self.identifiers[self.ftp.list()] = 'list'

    #called when commandFinished signal is called
    #decides what to do with the reply depending on what command it was
    def commandFin(self, iden, ok):
        print("iden: "+ str(iden))
        print("val: " + self.identifiers[iden])
        if self.identifiers[iden] == 'get':
            x = self.fileToSave.write(self.ftp.readAll())
            self.fileToSave.close()
        del self.identifiers[iden]

    #called when dropEvent is signaled
    #def itemDropped(self, evnt):
        
        
class openConnFrame(qt.QWidget):
    def __init__(self, parent):
        super(openConnFrame, self).__init__()
        
        self.initUI(parent)
        
    def initUI(self, parent):
        #layout for widget
        self.grid = qt.QGridLayout()
        self.setLayout(self.grid)

        #combo box of saved connections
        connCB = qt.QComboBox()
        info =  core.QFile("connInfo")
        self.infos = []
        connCB.addItem("Select Connection")
        if info.exists():
            info.open(core.QIODevice.ReadOnly)
            textstrmIn = core.QTextStream(info)
            while textstrmIn.atEnd() == False:
                wholeLine = textstrmIn.readLine()
                vals = re.split(' ', wholeLine)
                self.infos.append(vals)
                connCB.addItem(vals[0])
            info.close()
        connCB.activated.connect(self.fillFields)
        self.grid.addWidget(connCB, 0,0)
        #host
        urlLbl = qt.QLabel("Host URL: ")
        self.urlLW = qt.QLineEdit()
        self.grid.addWidget(urlLbl, 1,0)
        self.grid.addWidget(self.urlLW,1,1) 
        #username
        usrnmLbl = qt.QLabel("Username: ")
        self.ursnmLW = qt.QLineEdit()
        self.grid.addWidget(usrnmLbl, 2,0)
        self.grid.addWidget(self.ursnmLW, 2,1)
        #pswd
        pswdLbl = qt.QLabel("Password: ")
        self.pswdLW = qt.QLineEdit()
        self.grid.addWidget(pswdLbl, 3,0)
        self.grid.addWidget(self.pswdLW, 3,1)
        #submit 
        self.submitBtn = qt.QPushButton( "Connect")
        self.submitBtn.clicked.connect(parent.openConnection)
        self.grid.addWidget(self.submitBtn, 4,0)
        #save
        self.saveBtn = qt.QPushButton("Save Connection")
        self.saveBtn.clicked.connect(self.saveConnection)
        self.grid.addWidget(self.saveBtn, 4,1)
        
        self.resize(300,100)
        self.setWindowTitle("Open Connection")

    def getUrl(self):
        return self.urlLW.text()
    def getUserName(self):
        return self.ursnmLW.text()
    def getPassword(self):
        return self.pswdLW.text()

    def saveConnection(self):
        toWrite = self.getUrl()+' '+self.getUserName()+' '+self.getPassword()+'\n'
        ConnInfoFile = core.QFile("connInfo")
        if ConnInfoFile.exists():
            ConnInfoFile.open(core.QIODevice.Append)
        else:
            ConnInfoFile.open(core.QIODevice.WriteOnly)
        textstrmOut = core.QTextStream(ConnInfoFile)
        textstrmOut << toWrite
        ConnInfoFile.close()

    def fillFields(self, name):
        if name != 0:
            name = name - 1
            self.urlLW.setText(self.infos[name][0])
            self.ursnmLW.setText(self.infos[name][1])
            self.pswdLW.setText(self.infos[name][2])

def main():
    
    app = qt.QApplication(sys.argv)
    ex = MainFrame()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()