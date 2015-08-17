#!/bin/bash
# CGI script called from an html form action. The stdout generated by this script is sent back to the browser,
# therefore it is important to capture all stdout output which must not be returned to the html.
# This can be done using '> /dev/null 2>&1' or writing to a logfile.

function handle_command {
    prompt=$(basename $0)
    # Reset the log file to zero length if the size gets too large.
    if [ $(stat -c %s /home/pi/log/dfrobot_log.txt) -gt 1000000 ]
    then
        echo -e "***** $(date), $prompt: START LOG  *****" > /home/pi/log/dfrobot_log.txt
    else
        echo -e "\n***** $(date), $prompt: START LOG  *****" >> /home/pi/log/dfrobot_log.txt
    fi

    if [ "${1}" == "start-stream-hq" ]
    then
        echo "***** $(date), $prompt: 'start-stream-hq' command received" >> /home/pi/log/dfrobot_log.txt
        # Start capturing video stream. Stop previous capture first if any.
        killall mjpg_streamer > /dev/null 2>&1
        sleep 0.5
        LD_LIBRARY_PATH=/opt/mjpg-streamer/mjpg-streamer-experimental/ /opt/mjpg-streamer/mjpg-streamer-experimental/mjpg_streamer -i "input_raspicam.so -vf -hf -fps 10 -q 10 -x 800 -y 600" -o "output_http.so -p 44445 -w /opt/mjpg-streamer/mjpg-streamer-experimental/www" > /dev/null 2>&1
    elif [ "${1}" == "start-stream-lq" ]
    then
        echo "***** $(date), $prompt: 'start-stream-lq' command received" >> /home/pi/log/dfrobot_log.txt
        # Start low quality video stream. Stop previous stream first if any.
        killall mjpg_streamer > /dev/null 2>&1
        sleep 0.5
        LD_LIBRARY_PATH=/opt/mjpg-streamer/mjpg-streamer-experimental/ /opt/mjpg-streamer/mjpg-streamer-experimental/mjpg_streamer -i "input_raspicam.so -vf -hf -fps 2 -q 10 -x 800 -y 600" -o "output_http.so -p 44445 -w /opt/mjpg-streamer/mjpg-streamer-experimental/www" > /dev/null 2>&1
    elif [ "${1}" == "stop-stream" ]
    then
        echo "***** $(date), $prompt: 'stop-stream' command received" >> /home/pi/log/dfrobot_log.txt
        killall mjpg_streamer > /dev/null 2>&1
    elif [ "${1}" == "capture-start" ]
    then
        echo "***** $(date), $prompt: 'capture-start' command received" >> /home/pi/log/dfrobot_log.txt
        # Start capture video from http stream, with timeout of 60 seconds.
        echo "***** $(date), $prompt: going to capture http MJPEG stream" >> /home/pi/log/dfrobot_log.txt
        cvlc http://localhost:44445/?action=stream --sout '#standard{mux=ts,dst=/home/pi/DFRobotUploads/dfrobot_pivid_man.mp4,access=file}' --run-time=60 vlc://quit > /dev/null 2>&1 &
    elif [ "${1}" == "capture-stop" ]
    then
        echo "***** $(date), $prompt: 'capture-stop' command received" >> /home/pi/log/dfrobot_log.txt
        # Stop the video capture, upload to Google drive and purge the uploaded files on Google Drive.
        # These commands have to be execuded in sequence. Because we want the webpage and therefore this script to
        # be responsive we execute all these tasks in sequence in one background task with:
        # ( command1; command 2; command 3) > /dev/null 2>&1 &
        # The extra '> /dev/null 2>&1' is needed to capture the output of the 'moving to background' symbol '&'.
        # This because the stdout of this script is returned to the browser and is strictly defined.
        ( \
        killall vlc > /dev/null 2>&1 ;\
        # Going to upload the file to Google Drive using the 'drive' utility.
        # Run 'drive' as www-data to prevent Google Drive authentication problems.
        # To upload into the 'DFRobotUploads' folder, the -p option is used with the id of this folder.
        # When the 'DFRobotUploads' folder is changed, a new id has to be provided.
        # This id can be obtained using 'drive list -t DFRobotUploads'.
        # The uploaded file has a distinctive name to enable finding and removing it again with the 'drive' utility.
        echo "***** $(date), $prompt: going to call 'drive' to upload videofile" >> /home/pi/log/dfrobot_log.txt ;\
        sudo -u www-data drive upload -p 0B1WIoyfCgifmMUwwcXNqeDl6U1k -f /home/pi/DFRobotUploads/dfrobot_pivid_man.mp4 >> /home/pi/log/dfrobot_log.txt 2>&1 ;\
        echo "***** $(date), $prompt: going to call 'drive' to upload logfile" >> /home/pi/log/dfrobot_log.txt ;\
        sudo -u www-data drive upload -p 0B1WIoyfCgifmMUwwcXNqeDl6U1k -f /home/pi/log/dfrobot_log.txt >> /home/pi/log/dfrobot_log.txt 2>&1 ;\
        # Going to purge previously uploaded files to prevent filling up Google Drive.
        echo "***** $(date), $prompt: going to call 'purge_dfrobot_uploads.sh'" >> /home/pi/log/dfrobot_log.txt ;\
        purge_dfrobot_uploads.sh dfrobot_pivid_man.mp4 3 ;\
        purge_dfrobot_uploads.sh dfrobot_log.txt 1 ;\
    ) > /dev/null 2>&1 &
    elif [ "${1}" == "forward" ]
    then
        echo "***** $(date), $prompt: 'forward' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 1 ${2} > /dev/null 2>&1
    elif [ "${1}" == "backward" ]
    then
        echo "***** $(date), $prompt: 'backward' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 2 ${2} > /dev/null 2>&1
    elif [ "${1}" == "left" ]
    then
        echo "***** $(date), $prompt: 'left' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 3 ${2} > /dev/null 2>&1
    elif [ "${1}" == "right" ]
    then
        echo "***** $(date), $prompt: 'right' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 4 ${2} > /dev/null 2>&1
    elif [ "${1}" == "cam-up" ]
    then
        echo "***** $(date), $prompt: 'cam-up' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 10 ${2} > /dev/null 2>&1
    elif [ "${1}" == "cam-down" ]
    then
        echo "***** $(date), $prompt: 'cam-down' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 11 ${2} > /dev/null 2>&1
    elif [ "${1}" == "light-on" ]
    then
        echo "***** $(date), $prompt: 'light-on' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 20 > /dev/null 2>&1
    elif [ "${1}" == "light-off" ]
    then
        echo "***** $(date), $prompt: 'light-off' command received" >> /home/pi/log/dfrobot_log.txt
        i2c_cmd 21 > /dev/null 2>&1
    elif [ "${1}" == "home-start" ]
    then
        echo "***** $(date), $prompt: 'home-start' command received" >> /home/pi/log/dfrobot_log.txt
        /usr/local/bin/run_dfrobot.py -homerun > /dev/null 2>&1
    elif [ "${1}" == "home-stop" ]
    then
        echo "***** $(date), $prompt: 'home-stop' command received" >> /home/pi/log/dfrobot_log.txt
        # The name of the process to be killed is 'python' which is too general.
        # Therefore use pkill -f to kill only the python process running the run_dfrobot.py script.
        # With the -f option a pattern is matched against the full command line.
        # Note that we only kill the python process started by this user (www-data).
        pkill -f run_dfrobot.py > /dev/null 2>&1
    elif [ "${1}" == "status" ]
    then
        echo "***** $(date), $prompt: 'status' command received" >> /home/pi/log/dfrobot_log.txt
        do_update=true
    fi
}

# Set below value to true to have an html frame refresh for every form action (like a button click).
# On most devices this is not needed, except for an iPad.
do_update=false

# CGI POST method handling code below taken from http://tuxx-home.at/cmt.php?article=/2005/06/17/T09_07_39/index.html
if [ "$REQUEST_METHOD" = "POST" ]; then
    read POST_STRING

    # replace all escaped percent signs with a single percent sign
    POST_STRING=$(echo $POST_STRING | sed 's/%%/%/g')

    # replace all ampersands with spaces for easier handling later
    POST_STRING=$(echo $POST_STRING | sed 's/&/ /g')

    # Now $POST_STRING contains 'cmd=<value>' where 'cmd' and '<value>' correspond with the
    # 'name' and 'value' attribute of the button pressed in the client side html file.
    # Filter out <value> and store it in $COMMAND.
    COMMAND_PLUS_PARAMETER="$(echo $POST_STRING | sed -n 's/^.*cmd=\([^ ]*\).*$/\1/p')"
    COMMAND="$(echo $COMMAND_PLUS_PARAMETER | sed -n 's/\([^.]*\).*$/\1/p')"
    PARAMETER="$(echo $COMMAND_PLUS_PARAMETER | sed -n 's/[^.]*\.\(.*$\)/\1/p')"

    # Call command handler.
    handle_command $COMMAND $PARAMETER
fi

# Now we must return a valid HTTP header to the client, otherwise an "Internal Server Error" will be generated.
# Below are three options:
# 1. Use HTTP header "Content-type" and then add an HTML meta 'refresh' to force a refresh of the page.
#    This has the disadvantage that the refresh is visible, dependent of the browser.
# 2. Use HTTP header "Location" and point it to the original page so this will also refresh the page.
#    This has the disadvantage that the refresh is visible, dependent of the browser.
# 3. Use the HTTP header "Status" and return code 304, which means "Not Modified".
#    This will prevent most browsers from reloading the page and is the preferred method.
#    The disadvantage that the new html content like the robot status is not updated.
# The best option might be to use option 3 when no status update is needed else option 2.

#echo -e "Location: ../index1.html\n"

if [ $do_update = false ]
then
    echo -e "Status:304\n"
else
    # Get actual status so it can be sent to the web client.
    wifistatus=/sbin/iwconfig
    status="<br>$($wifistatus | sed -n 's/^.*ESSID:"\([^"]*\).*$/\1/p') level = $($wifistatus | sed -n 's/^.*level=\([^ ]*\).*$/\1/p') dBm<br>uptime = $(/usr/bin/uptime | sed -n 's/.*up \([^,]*\).*/\1/p')<br>battery = $(i2c_cmd 0 | sed -n 's/^.*Received \([^ ]*\).*$/\1/p') (154 = 6V)"

    # Send 'index1.html' to the web client, after replacing the 'feedbackstring' with the actual status.
    echo -e "Content-type: text/html\n"
    while read line
    do
        # Replace 'feedbackstring' in original string with the actual status.
        echo -e ${line/feedbackstring/$status}
    done < ${1}
fi


