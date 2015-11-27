from ctypes import *
from ctypes.wintypes import *
import math

class AD5933:

    def __init__(self, path_to_dll):
        self.dll = WinDLL(path_to_dll)
        self.handle = None

        #========constants===========
        self.VID = c_uint(0x0456)
        self.PID = c_uint(0xB203)
        self.REQUEST = c_byte(0xDE)
        self.VALUE = c_ushort(0xD)

        self.CLOCK_FREQ = 16000000
        self.START_FREQ = 30000
        self.FREQ_INC = 2
        self.NUM_FREQ_INC = 10

        self.NUM_SETTLING_TIME_CYCLES = 15

        self.GAIN_FACTOR = 0.000000184799 #200K Resistor

        #=======dll functions========
        #Uint  Search_For_Boards (uint VID, uint PID, uint *Num_boards, char *PartPath[]);
        self.dllSearchForBoards = self.dll.Search_For_Boards
        self.dllSearchForBoards.restype = c_uint
        self.dllSearchForBoards.argtypes = [c_uint, c_uint, POINTER(c_uint), POINTER(c_char)]

        #Int Connect(Uint VID, Uint PID, char PartPath, Uint *Handle);
        self.dllConnect = self.dll.Connect
        self.dllConnect.restype = c_int
        self.dllConnect.argtypes = [c_uint, c_uint, c_char, POINTER(c_uint)]

        #Int  Vendor_Request(UInt  Handle, UChar Request, UShort Value, UShort Index, UChar Direction, UShort DataLength, UChar *Buffer[]);
        self.dllRequest = self.dll.Vendor_Request
        self.dllRequest.restype = c_int
        self.argtypes = [c_uint, c_ubyte, c_ushort, c_ushort, c_ubyte, c_ushort, POINTER(c_ubyte)]

        #Int Download_Firmware(Uint Handle, char  pcFilePath[]);
        self.dllDownloadFirmware = self.dll.Download_Firmware
        self.dllDownloadFirmware.restype = c_int
        self.dllDownloadFirmware.argtypes = [c_uint, c_char]

        #Int Disconnect(Uint Handle);
        self.dllDisconnect = self.dll.Disconnect
        self.dllDisconnect.restype = c_int
        self.dllDisconnect.argtypes = [c_uint]


    def findBoards(self):
        numBoards = c_uint()
        partPaths = c_char()
        searchResult = self.dllSearchForBoards(self.VID, self.PID, byref(numBoards), byref(partPaths))
        if searchResult == 0:
            return (numBoards, partPaths)
        else:
            print "No Boards Found!"


    def connectToBoard(self,boardPath):
        handle = c_uint()
        connectResult = self.dllConnect(self.VID, self.PID, boardPath, byref(handle))
        self.handle = handle
        if connectResult == 0:
            return handle
        else:
            print "Error connecting to board!"

    def write(self,handle, register, dataLen):
        if not handle:
            print "No Connection"
            return
        writeResult = self.dllRequest(handle, self.REQUEST, self.VALUE, register, c_ubyte(0), dataLen, c_ubyte(0))
        if not writeResult == 0:
            print "Write Error!"

    def read(self,handle, register, dataLen):
        if not handle:
            print "No Connection"
            return
        data = c_ubyte()
        readResult = self.dllRequest(handle, self.REQUEST, self.VALUE, register, c_ubyte(1), dataLen, byref(data))
        print readResult
        if readResult == 0:
            return data
        else:
            print "Read Error!"


    #=====================
    def readTemp(self,handle):
        print "Reading temp"

        #write to measure temp
        self.write(handle,0x9080,0)

        #now read both bytes
        byte1 = self.read(handle,0x93,1).value
        byte2 = self.read(handle,0x92,1).value

        #convert to celcius
        maxBits = 14
        total = 0
        idx = 0
        while idx < maxBits:
            if idx < 8:
                if byte1 & 1:
                    total = total + pow(2,idx)
                byte1 = byte1 >> 1
            else:
                if byte2 & 1:
                    total = total + pow(2,idx)
                byte2 = byte2 >> 1
            idx += 1
        return total/32.0

    def readStartFreq(self):
        b0 = self.read(self.handle,0x84,1).value
        b1 = self.read(self.handle,0x83,1).value
        b2 = self.read(self.handle,0x82,1).value

        print("b0:" + hex(b0))
        print("b1:" + hex(b1))
        print("b2:" + hex(b2))

    def writeStartFreq(self):
        #midFreq = float(self.START_FREQ + (self.FREQ_INC * self.NUM_FREQ_INC) / 2)
        #freq = int((midFreq / (float(self.CLOCK_FREQ) / 4.0)) * 0xFFFFFF * 8)
        freq = int((float(self.START_FREQ)/ (float(self.CLOCK_FREQ)/ 4)) * pow(2,27))
        print freq

        b0 = freq & 0xFF
        b1A = (freq & 0xFF00) / 256
        b2 = (freq & 0xFF0000) / 65536
        b1B = b1A

        if b1A >= 0xFF:
            b1B &= 0xFF
            msb = (b1A & 0xFF00) / 256
            b2 = (b2 * 256) + msb
            b2 &= 0xFF
        b1 = b1B

        print("b0:" + hex(b0))
        print("b1:" + hex(b1))
        print("b2:" + hex(b2))

        #write bytes to registers
        #values are 'value(1 byte)' + 'address(1 byte)'
        val0 = int(hex(b0) + '84',0)
        val1 = int(hex(b1) + '83',0)
        val2 = int(hex(b2) + '82',0)
        print(val0)
        self.write(self.handle, val0, 0)
        self.write(self.handle, val1, 0)
        self.write(self.handle, val2, 0)

    def readNumFreqInc(self):
        print "Reading numFreqInc"

        b0 = self.read(self.handle,0x89,1).value
        b1 = self.read(self.handle,0x88,1).value

        print("b0:" + hex(b0))
        print("b1:" + hex(b1))

    def writeNumFreqInc(self):
        print "Writing numFreqInc"

        numFreqInc = self.NUM_FREQ_INC
        b0 = numFreqInc & 0xFF
        numFreqInc >>= 8
        b1 = numFreqInc & 0xFF

        val0 = int(hex(b0) + '89',0)
        val1 = int(hex(b1) + '88',0)

        self.write(self.handle, val0, 0)
        self.write(self.handle, val1, 0)

    def readFreqInc(self):
        print "Reading freqInc"

        b0 = self.read(self.handle,0x87,1).value
        b1 = self.read(self.handle,0x86,1).value
        b2 = self.read(self.handle,0x85,1).value

        print("b0:" + hex(b0))
        print("b1:" + hex(b1))
        print("b2:" + hex(b2))

    def writeFreqInc(self):
        print "Writing freqInc"

        freqInc = int((self.FREQ_INC / (float(self.CLOCK_FREQ) / 4)) * pow(2, 27))

        b0 = freqInc & 0xFF
        freqInc >>= 8
        b1 = freqInc & 0xFF
        freqInc >>= 8
        b2 = freqInc & 0xFF

        val0 = int(hex(b0) + '87',0)
        val1 = int(hex(b1) + '86',0)
        val2 = int(hex(b2) + '85',0)

        self.write(self.handle, val0, 0)
        self.write(self.handle, val1, 0)
        self.write(self.handle, val2, 0)

    def readSettlingTimeCycles(self):
        print "Reading settlingTimeCycles"

        cycles = self.read(self.handle,0x8B,1).value
        multiplier = self.read(self.handle,0x8A,1).value

        print "cycles: " + str(cycles)
        print "multiplier: " + str(multiplier)

    def writeSettlingTimeCycles(self):
        print "Writting settlingTimeCycles"

        cyclesVal = int(hex(self.NUM_SETTLING_TIME_CYCLES) + '8B')

        self.write(self.handle, cyclesVal, 0)
        self.write(self.handle, 0x008A, 0);

    def enterStandbyMode(self):
        print "Entering standby mode"
        self.write(self.handle, 0xB080, 0)

    def enableExternalOscillator(self):
        print "Enabling external oscillator"
        self.write(self.handle,0x0881,0)

    def setDefaultExitationRangeAndPGA(self):
        print "Setting output exitation and PGA to default"
        self.write(self.handle,0x0180,0)

    def initSensorWithStartFreq(self):
        print "Initializing sensor with start freq"
        self.write(self.handle,0x1080,0)

    def startFreqSweep(self):
        print "Starting freq sweep!"
        self.write(self.handle,0x2080,0)

        readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x04

        while not readbackStatusRegister == 4 and not self.FREQ_INC == 0:
            readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x02
            if readbackStatusRegister == 2:
                #returned valid data so proceed with sweep
            else:
                #valid data has not been returned. pole status register until valid data is returned
                self.write(self.handle, 0x4080, 0) #repeat sweep point
                while not readbackStatusRegister == 2:
                    readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x02

            realDataUpper = self.read(self.handle,0x94,1)
            realDataLower = self.read(self.handle,0x95,1)
            realData = realDataLower + (realDataUpper * 256)
            #real data is stored in 16bit 2s complement format
            #must be converted to decimal format
            if realData <= 0x7FFF:
                #positive
            else:
                #negative
                realData &= 0x7FFF
                realData -= 65536

            imaginaryDataUpper = self.read(self.handle,0x96,1)
            imaginaryDataLower = self.read(self.handle,0x97,1)
            imaginaryData = imaginaryDataLower + (imaginaryDataUpper * 256)
            #imaginary data is stored in 16bit 2s complement format
            #must be converted to decimal format
            if imaginaryData <= 0x7FFF:
                #positive
            else:
                #negative
                imaginaryData &= 0x7FFF
                imaginaryData -= 65536

            #calculate impedance and phase of data at this freq sweep point
            magnitude = pow((pow(realData,2) + pow(imaginaryData,2)), 0.5)
            sweepPhase = self.phaseSweep(realData,imaginaryData) - calibMidPoint

            impedance = 1.0 / (magnitude * self.GAIN_FACTOR)

    def phaseSweep(self,real,img):
        theta = 0.0
        pSweep = 0
        if real > 0 and img > 0:
            theta = math.atan2(img,real)
            pSweep = (theta * 180) / math.pi
        elif real > 0 and img < 0:
            theta = math.atan2(img,real)
            pSweep = ((theta * 180) / math.pi) + 360
        elif real < 0 and img < 0:
            theta = math.pi + math.atan2(img,real)
            pSweep = (theta * 180) / math.pi
        elif real < 0 and img > 0:
            theta = math.pi + math.atan2(img,real)
            pSweep = (theta * 180) / math.pi
        return pSweep





test = AD5933("C:\\Program Files (x86)\\Analog Devices\\AD5933\\ADI_CYUSB_USB4.dll")

boards = test.findBoards()[1]
handle = test.connectToBoard(boards)

#test.writeStartFreq()
#test.readStartFreq()

#test.writeNumFreqInc()
#test.readNumFreqInc()

#test.writeFreqInc()
#test.readFreqInc()
        
