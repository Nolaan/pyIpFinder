#!/usr/bin/python

import sys, getpass, os, subprocess, re
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QThread, pyqtSlot, SLOT
from ui_pyipfinder import Ui_MainWindow

try:
    import nmap
except ImportError:
    p = subprocess.Popen(['python','setup.py','install','--user'],cwd="python-nmap")
    p.wait()
    username = getpass.getuser()
    sys.path.insert(0,'/home/' + username + '/.local/lib/python2.7/site-packages')
    try:
        import nmap
    except:
        print "Couldnt install nmap! Exiting\n"
        exit(1)



class ModalThread(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self, parent)

    def run(self):
        # waiting modal window + label
        Dialog = QtGui.QDialog(myapp)
        Dialog.resize(300,230)
        verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        verticalLayout = QtGui.QVBoxLayout()
        label = QtGui.QLabel(Dialog)
        label.setAlignment(QtCore.Qt.AlignCenter)
        verticalLayout.addWidget(label)
        verticalLayout_2.addLayout(verticalLayout)
        Dialog.setWindowTitle("Wait")
        label.setText("Scanning...")
        Dialog.setModal(True)
        Dialog.exec_()


class ThreadedScan(QThread):
    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.parent = parent
        self.connect(self,QtCore.SIGNAL("updateGuiList"),parent.updateList)
        print "Scan init done"
        

    def run(self):
        print "Scan started!"
        rpi_list = filter_results(scan_list(get_networks()))
        # rpi_list = filter_results(["10.42.0.167"])
        # Let's close the modal window
        if self.parent.Dialog != None:
            self.parent.Dialog.deleteLater()
            self.parent.Dialog = None
        print "Scan ended!"
        if len(rpi_list) > 0 :
            print "This is the list of IP for Rpi : " + str(rpi_list)
        else : 
            print "The scan returned an empty list"
        
        self.emit(QtCore.SIGNAL("updateGuiList"),rpi_list)
        print "Emitted"


class NewPiBlock(QtGui.QWidget):
    def __init__(self, item, parent=None):
        QtGui.QWidget.__init__(self, parent)

        # Recuperer le scroll area
        self.scrollArea = parent.ui.scrollArea
        
        self.verticalLayout = parent.ui.verticalLayout
        self.horizontalLayout = QtGui.QHBoxLayout()
        rpi_image = QtGui.QImage("./rpi.png")
        pixmap = QtGui.QPixmap.fromImage(rpi_image) 
        scene = QtGui.QGraphicsScene()
        scene.setSceneRect(0, 0, 140, 140)
        scene.addPixmap(pixmap)
        self.graphicsView = QtGui.QGraphicsView()
        self.graphicsView.setMinimumSize(QtCore.QSize(150,170))
        self.graphicsView.setMaximumSize(QtCore.QSize(150, 16777215))
        self.graphicsView.setScene(scene)
        self.horizontalLayout.addWidget(self.graphicsView)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.label_2 = QtGui.QLabel()
        self.label_2.setText("IP Address : \n" + str(item[0]))
        self.verticalLayout_3.addWidget(self.label_2)
        self.label = QtGui.QLabel()
        self.label.setText("MAC Address : \n" + str(item[1]))
        self.verticalLayout_3.addWidget(self.label)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.line = QtGui.QFrame()
        self.line.setFrameShape(QtGui.QFrame.HLine)
        self.line.setFrameShadow(QtGui.QFrame.Sunken)
        self.verticalLayout.addWidget(self.line)
        # self.setLayout(self.verticalLayout)




class MyMainWindow(QtGui.QMainWindow):
    def __init__(self, parent=None):
        QtGui.QWidget.__init__(self, parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

    @pyqtSlot(list)
    def updateList(self,rpi_list):
        """ Update GUI with the list of found rpi (ipAddr, macAddr)"""

        print "updating :D"
        listLen = len(rpi_list) 
        if listLen == 1:
            self.ui.label_2.setText("IP Address : \n" + str(rpi_list[0][0]))
            self.ui.label.setText("MAC Address : \n" + str(rpi_list[0][1]))
            self.ui.deviceNumbertext.setText("Found 1 device")

            
        elif listLen > 1 :
            self.ui.label_2.setText(str(rpi_list[0][0]))
            self.ui.label.setText(str(rpi_list[0][1]))
            self.ui.deviceNumbertext.setText("Found "+ str(listLen) + " device")
            # Adding new blocks
            for i in range (1,listLen):
                self.ui.formLayout.addRow(NewPiBlock(rpi_list[i],parent=self))

        else:
            self.ui.label_2.setText("NO DEVICE FOUND")
            self.ui.label.setText("MAYBE LAUNCH THE \nAPP WITH SUDO")


    def rescan(self):
        if self.scan.isFinished():
            self.scan = ThreadedScan(self)
            self.scan.start()
        else:
            self.scan.quit()
            self.scan = ThreadedScan(self)
            self.scan.start()



def scan_list(network):
    """ Scan a given network trunk """
    nm = nmap.PortScanner()         # instantiate nmap.PortScanner object
    device_list = []
    for trunk in network:
        nm.scan(hosts=trunk, arguments='-sn')
        for device in nm.all_hosts():
            device_list.append(device.encode("ascii"))
    return device_list

def filter_results(devicesList):
    """ Filters and grep results """
    nm = nmap.PortScanner()
    rpi_list =[]

    for ip in devicesList:
        nm.scan(hosts=ip, arguments="-sn")
        for device in nm.all_hosts():
            if 'mac' in nm[device]['addresses']:
                vendorName = "".join(nm[device]['vendor'].values())
                if re.match("Raspberry Pi",vendorName):
                    rpi_list.append([ip,nm[device]['addresses']['mac'].encode("ascii")])
    return rpi_list



def get_networks():
    """ Scan cards and returns the networks reachable by the
    computer """
    ifconfig = subprocess.check_output(["ifconfig"])
    addresses_list = re.findall("inet \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",ifconfig)
    addresses_list = [re.sub("inet ","",fname ) for fname in addresses_list]
    network_list = [re.sub(".\d{1,3}$",".0/24",fname) for fname in addresses_list]

    # Don't forget to remove localhost
    network_list = [i for i in network_list if not ('127.0.0.' in i )]
    
    return network_list

if __name__ == '__main__':

    app = QtGui.QApplication(sys.argv)
    myapp = MyMainWindow()
    myapp.show()

    myapp.Dialog = QtGui.QDialog(myapp)
    myapp.Dialog.resize(300,230)
    verticalLayout_2 = QtGui.QVBoxLayout(myapp.Dialog)
    verticalLayout = QtGui.QVBoxLayout()
    label = QtGui.QLabel(myapp.Dialog)
    label.setAlignment(QtCore.Qt.AlignCenter)
    verticalLayout.addWidget(label)
    verticalLayout_2.addLayout(verticalLayout)
    myapp.Dialog.setWindowTitle("Wait")
    label.setText("Scanning...")
    myapp.Dialog.setModal(True)
    myapp.Dialog.show()

    QtCore.QObject.connect(myapp.ui.actionRescan, QtCore.SIGNAL("activated()"), myapp.rescan)
    print "Launching threaded scan"
    myapp.scan = ThreadedScan(myapp)
    myapp.scan.start()
    print "Launched threaded scan"
    # modal = ModalThread(myapp)
    # modal.start()

    rpi_image = QtGui.QImage("./rpi.png")
    pixmap = QtGui.QPixmap.fromImage(rpi_image) 
    scene = QtGui.QGraphicsScene()
    scene.setSceneRect(0, 0, 140, 140)
    scene.addPixmap(pixmap)
    myapp.ui.graphicsView.setScene(scene)

    
    sys.exit(app.exec_())

