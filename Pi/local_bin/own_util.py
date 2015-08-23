#!/usr/bin/python
import time
import math
import os
import subprocess
import thread
import re
import inspect
import fcntl
import logging

def runShellCommandWait( cmd ):
    return subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True).communicate()[0]

def runShellCommandNowait( cmd ):
    subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)

def getNofConnections():
    stdOutAndErr = runShellCommandWait('netstat | grep -E \'44444.*ESTABLISHED|44445.*ESTABLISHED\' | wc -l')
    return int(stdOutAndErr)

# Below a psutil equivalent of netstat.
# At the moment we do not use this because the output is difficult to parse and probably less stable than netstat.
# The number of connections reported with this function is not the same as with getNofConnections()
# due to different parsing, mostly it is one less.
def getNofConnectionsPsUtil():
    txt = str(psutil.net_connections(kind='tcp'))
    rexp = re.compile('(44444|44445)\)[^\)]*\)[^\)]*ESTABLISHED\'')
    match = rexp.findall(txt)
    return len(match)

def move(direction, speed, delay, doMove):
    if doMove:
        if direction == 'forward':
            dir = 1
        elif direction == 'backward':
            dir = 2
        elif direction == 'left':
            dir = 3
        elif direction == 'right':
            dir = 4
        else:
            dir = 0
        stdOutAndErr = runShellCommandWait('/usr/local/bin/i2c_cmd ' + str(dir) + ' ' + str(speed))
    # Still delay when doMove == False to have similar timing.
    time.sleep(delay)

def moveCamRel(degrees):
    if degrees >= -90 and degrees <= 90:
        if degrees > 0:
            stdOutAndErr = runShellCommandWait('/usr/local/bin/i2c_cmd 10 ' + str(128 + degrees))
        elif degrees < 0:
            stdOutAndErr = runShellCommandWait('/usr/local/bin/i2c_cmd 11 ' + str(128 - degrees))
        # Delay for i2c communication.
        time.sleep(0.1)

def moveCamAbs(degrees):
    if degrees >= 0 and degrees <= 90:
        stdOutAndErr = runShellCommandWait('/usr/local/bin/i2c_cmd 12 ' + str(128 + degrees))
        # Delay for i2c communication.
        time.sleep(0.1)

def getBatteryLevel():
    stdOutAndErr = runShellCommandWait('/usr/local/bin/i2c_cmd 0')
    # Delay for i2c communication.
    time.sleep(0.1)
    # Use DOTALL (so '.' will also match a newline character) because stdOutAndErr can be multiline.
    expr = re.compile('.*Received ([0-9]+).*', re.DOTALL)
    m = expr.match(stdOutAndErr)
    if m != None:
        return m.group(1)
    else:
        return 'unknown'

def getUptime():
    stdOutAndErr = runShellCommandWait('/usr/bin/uptime')
    # Use DOTALL (so '.' will also match a newline character) because stdOutAndErr can be multiline.
    expr = re.compile('.*up ([^,]+).*', re.DOTALL)
    m = expr.match(stdOutAndErr)
    if m != None:
        return m.group(1)
    else:
        return 'unknown'

def uploadAndPurge(filepath, nrOfFilesToKeep):
    # Going to upload the file to Google Drive using the 'drive' utility.
    # To upload into the 'DFRobotUploads' folder, the -p option is used with the id of this folder.
    # When the 'DFRobotUploads' folder is changed, a new id has to be provided.
    # This id can be obtained using 'drive list -t DFRobotUploads'.
    # The uploaded file has a distinctive name to enable finding and removing it again with the 'drive' utility.
    logging.getLogger("MyLog").info('going to call \'drive\' to upload ' + filepath)
    # Run 'drive' as www-data to prevent Google Drive authentication problems.
    stdOutAndErr = runShellCommandWait('sudo -u www-data /usr/local/bin/drive upload -p 0B1WIoyfCgifmMUwwcXNqeDl6U1k -f ' + filepath)
    logging.getLogger("MyLog").info(stdOutAndErr)
    
    # Purge uploads to Google Drive to prevent filling up.
    logging.getLogger("MyLog").info('going to call \'purge_dfrobot_uploads.sh\'')
    # purge_dfrobot_uploads.sh is a bash script which writes to the logfile itself, so do not redirect output.
    # This means we cannot use runShellCommandWait() or runShellCommandNowait().
    p = subprocess.Popen('/usr/local/bin/purge_dfrobot_uploads.sh ' + os.path.basename(filepath) + ' ' + str(nrOfFilesToKeep), shell=True)
    p.wait()

def whatsAppClient():
    global globContinueWhatsApp
    global globMsgIn, globMsgInAvailable, globMsgInAvailableLock
    global globMsgOut, globMsgOutType, globImgOut, globMsgOutAvailable, globMsgOutAvailableLock
    # BE CAREFUL: do not use logging.getLogger("MyLog").info() here, it wil lock up!
    # According to the documentation the Python logging should be thread safe, but still it locks up if used here.
    # Only in case of an exception we log for debugging.
    # Start Yowsup client. Through pipes it communicates with this thread. Default the pipes are buffering
    # which makes that the communication blocks. Therefore the -u option is which will put stdout in unbuffered mode.
    # For stdin we use stdin.flush() below.
    p = subprocess.Popen('python -u /home/pi/yowsup/yowsup-cli demos --yowsup --config /home/pi/yowsup/yowsup_config', stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    # Use file control to make the stdout readline() used below non-blocking.
    # stdout is what comes back from yowsup-cli.
    # This means that if there is no input, readline() will generate an exception.
    # This is what we want otherwise we cannot handle stdout and stdin in the same thread.
    fcntl.fcntl(p.stdout.fileno(), fcntl.F_SETFL, os.O_NONBLOCK)
    p.stdin.write('/L\n')
    # Set presence as available. This will remain available as long as yowsup-cli remains running and
    # WhatsApp will report status as 'online.
    p.stdin.write('/presence available\n')
    
    # Regular expression to filter out message from yowsup-cli output,
    expr = re.compile('.*\[.*whatsapp.net.*\]\\s*(.+)')
    while globContinueWhatsApp:
        # Sleep below to save CPU.
        time.sleep(1)
        
        # Run in try/except to catch and log all errors. Keep this thread running because
        # when this thread ends between an acquire() and release(), it will block other threads.
        try:
            # ***** Handle input *****
            # Below use readline() and not read() because read() will return only after EOF is read which will
            # not happen as the Yowsup client keeps running. readline() instead reads until the end of a line.
            # Using the fcntl above the readline() will not block, but throw an IOError exception
            # when there is no input.
            # Note that when the exception is not caught, this thread will end which will also end yowsup-cli.
            try:
                line = p.stdout.readline()
            except IOError:
                pass
            else: # got line
                m = expr.match(line)
                if m != None:
                    # Keep critical section as short as possible.
                    globMsgInAvailableLock.acquire()
                    globMsgIn = m.group(1)
                    globMsgInAvailable = True
                    globMsgInAvailableLock.release()

            # ***** Handle output *****
            # Keep critical section as short as possible.
            globMsgOutAvailableLock.acquire()
            if globMsgOutAvailable:
                # Copy to keep critical section as short as possible.
                msgOutType = globMsgOutType
                if msgOutType == 'Image':
                    imgOut = globImgOut
                msgOut = globMsgOut
                globMsgOutAvailable = False
                globMsgOutAvailableLock.release()
                
                if msgOutType == 'Image':
                    p.stdin.write('/image send 31613484264' + ' "' + imgOut + '"' + ' "' + msgOut + '"' + '\n')
                else:
                    p.stdin.write('/message send 31613484264 "' + msgOut + '"\n')
                # Flush the stdin pipe otherwise the command will not get through.
                p.stdin.flush()
            else:
                globMsgOutAvailableLock.release()
        except Exception,e:
            logging.getLogger("MyLog").info('whatsAppClient exception: ' + str(e))
                
    # There seems to be no command for exiting yowsup-cli client, so kill process.
    stdOutAndErr = runShellCommandWait('pkill -f yowsup')

def startWhatsAppClient():
    global globContinueWhatsApp
    global globMsgIn, globMsgInAvailable, globMsgInAvailableLock
    global globMsgOut, globMsgOutAvailable, globMsgOutAvailableLock
    logging.getLogger("MyLog").info('going to start whatsAppClient')
    globMsgInAvailableLock = thread.allocate_lock()
    globMsgOutAvailableLock = thread.allocate_lock()
    globContinueWhatsApp = True
    globMsgInAvailable = globMsgOutAvailable = False
    thread.start_new_thread(whatsAppClient, ())
    # The delay below is because if subprocess.Popen() is called right after this it hangs.
    # This is independent of the command called by subprocess.Popen().
    # The reason for his is still unknown.
    # A delay of 0.01 s seems to be sufficient, but we take 0.5 s to be safe.
    time.sleep(0.5)

def stopWhatsAppClient():
    global globContinueWhatsApp
    logging.getLogger("MyLog").info('going to stop whatsAppClient')
    globContinueWhatsApp = False

def sendWhatsAppMsg(msg):
    global globMsgOut, globMsgOutType, globMsgOutAvailable, globMsgOutAvailableLock
    logging.getLogger("MyLog").info('going to send WhatsApp message "' + msg + '"')
    # Keep critical section as short as possible.
    globMsgOutAvailableLock.acquire()
    globMsgOut = msg
    globMsgOutType = 'Text'
    globMsgOutAvailable = True
    globMsgOutAvailableLock.release()

def sendWhatsAppImg(img, caption):
    global globMsgOut, globMsgOutType, globImgOut, globMsgOutAvailable, globMsgOutAvailableLock
    logging.getLogger("MyLog").info('going to send WhatsApp image ' + img + ' with caption "' + caption + '"')
    # Keep critical section as short as possible.
    globMsgOutAvailableLock.acquire()
    globImgOut = img
    globMsgOut = caption
    globMsgOutType = 'Image'
    globMsgOutAvailable = True
    globMsgOutAvailableLock.release()

def receiveWhatsAppMsg():
    global globMsgIn, globMsgInAvailable, globMsgInAvailableLock
    msg = ''
    # Keep critical section as short as possible.
    globMsgInAvailableLock.acquire()
    if globMsgInAvailable:
        msg = globMsgIn
        globMsgInAvailable = False
        globMsgInAvailableLock.release()
        logging.getLogger("MyLog").info('WhatsApp message received: "' + msg + '"')
    else:
        globMsgInAvailableLock.release()
    return msg
