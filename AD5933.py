from ctypes import *
from ctypes.wintypes import *
import math

class AD5933:
    '''
    This class is used to control the AD5933.
    Currently works by loading the DLL provided with the AD5933 evaluation kit.
    '''
        
    def __init__(self, path_to_dll, logDebug = False):
        self.logDebug = logDebug
        
        self.dll = WinDLL(path_to_dll)
        self.handle = None
        
        #========constants===========
        self.VID = c_uint(0x0456)
        self.PID = c_uint(0xB203)
        self.REQUEST = c_byte(0xDE)
        self.VALUE = c_ushort(0xD)
        
        self.CLOCK_FREQ = 16000000
        self.START_FREQ = 60000
        self.FREQ_INC = 0
        self.NUM_FREQ_INC = 1
        
        self.NUM_SETTLING_TIME_CYCLES = 15
        
        self.GAIN_FACTOR = 0.00000000478049 #4.78049E-9 #200K Resistor
        
        #=========sweep vars=========
        self.curFreqInc = self.NUM_FREQ_INC + 1
        self.curFreq = self.START_FREQ
        
        self.sweepData = dict()
        self.sweepData['impedanceArray'] = []
        self.sweepData['phaseArray'] = []
        self.sweepData['imaginaryDataArray'] = []
        self.sweepData['magnitudeArray'] = []
        self.sweepData['realDataArray'] = []
        self.sweepData['frequencyList'] = []
        
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

    #find and return any connected AD5933 EK boards
    def findBoards(self):
        numBoards = c_uint()
            partPaths = c_char()
            searchResult = self.dllSearchForBoards(self.VID, self.PID, byref(numBoards), byref(partPaths))
            if searchResult == 0:
                return (numBoards, partPaths)
        else:
            self.log("No Boards Found!")

    #connect to the board connected at "boardPath"
    def connectToBoard(self,boardPath):
        handle = c_uint()
            connectResult = self.dllConnect(self.VID, self.PID, boardPath, byref(handle))
            self.handle = handle
            if connectResult == 0:
                self.log("connected to board")
                return handle
        else:
            self.log("Error connecting to board!")

    #write dataLen bytes to register
    def write(self,handle, register, dataLen):
        if not handle:
            self.log("No Connection")
            return
        writeResult = self.dllRequest(handle, self.REQUEST, self.VALUE, register, c_ubyte(0), dataLen, c_ubyte(0))
        if not writeResult == 0:
            self.log("Write Error!")
    
    #read dataLen bytes from register     
    def read(self,handle, register, dataLen):
        if not handle:
            self.log("No Connection")
            return
        data = c_ubyte()
        readResult = self.dllRequest(handle, self.REQUEST, self.VALUE, register, c_ubyte(1), dataLen, byref(data))
        if readResult == 0:
            return data
        else:
            self.log("Read Error!")

    #read current temperature from temperature register and return it (in celcius)
    def readTemp(self):
        self.log("Reading temp")
            
            #write to measure temp
            self.write(self.handle,0x9080,0)
            
            #now read both bytes
            byte1 = self.read(self.handle,0x93,1).value
            byte2 = self.read(self.handle,0x92,1).value
            
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

    #read the start frequency from the start frequency register
    def readStartFreq(self):
        b0 = self.read(self.handle,0x84,1).value
        b1 = self.read(self.handle,0x83,1).value
        b2 = self.read(self.handle,0x82,1).value
    
    #write start frequency set in init to the start frequency register
    def writeStartFreq(self):
        self.log("Writing startFreq")
        freq = int((float(self.START_FREQ)/ (float(self.CLOCK_FREQ)/ 4)) * pow(2,27))
        
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
        
        #write bytes to registers
        #values are 'value(1 byte)' + 'address(1 byte)'
        val0 = int(hex(b0) + '84',0)
        val1 = int(hex(b1) + '83',0)
        val2 = int(hex(b2) + '82',0)
        self.write(self.handle, val0, 0)
        self.write(self.handle, val1, 0)
        self.write(self.handle, val2, 0)

    def readNumFreqInc(self):
        self.log("Reading numFreqInc")
        b0 = self.read(self.handle,0x89,1).value
        b1 = self.read(self.handle,0x88,1).value

    def writeNumFreqInc(self):
        self.log("Writing numFreqInc")
        
        numFreqInc = self.NUM_FREQ_INC
        b0 = numFreqInc & 0xFF
        numFreqInc >>= 8
        b1 = numFreqInc & 0xFF
        
        val0 = int(hex(b0) + '89',0)
        val1 = int(hex(b1) + '88',0)
        
        self.write(self.handle, val0, 0)
        self.write(self.handle, val1, 0)

    def readFreqInc(self):
        self.log("Reading freqInc")
        b0 = self.read(self.handle,0x87,1).value
        b1 = self.read(self.handle,0x86,1).value
        b2 = self.read(self.handle,0x85,1).value
    
    def writeFreqInc(self):
        self.log("Writing freqInc")
        
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
        self.log("Reading settlingTimeCycles")
        cycles = self.read(self.handle,0x8B,1).value
        multiplier = self.read(self.handle,0x8A,1).value
    
    
    def writeSettlingTimeCycles(self):
        self.log("Writting settlingTimeCycles")
        cyclesVal = int(hex(self.NUM_SETTLING_TIME_CYCLES) + '8B',0)
        self.write(self.handle, cyclesVal, 0)
        self.write(self.handle, 0x008A, 0);

    def enterStandbyMode(self):
        self.log("Entering standby mode")
        self.write(self.handle, 0xB080, 0)

    def enterPowerdownMode(self):
        self.log("Entering powerdown mode")
        self.write(self.handle, 0xA080, 0)

    def enableExternalOscillator(self):
        self.log("Enabling external oscillator")
        self.write(self.handle,0x0881,0)

    def setDefaultExitationRangeAndPGA(self):
        self.log("Setting output exitation and PGA to default")
        self.write(self.handle,0x0180,0)

    def initSensorWithStartFreq(self):
        self.log("Initializing sensor with start freq")
        self.write(self.handle,0x1080,0)

    def startFreqSweep(self):
        self.log("Starting freq sweep!")
        self.write(self.handle,0x2080,0)
        
        readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x04
        while not readbackStatusRegister == 4 and not self.curFreqInc == 0:
            readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x02
            if not readbackStatusRegister == 2:
                #valid data has not been returned. pole status register until valid data is returned
                self.write(self.handle, 0x4080, 0) #repeat sweep point
                while not readbackStatusRegister == 2:
                    readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x02
        
            realDataUpper = self.read(self.handle,0x94,1).value
            realDataLower = self.read(self.handle,0x95,1).value
            realData = realDataLower + (realDataUpper * 256)
            #real data is stored in 16bit 2s complement format
            #must be converted to decimal format
            if realData > 0x7FFF:
                #negative
                realData &= 0x7FFF
                realData -= 65536

        imaginaryDataUpper = self.read(self.handle,0x96,1).value
        imaginaryDataLower = self.read(self.handle,0x97,1).value
        imaginaryData = imaginaryDataLower + (imaginaryDataUpper * 256)
        #imaginary data is stored in 16bit 2s complement format
        #must be converted to decimal format
        if imaginaryData > 0x7FFF:
            #negative
            imaginaryData &= 0x7FFF
            imaginaryData -= 65536

        #calculate impedance and phase of data at this freq sweep point
        magnitude = pow((pow(realData,2) + pow(imaginaryData,2)), 0.5)
        calibMidPoint = self.START_FREQ + ((self.FREQ_INC * self.NUM_FREQ_INC) / 2.0)
        sweepPhase = self.phaseSweep(realData,imaginaryData) - calibMidPoint
            
        impedance = 1.0 / (magnitude * self.GAIN_FACTOR)
            
        self.sweepData['impedanceArray'].append(impedance)
        self.sweepData['phaseArray'].append(sweepPhase)
        self.sweepData['imaginaryDataArray'].append(imaginaryData)
        self.sweepData['magnitudeArray'].append(realData)
        self.sweepData['realDataArray'].append(magnitude)
        self.sweepData['frequencyList'].append(self.curFreq)
            
        self.curFreqInc -= 1
        self.curFreq += self.FREQ_INC
            
        readbackStatusRegister = self.read(self.handle, 0x8F, 1).value & 0x04
            
        #update freq point frequency
        self.write(self.handle,0x3080,0)

    #powerdown
    #self.enterPowerdownMode()
    self.log("Sweep Complete")
        return self.sweepData
    
    def reset(self):
        self.curFreqInc = self.NUM_FREQ_INC
        self.sweepData['impedanceArray'] = []
        self.sweepData['phaseArray'] = []
        self.sweepData['imaginaryDataArray'] = []
        self.sweepData['magnitudeArray'] = []
        self.sweepData['realDataArray'] = []
        self.sweepData['frequencyList'] = []
    
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
    
    def log(self, message):
        if self.logDebug:
            print message






