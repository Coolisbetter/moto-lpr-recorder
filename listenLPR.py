import socket
import time
import re
import os.path
from datetime import date

def listenLPR(hostname, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(10)
            s.connect((hostname, port))
            s.settimeout(None)
        except socket.error:
            print(f"Timed out connecting to {hostname}:{port}")
            return
        buffer = None
        receiving = False
        firstData = False
        while 1:
            data = s.recv(60000) # 60KB buffer
            if (len(data) == 0):
                break
            if (firstData == False):
                firstData = True
                print("Started receiving data stream")
            #print("Received data of size " + str(len(data)))
            if (len(data) == 4 and data == b'\xBB\x0B\x00\x00'): # Start packet
                #print("Start Packet: "+str(data))
                if (receiving == True): # Save existing data before starting new
                    saveData(f"{hostname}:{port}", buffer)
                receiving = True
                buffer = data

            if (receiving == True and len(data) > 4):
                buffer = buffer + data
            
            if (receiving == True and len(data) == 4 and data == b'\x08\x04\x00\x00'): # End / heartbeat packet
                #print("End Packet: "+str(data))
                receiving = False
                saveData(f"{hostname}:{port}", buffer)

def search_bytes(data, pattern):
    """Searches for a byte pattern in binary data."""
    for i in range(len(data) - len(pattern) + 1):
        if data[i:i + len(pattern)] == pattern:
            return i
    return -1

def extract_jpg_image(binary_data, timestamp, plate):
    jpg_byte_start = b'\xff\xd8'
    jpg_byte_end = b'\xff\xd9'
    jpg_image = bytearray()

    start = binary_data.find(jpg_byte_start)

    if start == -1:
        print('Could not find JPG start of image marker!')
        return

    end = binary_data.find(jpg_byte_end, start) + len(jpg_byte_end)
    jpg_image += binary_data[start:end]

    #print(f'Size: {end - start} bytes')
    folder_path = os.path.join('images',f'{date.today().strftime("%Y-%m-%d")}')
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    with open(os.path.join(folder_path,f'{timestamp}-{plate}.jpg'), 'wb') as f:
        f.write(jpg_image)

def saveData(hostname, binary_data):
    plate = "PARSE_ERROR"
    makerName = "PARSE_ERROR"
    modelName = "PARSE_ERROR"
    colorName = "PARSE_ERROR"
    engineTimeDelay = "PARSE_ERROR"
    timestamp = str(int(time.time()))
    
    # Plate number at start of file
    index = search_bytes(binary_data[0:32], b'=\x00\x00\x00')
    if (index > -1):
        plate = binary_data[index+4:32].decode('utf-8')
        plate = plate.rstrip('\x00')

    # JSON at end of file
    try:
        detail_raw = binary_data[-160:].decode('utf-8', 'ignore')
        #print(detail_raw)

        #print(detail_raw)
        res = re.search(r'"MakerName": "(.*)".*', detail_raw)
        makerName = res.group(1)
        res = re.search(r'"ModelName": "(.*)".*', detail_raw)
        modelName = res.group(1)
        res = re.search(r'"ColorName": "(.*)".*', detail_raw)
        colorName = res.group(1)
        res = re.search(r'"EngineTimeDelay": "(.*)".*', detail_raw)
        engineTimeDelay = res.group(1)
        #print(makerName + "\n" + modelName + "\n" + colorName + "\n" + engineTimeDelay)
    except Exception as e:
        #print(e)
        pass
    
    print(timestamp+","+plate+","+makerName+","+modelName+","+colorName+","+engineTimeDelay)
    with open('output.csv', "a") as fo:
        fo.write(timestamp+","+plate+","+makerName+","+modelName+","+colorName+","+engineTimeDelay+','+hostname+'\n')
    extract_jpg_image(binary_data, timestamp, plate)
    # with open (timestamp+".bin", "wb") as f:
    #     f.write(binary_data)

if __name__ == "__main__":
    print("Script started")
    # Write header if CSV doesn't exist
    if (os.path.isfile('output.csv') == False):
        with open('output.csv', "a") as fo:
            fo.write('timestamp,plate_number,maker_name,model_name,color_name,engine_time_delay,ip_addr\n')
        print('timestamp,plate_number,maker_name,model_name,color_name,engine_time_delay,ip_addr')
    
    #listenLPR("152.86.30.137", 5001)
    listenLPR("166.157.142.221", 5002)
