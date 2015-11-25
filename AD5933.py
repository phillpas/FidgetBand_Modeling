from ctypes import *
from ctypes.wintypes import *

class AD5933:

    def __init__(self, path_to_dll):
        self.dll = WinDLL(path_to_dll)
        self.VID = c_uint(0x0456)
        self.PID = c_uint(0xB203)

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
        if connectResult == 0:
            return handle
        else:
            print "Error connecting to board!"

    def write(self,handle, request, value, register, dataLen):
        writeResult = self.dllRequest(handle, request, value, register, c_ubyte(0), dataLen, c_ubyte(0))
        print writeResult
        if not writeResult == 0:
            print "Write Error!"

    def read(self,handle, request, value, register, dataLen):
        data = c_ubyte()
        readResult = self.dllRequest(handle, request, value, register, c_ubyte(1), dataLen, byref(data))
        print readResult
        if readResult == 0:
            return data
        else:
            print "Read Error!"


    #=====================
    def readTemp(self,handle):
        request = c_byte(0xDE)
        value = c_ushort(0xD)

        #write to measure temp
        self.write(handle,request,value,0x9080,0)

        #now read both bytes
        byte1 = self.read(handle,request,value,0x93,1).value
        byte2 = self.read(handle,request,value,0x92,1).value

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

        

test = AD5933("C:\\Program Files (x86)\\Analog Devices\\AD5933\\ADI_CYUSB_USB4.dll")

boards = test.findBoards()[1]
handle = test.connectToBoard(boards)

temp = test.readTemp(handle)
print(temp)
        
        
        
