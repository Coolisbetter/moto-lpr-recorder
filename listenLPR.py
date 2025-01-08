import socket
import time
import re
import os.path
from datetime import date
from enum import Enum
import mysql.connector
import logging
import threading
import datetime
from dotenv import load_dotenv


class Output(Enum):
    CSV = 1
    MYSQL = 2
logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.INFO,
    datefmt='%Y-%m-%d %H:%M:%S')

def listenLPR(hostname, port, doSaveImg:bool = False, doDumpBin:bool = False, outputType:Output=Output.CSV, mysql_host:str="", mysql_user:str="", mysql_pass:str="", mysql_db:str=""):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.settimeout(60)
            s.connect((hostname, port))
            s.settimeout(None)
        except socket.error:
            logging.error(f"Timed out connecting to {hostname}:{port}")
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
                logging.info(f"Started receiving data stream: {hostname}:{port}")
            #logging.info("Received data of size " + str(len(data)))
            if (len(data) == 4 and data == b'\xBB\x0B\x00\x00'): # Start packet
                #logging.info("Start Packet: "+str(data))
                if (receiving == True): # Save existing data before starting new
                    saveData(hostname=hostname, port=port, binary_data=buffer, doSaveImg=doSaveImg, doDumpBin=doDumpBin, outputType=outputType, mysql_host=mysql_host, mysql_user=mysql_user, mysql_pass=mysql_pass, mysql_db=mysql_db)
                receiving = True
                buffer = data

            if (receiving == True and len(data) > 4):
                buffer = buffer + data
            
            if (receiving == True and len(data) == 4 and data == b'\x08\x04\x00\x00'): # End / heartbeat packet
                #logging.info("End Packet: "+str(data))
                receiving = False
                saveData(hostname=hostname, port=port, binary_data=buffer, doSaveImg=doSaveImg, doDumpBin=doDumpBin, outputType=outputType, mysql_host=mysql_host, mysql_user=mysql_user, mysql_pass=mysql_pass, mysql_db=mysql_db)

def search_bytes(data, pattern):
    """Searches for a byte pattern in binary data."""
    for i in range(len(data) - len(pattern) + 1):
        if data[i:i + len(pattern)] == pattern:
            return i
    return -1

def dump_bin(binary_data, timestamp, plate):
    folder_path = os.path.join('bins',f'{date.today().strftime("%Y-%m-%d")}')
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    with open (os.path.join(folder_path,f'{timestamp}-{plate}.bin'), "wb") as f:
        f.write(binary_data)

def extract_jpg_image(binary_data, timestamp, plate):
    jpg_byte_start = b'\xff\xd8'
    jpg_byte_end = b'\xff\xd9'
    jpg_image = bytearray()

    start = binary_data.find(jpg_byte_start)

    if start == -1:
        logging.error('Could not find JPG start of image marker!')
        return

    end = binary_data.find(jpg_byte_end, start) + len(jpg_byte_end)
    jpg_image += binary_data[start:end]

    #logging.info(f'Size: {end - start} bytes')
    folder_path = os.path.join('images',f'{date.today().strftime("%Y-%m-%d")}')
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    with open(os.path.join(folder_path,f'{timestamp}-{plate}.jpg'), 'wb') as f:
        f.write(jpg_image)

def saveData(hostname, port, binary_data, doSaveImg:bool, doDumpBin:bool, outputType:Output=Output.CSV, mysql_host:str="", mysql_user:str="", mysql_pass:str="", mysql_db:str=""):
    plate = "PARSE_ERROR"
    makerName = "PARSE_ERROR"
    modelName = "PARSE_ERROR"
    colorName = "PARSE_ERROR"
    engineTimeDelay = "PARSE_ERROR"
    timestamp_i = int(time.time())
    timestamp = str(timestamp_i)
    
    # Plate number at start of file
    index = search_bytes(binary_data[0:32], b'=\x00\x00\x00')
    if (index > -1):
        plate = binary_data[index+4:32].decode('utf-8', 'ignore')
        plate = plate.rstrip('\x00')

    # JSON at end of file
    try:
        detail_raw = binary_data[-160:].decode('utf-8', 'ignore')
        #logging.info(detail_raw)

        #logging.info(detail_raw)
        res = re.search(r'"MakerName": "(.*)".*', detail_raw)
        makerName = res.group(1)
        res = re.search(r'"ModelName": "(.*)".*', detail_raw)
        modelName = res.group(1)
        res = re.search(r'"ColorName": "(.*)".*', detail_raw)
        colorName = res.group(1)
        res = re.search(r'"EngineTimeDelay": "(.*)".*', detail_raw)
        engineTimeDelay = res.group(1)
        #logging.info(makerName + "\n" + modelName + "\n" + colorName + "\n" + engineTimeDelay)
    except Exception as e:
        #logging.info(e)
        pass
    
    if (outputType == Output.CSV):
        # Write header if CSV doesn't exist
        if (os.path.isfile('output.csv') == False):
            logging.info('timestamp,plate_number,maker_name,model_name,color_name,engine_time_delay,ip_addr,port')
            with open('output.csv', "a") as fo:
                fo.write('timestamp,plate_number,maker_name,model_name,color_name,engine_time_delay,ip_addr,port\n')
        with open('output.csv', "a") as fo:
            fo.write(timestamp+","+plate+","+makerName+","+modelName+","+colorName+","+engineTimeDelay+','+f"{hostname}:{port}"+'\n')
    
    if (outputType == Output.MYSQL):
        try:
            dbcon = mysql.connector.connect(host=mysql_host, user=mysql_user, password=mysql_pass, database=mysql_db, collation='utf8mb4_general_ci', charset="utf8mb4",)
            dbcur = dbcon.cursor()
            sql = "INSERT INTO `plates`.`plate_table` (`timestamp`, `plate`, `makerName`, `modelName`, `colorName`, `engineTimeDelay`, `ipAddr`, `port`) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
            val = (timestamp_i, plate, makerName, modelName, colorName, engineTimeDelay, hostname, port)
            dbcur.execute(sql, val)
            dbcon.commit()
        except Exception as e:
            logging.info(str(e))

    logging.info(timestamp+","+plate+","+makerName+","+modelName+","+colorName+","+engineTimeDelay+","+hostname+","+str(port))
    
    if (doSaveImg):
        extract_jpg_image(binary_data, timestamp, plate)
    if (doDumpBin):
        dump_bin(binary_data, timestamp, plate)
    
def target(hostname, port, doSaveImg:bool = False, doDumpBin:bool = False, outputType:Output=Output.CSV, mysql_host:str="", mysql_user:str="", mysql_pass:str="", mysql_db:str=""):
    while 1:
        listenLPR(hostname=hostname, port=port, doSaveImg=doSaveImg, doDumpBin=doDumpBin,outputType=outputType,mysql_host=mysql_host,mysql_user=mysql_user,mysql_db=mysql_db,mysql_pass=mysql_pass)

if __name__ == "__main__":
    logging.info("Script started")
    load_dotenv()
    with open('ips.txt', 'r') as f:
        ipArray = f.read().splitlines() 
    doSaveImg=False
    doDumpBin=False
    outputType=Output.MYSQL
    mysql_host=os.getenv('mysql_host')
    mysql_user=os.getenv('mysql_user')
    mysql_db=os.getenv('mysql_db')
    mysql_pass=os.getenv('mysql_pass')

    for ip in ipArray:
        t1 = threading.Thread(target=target, args=(ip, 5001, doSaveImg,doDumpBin,outputType,mysql_host,mysql_user,mysql_pass,mysql_db))
        t2 = threading.Thread(target=target, args=(ip, 5002, doSaveImg,doDumpBin,outputType,mysql_host,mysql_user,mysql_pass,mysql_db))
        t1.start()
        t2.start()