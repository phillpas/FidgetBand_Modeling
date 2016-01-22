import AD5933
import ConnManager
import matplotlib.pyplot as plt
import numpy as np
import time
import csv
import sys
sys.path.append('C:\Users\Phill\Desktop\Tomo\libsvm-3.20\python')
from svmutil import *
from sklearn import svm
from sklearn.datasets import load_svmlight_file
from sklearn import preprocessing
from sklearn.preprocessing import StandardScaler


class TestBed:

    def __init__(self):
        self.ad5933 = AD5933.AD5933("C:\\Program Files (x86)\\Analog Devices\\AD5933\\ADI_CYUSB_USB4.dll")
        boards = self.ad5933.findBoards()[1]
        self.ad5933.connectToBoard(boards)
        self.ad5933.writeStartFreq()
        print "1"
        self.ad5933.writeNumFreqInc()
        print "2"
        self.ad5933.writeFreqInc()
        print "3"
        self.ad5933.writeSettlingTimeCycles()
        self.ad5933.enterStandbyMode()
        self.ad5933.enableExternalOscillator()
        self.ad5933.setDefaultExitationRangeAndPGA()
        self.ad5933.initSensorWithStartFreq()
        print "done"

        self.connManager = ConnManager.ConnManager(8)

        #plotter
        self.fig = plt.figure()
        self.ax1 = self.fig.add_subplot(1,1,1)


    def doFreqSweep(self):
        self.ad5933.writeStartFreq()
        self.ad5933.writeNumFreqInc()
        self.ad5933.writeFreqInc()
        self.ad5933.writeSettlingTimeCycles()
        self.ad5933.enterStandbyMode()
        self.ad5933.enableExternalOscillator()
        self.ad5933.setDefaultExitationRangeAndPGA()
        self.ad5933.initSensorWithStartFreq()
        data = self.ad5933.startFreqSweep()
        impedance = data['impedanceArray'][0]
        self.ad5933.reset()
        return impedance

    def collectGestureSamples(self, label, numSamples):
        rows = []
        for i in xrange(numSamples):
            row = []
            for j in xrange(8-1,-1,-1):
                for k in xrange(j-1,-1,-1):
                    #key = str(j) + str(k)
                    self.connManager.connectElectrodes(j,k)
                    impedance = self.doFreqSweep()
                    row.append(impedance)

            numBasicFeats = len(row)
            for j in xrange(numBasicFeats):
                for k in xrange(j-1):
                    diff = abs(row[j] - row[k])
                    row.append(diff)
                    
            rows.append(row)
                    
            print "Finisehd " + str(i)
        return rows

    def logData_CSV(self,label,data):
        with open(label + '.csv', 'wb') as logFile:
            writer = csv.writer(logFile)
            for row in data:
                rowOut = [label] + row
                writer.writerow(rowOut)

    def logData_SVM(self,label,data):
        with open(label, 'wb') as svmFile:
            for row in data:
                rowOut = label + " "
                for i in xrange(len(row)):
                    rowOut += str(i+1) + ':' + str(row[i]) + ' '
                svmFile.write(rowOut + '\n')
                i+=1
            

    def barTest(self):
        self.ax1.cla()
        self.ax1.set_title('Impedance vs Time')
        self.ax1.set_xlabel('Time')
        self.ax1.set_ylabel('Impedance')

        plt.ion()
        plt.show(False)
        self.ax1.hold(True)
        
        barPlot = self.ax1.bar(np.arange(28),np.zeros(28), 0.7)
        
        self.fig.show()
        self.fig.canvas.draw()
        while True:
            impVals = []
            for i in xrange(8-1,-1,-1):
                for j in xrange(i-1,-1,-1):
                    self.connManager.connectElectrodes(i,j)
                    impedance = self.doFreqSweep()
                    #print impedance
                    impVals.append(impedance)
            
            xmin, xmax, ymin, ymax = [0, 30, 5000, 200000]

            plt.axis([xmin,xmax,ymin,ymax])

            

            for i in xrange(len(impVals)):
                self.ax1.patches[i].set_height(impVals[i])

            self.ax1.draw_artist(self.ax1.patch)
            #self.ax1.draw_artist(line1)
            self.fig.canvas.draw()
            self.fig.canvas.flush_events()


    def classifyTest(self):
        #y, x = svm_read_problem('Default+Up+Down_30')
        #means, stdevs = self.calcMeansStdevs(x)
        #m = svm_train(y[:90], x[:90], '-s 0 -t 1')
        x_train, y_train = load_svmlight_file('Default+Up+Down+Left+Right')
        scaler = preprocessing.MaxAbsScaler()
        x_scaled = scaler.fit_transform(x_train)

        clf = svm.SVC(kernel='poly')
        clf.fit(x_scaled, y_train)

        
        for i in xrange(200): 
            x = [0]*np.shape(x_train)[1]#dict()
            count = 0
            for j in xrange(8-1,-1,-1):
                for k in xrange(j-1,-1,-1):
                    self.connManager.connectElectrodes(j,k)
                    impedance = self.doFreqSweep()
                    x[count] = impedance
                    count+=1

            numBasicFeats = 28
            for j in xrange(numBasicFeats):
                for k in xrange(j-1):
                    diff = abs(x[j] - x[k])
                    x[count] = diff
                    count+=1

            x_s = scaler.transform(x)
            #print x_s
            print clf.predict([x_s])
            #p_labs, p_acc, p_vals = svm_predict([0],[x],m)
            #print p_labs

            '''
            MAPPINGS
            -2: Left
            -1: Down
             0: Default
             1: Up
             2:Right

            '''

    def calcMeansStdevs(self,data,svmFormat):
        features = [[0]*len(svmData[0].values())]
        for i in xrange(len(svmData)):
            if svmFormat:
                row = svmData[i].values()
            else:
                row = svmData[i]
            for j in xrange(len(row)):
                features[j] += row[j]

        means = [0]*len(features)
        stdevs = [0]*len(features)

        for i in xrange(len(features)):
            feat = features[i]
            means[i] = np.mean(feat)
            stdevs[i] = np.std(feat) + 0.00001

        return (means,stdevs)
        
            



tester = TestBed()
#tester.barTest()
tester.classifyTest()
'''gestLabel = input("Gesture: ")
numSamples = input("Num Samples: ")

data = tester.collectGestureSamples(gestLabel,numSamples)
tester.logData_SVM(gestLabel,data)'''

