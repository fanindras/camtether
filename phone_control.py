"""USB camera launch; never unlocks or changes phone security settings."""
import time

def wake_and_start(adb, port, pairing_url):
    adb('reverse', f'tcp:{port}', f'tcp:{port}')
    adb('shell', 'input', 'keyevent', 'KEYCODE_WAKEUP')
    # Unique navigation reloads the page even when Chrome already has it open.
    url=pairing_url.replace('#',f'&launch={time.time_ns()}&start=1#',1)
    adb('shell','am','start','-a','android.intent.action.VIEW','-d',"'"+url+"'",'-p','com.android.chrome')
    return url
