on run
    set supportFolder to (POSIX path of (path to home folder)) & "Library/Application Support/HardwareOne Launcher/"
    set commandBase to "/usr/bin/python3 " & quoted form of (supportFolder & "control.py")
    set helpCommand to "/usr/bin/python3 " & quoted form of (supportFolder & "setup_help.py")
    try
        repeat
            set currentStatus to do shell script commandBase & " status"
            set answer to display dialog currentStatus & return & return & "Start or stop the HardwareOne relay and Terminal host together. Nothing starts automatically at login. Click ? for setup, the device key, or to close." with title "HardwareOne G2 Terminal Bridge" buttons {"?", "Stop both", "Start both"} default button "Start both"
            set selectedAction to button returned of answer
            if selectedAction is "?" then
                set helpText to do shell script helpCommand & " summary"
                set helpChoice to display dialog helpText with title "HardwareOne — Setup help" buttons {"Close", "Setup guide", "Copy device key"} default button "Close" cancel button "Close"
                if button returned of helpChoice is "Copy device key" then
                    set helpResult to do shell script helpCommand & " copy-key"
                    display dialog helpResult with title "HardwareOne — Device key" buttons {"OK"} default button "OK"
                else
                    do shell script helpCommand & " guide"
                end if
            else
                if selectedAction is "Start both" then
                    set outcome to do shell script commandBase & " start"
                else
                    set outcome to do shell script commandBase & " stop"
                end if
                display dialog outcome with title "HardwareOne G2 Terminal Bridge" buttons {"OK"} default button "OK"
                exit repeat
            end if
        end repeat
    on error messageText number errorNumber
        if errorNumber is not -128 then display dialog messageText with title "HardwareOne G2 Terminal Bridge" buttons {"OK"} default button "OK" with icon caution
    end try
end run
