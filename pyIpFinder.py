#!/usr/bin/python

import sys, getpass, os, subprocess, re
from PyQt4 import QtCore, QtGui
from PyQt4.QtCore import QThread, pyqtSlot, SLOT
from ui_pyipfinder import Ui_MainWindow

import logging
import optparse

LOGGING_LEVELS = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}

# Default handler
ch = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)

# Logging facilities for debug
parser = optparse.OptionParser()
parser.add_option('-l', '--logging-level', help='Logging level')
parser.add_option('-f', '--logging-file', help='Logging file name')
(options, args) = parser.parse_args()
logging_level = LOGGING_LEVELS.get(options.logging_level, logging.NOTSET)


try:
    import nmap
except ImportError:
    p = subprocess.Popen(['python','setup.py','install','--user'],cwd="python-nmap")
    p.wait()
    username = getpass.getuser()
    if username != 'root':
        sys.path.insert(0,'/home/' + username + '/.local/lib/python2.7/site-packages')
    sys.path.insert(1,'/root/.local/lib/python2.7/site-packages')
    try:
        import nmap
    except:
        print "Couldnt detect nmap! Relaunch please!\n"
        exit(1)

try:
    import netifaces
except ImportError:
    p = subprocess.Popen(['python','setup.py','install','--user'],cwd="netifaces")
    p.wait()
    username = getpass.getuser()
    subprocess.call(["chmod", "755","-R", "/home/"+ username + "/.python-eggs"])
    try:
        import netifaces
    except ImportError:
        try:
            username = getpass.getuser()
            if username != 'root':
                sys.path.insert(0,'/home/' + username + '/.local/lib/python2.7/site-packages')
            sys.path.insert(1,'/root/.local/lib/python2.7/site-packages')
            import netifaces
        except:
            print "Couldnt detect netifaces! Relaunch please!\n"
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
        self.connect(self,QtCore.SIGNAL("messageToStatusbar(QString)"),parent.ui.statusbar, QtCore.SLOT("showMessage(QString)"))
        # print "Scan init done"
        self.log = logging.getLogger("Scan Thread")
        self.log.setLevel(logging_level)
        self.log.addHandler(ch)
        

    def run(self):
        self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"), "Scanning...")
        rpi_list = filter_results(scan_list(get_networks()))
        self.log.debug("Received rpi_list : " + str(rpi_list))
        # rpi_list = filter_results(["10.42.0.167"])
        # Let's close the modal window
        if self.parent.Dialog != None:
            self.parent.Dialog.deleteLater()
            self.parent.Dialog = None
        # print "Scan ended!"
        # if len(rpi_list) > 0 :
        #     print "This is the list of IP for Rpi : " + str(rpi_list)
        # else : 
        #     print "The scan returned an empty list"
        
        self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"), "Scanning done")
        if len(rpi_list) == 0:
            self.emit(QtCore.SIGNAL("messageToStatusbar(QString)"), "Scan returned empty list")
        self.emit(QtCore.SIGNAL("updateGuiList"),rpi_list)


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

        # print "updating :D"
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

    scan_log = logging.getLogger("scan_list")
    scan_log.setLevel(logging_level)
    scan_log.addHandler(ch)

    nm = nmap.PortScanner()         # instantiate nmap.PortScanner object
    device_list = []
    for trunk in network:
        scan_log.debug("Inspecting trunk : " + str(trunk))
        nm.scan(hosts=trunk, arguments='-sn')
        for device in nm.all_hosts():
            scan_log.debug("Found device with ip addr : " + str(device))
            device_list.append(device.encode("ascii"))
    scan_log.debug("We return this device list : " + str(device_list))
    return device_list

def filter_results(devicesList):
    """ Filters and grep results """

    filter_log = logging.getLogger("filter_results")
    filter_log.setLevel(logging_level)
    filter_log.addHandler(ch)

    nm = nmap.PortScanner()
    rpi_list =[]

    for ip in devicesList:
        nm.scan(hosts=ip, arguments="-sn")
        filter_log.debug("nm.all_hosts() gives : " + str(nm.all_hosts()))
        # for device in nm.all_hosts():
        filter_log.debug("Inspecting device : "+ str(ip))
        filter_log.debug("nm["+ ip +"] : " + str(nm[ip]))
        if 'mac' in nm[ip]['addresses']:
            vendorName = "".join(nm[ip]['vendor'].values())
            if re.match("Raspberry Pi",vendorName):
                rpi_list.append([ip,nm[ip]['addresses']['mac'].encode("ascii")])
        filter_log.debug("Results rpi_list : " + str(rpi_list))
    return rpi_list



def get_networks():
    """ Scan cards and returns the networks reachable by the
    computer """

    g_ntwlog = logging.getLogger("get_networks")
    g_ntwlog.setLevel(logging_level)
    g_ntwlog.addHandler(ch)

    iflist = netifaces.interfaces()
    # Remove localhost
    iflist = [ i for i in iflist if not ('lo' in i )]
    g_ntwlog.debug("iflist contains : "+str(iflist))
    
    addresses_list = []
    for iface in iflist:
        ad = netifaces.ifaddresses(iface)
        g_ntwlog.debug("ad contains : "+str(ad))
        if netifaces.AF_INET in ad.keys():
            addresses_list.append(ad[netifaces.AF_INET][0]['addr'])
    network_list = [re.sub(".\d{1,3}$",".0/24",fname) for fname in addresses_list]

    g_ntwlog.debug("We return network_list with : "+str(network_list))
    return network_list

if __name__ == '__main__':

    mainlog = logging.getLogger("main")
    mainlog.setLevel(logging_level)
    mainlog.addHandler(ch)

    # logging.basicConfig(level=logging_level, filename=options.logging_file,
            # format='%(asctime)s %(levelname)s: %(message)s',
            # datefmt='%Y-%m-%d %H:%M:%S')

    app = QtGui.QApplication(sys.argv)

    # Adding app icon
    app_icon = QtGui.QIcon()
    app_icon.addFile('windowIcon.png', QtCore.QSize(64,64))
    app.setWindowIcon(app_icon)

    myapp = MyMainWindow()
    myapp.show()
    myapp.setWindowTitle("pyIpFinder")

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
    mainlog.debug("Launching threaded scan")
    myapp.scan = ThreadedScan(myapp)
    myapp.scan.start()
    mainlog.debug("Launched threaded scan")

    rpi_image = QtGui.QImage("./rpi.png")
    pixmap = QtGui.QPixmap.fromImage(rpi_image) 
    scene = QtGui.QGraphicsScene()
    scene.setSceneRect(0, 0, 140, 140)
    scene.addPixmap(pixmap)
    myapp.ui.graphicsView.setScene(scene)

    
    sys.exit(app.exec_())

