import serial
from time import sleep

class ConnManager:

    def __init__(self,numElectrodes):
        self.numElectrodes = numElectrodes
        self.conn = serial.Serial('COM6',9600)
        self.disconnectElectrodes()

    def electrodeSweep(self):
        for i in xrange(self.numElectrodes-1,-1,-1):
            for j in xrange(i-1,-1,-1):
                writeVal = str(i) + str(j)
                self.conn.write(writeVal)
                #sleep(0.3)

    def connectElectrodes(self,e1,e2):
        val = str(e1) + str(e2)
        self.conn.write(val)

    def disconnectElectrodes(self):
        self.conn.write('88')

    def close(self):
        self.conn.close()


        
