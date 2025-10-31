import os
import cv2
import time
import json
import pyuac
import boto3
import winreg
import psutil
import easyocr
import logging
import datetime
import requests
import threading
import pyautogui
import numpy as np
import subprocess
import pandas as pd
import winreg as reg
from pywinauto.keyboard import send_keys
from pywinauto.application import Application
from PIL import Image, ImageOps, ImageEnhance


AWS_ACCESS_KEY = ''
AWS_SECRET_KEY = ''
AWS_REGION = 'us-west-2'
S3_BUCKET_NAME = 'adwareautomation'
s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY,
                    region_name=AWS_REGION, verify=True)

with open( r'pathfinder_coup.json', 'r', encoding='utf-8') as file:
    config = json.load(file)

# videoFolderPath = r"C:\bundling\bundling_scripts\video"
# stopFilePath1 = r"C:\bundling\bundling_scripts\taskCom"
# stopFilePath = r"C:\bundling\bundling_scripts\taskCom\completed.txt"
# openh264_path = r"C:\bundling\bundling_scripts\openh264_path\openh264-1.8.0-win64.dll"
# log_file_path = r'C:\bundling\bundling_scripts\app.log'
# outpath = r"C:\bundling\bundling_scripts\output"
# click_screenshot = r"C:\bundling\bundling_scripts\click_screenshot"
# screenshotpath = r"C:\bundling\bundling_scripts\screenshots"
# app_path = r"C:\Users\VPT\AppData\Local\Programs\Fiddler\Fiddler.exe"
# filedir = r'C:\bundling\bundling_scripts\networklog'

videoFolderPath = config.get("videoFolderPath")
stopFilePath1 = config.get("stopFilePath1")
stopFilePath = config.get("stopFilePath")
openh264_path = config.get("openh264_path")
log_file_path = config.get("log_file_path")
outpath = config.get("outpath")
outpath_backup = config.get("outpath_backup")
click_screenshot = config.get("click_screenshot")
screenshotpath = config.get("screenshotpath")
app_path = config.get("app_path")
filedir = config.get("filedir")


with open(log_file_path, 'w'):
    pass
# Logger configuration
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
stream_handler.setFormatter(formatter)

logger.addHandler(file_handler)
logger.addHandler(stream_handler)


def clear_folder_content(folder_path):
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                for sub_file in os.listdir(file_path):
                    sub_file_path = os.path.join(file_path, sub_file)
                    os.unlink(sub_file_path)
        except Exception as e:
            print(f"Error: {e}")


# start and stop video
def ScreenRecordStop(output_video_path):
    clear_folder_content(stopFilePath1)
    # Ensure the path to the OpenH264 library is set in the PATH environment variable

    os.environ['PATH'] = os.path.dirname(openh264_path) + ';' + os.environ['PATH']
    screen_width, screen_height = pyautogui.size()
    resized_width = 1280
    resized_height = 720

    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    video_writer = cv2.VideoWriter(output_video_path, fourcc, 40.0, (resized_width, resized_height))

    # Check if the video writer was successfully initialized
    if not video_writer.isOpened():
        raise RuntimeError("Failed to open video writer. Check the codec and file path.")

    start_time = datetime.datetime.now()
    record_duration_minutes = 40  # Change this value to your desired duration
    end_time = time.time() + (record_duration_minutes * 60)

    try:
        while time.time() < end_time:
            if os.path.exists(stopFilePath):
                break
            elapsed_time = datetime.datetime.now() - start_time
            elapsed_time_str = str(elapsed_time).split('.')[0]
            screenshot = pyautogui.screenshot()
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

            # Resize the frame
            frame = cv2.resize(frame, (resized_width, resized_height))

            # Calculate text size to adjust its position
            text_size = cv2.getTextSize(elapsed_time_str, cv2.FONT_HERSHEY_SIMPLEX, 1, 2)[0]
            text_x = resized_width - text_size[0] - 10  # 10 pixels padding from the right
            text_y = 30  # Same vertical position

            # Add elapsed time text at the new position (right side)
            cv2.putText(frame, elapsed_time_str, (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Write the frame to the video
            video_writer.write(frame)

    except KeyboardInterrupt:
        pass

    finally:
        video_writer.release()
        cv2.destroyAllWindows()


# Function to get installed programs from the registry
def get_installed_programs():
    installed_programs = set()
    reg_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"  # 32-bit apps on 64-bit Windows
    ]
    for path in reg_paths:
        try:
            registry_key = reg.OpenKey(reg.HKEY_LOCAL_MACHINE, path)
            for i in range(reg.QueryInfoKey(registry_key)[0]):  # Loop through the subkeys
                try:
                    subkey_name = reg.EnumKey(registry_key, i)
                    subkey = reg.OpenKey(registry_key, subkey_name)
                    program_name, _ = reg.QueryValueEx(subkey, "DisplayName")
                    installed_programs.add(program_name)
                except FileNotFoundError:
                    continue
                except OSError:
                    continue
        except WindowsError:
            continue
    return installed_programs


# Function to get the file extension
def get_file_extension(file_path):
    return os.path.splitext(file_path)[1]


def get_temp_folder_contents():
    temp_path = os.environ.get('TEMP', r'C:\Windows\Temp')
    contents = set()
    for root, dirs, files in os.walk(temp_path):
        for name in dirs + files:
            full_path = os.path.join(root, name)
            contents.add(full_path)
    return contents


def sanitize_filename(url_path):
    # Get the actual filename from the path before the ?
    filename = url_path.split("/")[-1].split("?")[0]
    return filename


def download_exe_file(exe_url, save_dir=r"\exe_downloads"):
    # Create download directory if it doesn't exist
    os.makedirs(save_dir, exist_ok=True)
    filename = sanitize_filename(exe_url)
    # filename = exe_url.split("/")[-1]
    file_path = os.path.join(save_dir, filename)

    # Download the file
    response = requests.get(exe_url, stream=True)
    if response.status_code == 200:
        with open(file_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        full_path = os.path.abspath(file_path)
        print(f"Downloaded to: {full_path}")
        return full_path
    else:
        print(f"Failed to download. Status code: {response.status_code}")
        return None


def disable_proxy():
    try:
        internet_settings = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                           r'SOFTWARE\Microsoft\Windows\CurrentVersion\Internet Settings',
                                           0, winreg.KEY_ALL_ACCESS)
        winreg.SetValueEx(internet_settings, 'ProxyEnable', 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(internet_settings)
        print("Proxy disabled.")
    except Exception as e:
        print(f"Failed to disable proxy: {e}")


# Function to install exe and handle installation process
def install_exe(path):
    before_install = get_process_names()
    result = {"violation": [], "type": "", "tempdata": []}  # Initialize result dict

    try:
        # Get installed programs before installation
        logger.info("Getting list of installed programs before installation...")
        before_installation = get_installed_programs()
        logger.info(f"Programs installed before installation: {len(before_installation)}")
        logger.info("Capturing temp folder contents before installation...")
        temp_before = get_temp_folder_contents()
       
        # Start the installer
        try:
            logger.info(f"Starting installer: {path}")
            app = Application().start(cmd_line=path)
            time.sleep(45)  # Wait for the installer to open
        except:
            logger.info('Something Error in Instraller file')
        # quit(stopFilePath)
        abc = 0
        img_count = 0
        screenshots = []
        while img_count < 4:
            time.sleep(3)
            ss_path = click_screenshot
            x, y, ss = take_screenshot(ss_path)
            if x and y:
                pyautogui.moveTo(x, y, duration=1)
                pyautogui.click()
                screenshots.append(ss)
                time.sleep(180)
                abc = 1
            else:
                break
            # elif not x and not y:
            #     if img_count > 1:
            #         time.sleep(300)
            #         break
            img_count += 1  # Increment the press count
            logger.info(f"click pressed {img_count} times.")
            time.sleep(10)
        if not abc:
            press_count = 0  # Variable to keep track of how many times ENTER is pressed
            while press_count < 10:  # Loop will run 10 times
                time.sleep(10)
                send_keys("{ENTER}")  # Press the ENTER key
                press_count += 1  # Increment the press count
                logger.info(f"ENTER pressed {press_count} times.")
                time.sleep(10)  # Wait for 10 seconds before the next key press
        
        logger.info("10 ENTER presses completed. Exiting loop.")
        time.sleep(1800)
        # Get installed programs after installation
        logger.info("Getting list of installed programs after installation...")
        after_installation = get_installed_programs()
        logger.info(f"Programs installed after installation: {len(after_installation)}")
        logger.info("Capturing temp folder contents after installation...")
        temp_after = get_temp_folder_contents()
        # Compare the two lists
        exetype = get_file_extension(path)
        new_programs = after_installation - before_installation
        # new_temp_files = list(temp_after - temp_before)
        new_temp_files = [f for f in (temp_after - temp_before) if f.endswith('.exe')]

        if new_programs:
            result["violation"] = [{"installedProgram": prog} for prog in list(new_programs)]
            result["type"] = exetype or ''
            logger.info(f"New programs installed: {len(new_programs)}")
            for program in new_programs:
                logger.info(f"- {program}")
        else:
            logger.info("No new programs installed.")
        result["tempdata"] = [{"tempfolder": temp} for temp in new_temp_files]
        logger.info("Installation completed.")
    except Exception as e:
        # Catch any exceptions
        logger.error(f"An unexpected error occurred: {e}")
        result["error"] = str(e)
    finally:
        time.sleep(30)
        app.kill()
        after_install = get_process_names()
        kill_new_processes(before_install, after_install)
        return result, screenshots


def get_process_names():
    return {proc.name(): proc.pid for proc in psutil.process_iter(['pid', 'name'])}


def kill_new_processes(before, after):
    new_processes = {name: pid for name, pid in after.items() if name not in before}
    for name, pid in new_processes.items():
        try:
            logger.info(f"Terminating new process: {name} (PID: {pid})")
            psutil.Process(pid).terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.error(f"Failed to terminate {name}: {e}")


MAX_RETRIES = 3
RETRY_DELAY = 5

def upload_to_s3(video_path, s3, S3_BUCKET_NAME, retries=MAX_RETRIES, delay=RETRY_DELAY):
    s3_object_key = f'aap2appvideos/{os.path.basename(video_path)}'
    for attempt in range(1, retries + 1):
        try:
            s3.upload_file(video_path, S3_BUCKET_NAME, s3_object_key, ExtraArgs={'ContentType': 'video/mp4'})
            s3_url = f'https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_object_key}'
            logger.info(f"Video uploaded to S3: {s3_url}")
            return s3_url
        except Exception as e:
            logger.info(f"Attempt {attempt} failed to upload video to S3: {e}")
            if attempt < retries:
                logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logger.info(f"Failed to upload video to S3 after {retries} attempts.")
                raise


def file_uploader_api(file_path, filetype, tooltype, cl_name):
    filename = os.path.basename(file_path)
    logger.info(f"Filename: {filename}")
    url = "https://reports.vptdigital.com/EvidencesApi/api/SaveFiles/upload"

    payload = {'filename': filename,
               'filetype': filetype,
               'tooltype': tooltype,
               'clientname': cl_name}
    files = [
        ('file', (filename, open(file_path, 'rb'), 'application/octet-stream'))
    ]

    headers = {
        'X-Client-Token': 'vptdigital09082025'
    }

    # response = requests.request("POST", url, data=payload, files=files)
    response = requests.request("POST", url, headers=headers, data=payload, files=files, verify=False)

    logger.info(f"status: {response.status_code}")
    logger.info(response.text)
    logger.info(response.json())
    upload_path = response.json().get('filePath').replace('\\', '/')

    return upload_path


def take_screenshot(path):
    time.sleep(3)
    import datetime

    from PIL import ImageGrab
    # current_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")

    # file_path = rf"{path}\full_screenshot_{current_datetime}.png"
    file_path = rf"{path}\full_screenshot.png"
    ss_path = rf"{screenshotpath}\screenshot_{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
    # screenshot = pyautogui.screenshot()
    # screenshot.save(file_path)
    
    screenshot = ImageGrab.grab()
    screenshot.save(file_path)
    screenshot.save(ss_path)
    
    time.sleep(3)
    x, y = gray_scling_and_finder(file_path)
    return x, y, ss_path


def gray_scling_and_finder(path):
    # Path to your image
    # image_path = rf"{path}\full_screenshot.png"
    image_path = path

    # Create the EasyOCR reader
    reader = easyocr.Reader(['en'])

    # Run OCR
    results = reader.readtext(image_path)

    # Loop through results and extract data
    for result in results:
        bbox, text, conf = result
        # bbox = [top-left, top-right, bottom-right, bottom-left]
        top_left = bbox[0]
        x, y = int(top_left[0]), int(top_left[1])

        print(f"Text: '{text.strip()}', X: {x}, Y: {y}, Confidence: {conf:.2f}")
        click_keywords = json.loads(config.get('clickKey'))
        # if text.lower().strip() in ["next", "ok", "agree", "install", "accept", "finish", "yes", "continue", "accept"]:
        if text.lower().strip() in click_keywords:
            logger.info(f">>> Found button '{text}' at x={x}, y={y}")
            logger.info(f"wlfdgjfdgdfkudgfkgsdf: {x, y}")
            # pyautogui.click(x, y)
            return x, y
    return "", ""


def save_fiddler_log(output_path):
    try:
        pyautogui.hotkey('alt', 'f')  # Open File menu
        time.sleep(1)
        pyautogui.press('s')  # Select Save -> All Sessions
        time.sleep(1)
        pyautogui.press('a')  # Select All Sessions
        time.sleep(1)
        pyautogui.typewrite(output_path)  # Enter the output path
        pyautogui.press('enter')  # Press Enter to save
    except:
        logger.info('Something wrong with Network Log')

 
# Main function to process the input and generate output
def main(input_data):
    listdata = []
    # logger.info(f"dkjbsdjvb,sbdvbkvjvL: {type(input_data)}")
    for installer in input_data.get("exeList"):
        # logger.info(f"12345678765: {input_data.get("taskId")}")
        output_data = {
            "AutomationStart": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "taskId": input_data.get("taskId"),
            "projectId": input_data.get("projectId"),
            "vmId": input_data.get("vmId"),
            "exePath": installer.get("exePath"),
            "exeId": installer.get("exeId", ""),
            "Finding": False,
            "violation": [],
            "tempdata": [],
            "screenshot1": "",
            "screenshot2": "",
            "screenshot3": "",
            "screenshot4": "",
            "videoFilePath": "",
            "networkLogFilePath": "",
            "AutomationEnd": ""
        }
        downloaded_exe_path = download_exe_file(installer.get("exePath"))
        if not os.path.exists(downloaded_exe_path):
            logger.warning(f"Installer not found: {downloaded_exe_path}")
            continue
        logger.info(installer)
        current_datetime = datetime.datetime.now().strftime("%Y%m%d%H%M%S%f")
        app_process = subprocess.Popen(app_path, creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(5)
        videoS3 = os.path.join(videoFolderPath, f"{installer.get('Id')}_{current_datetime}_screen_record3.mp4")
        thread = threading.Thread(target=ScreenRecordStop, args=(videoS3,))
        thread.start()
        
        result, ss_list = install_exe(downloaded_exe_path)
        if result.get('violation'):
            output_data['status'] = True
        output_data["violation"].append(result)
        output_data["tempdata"] = result.get("tempdata", [])
        with open(f'{stopFilePath1}/completed.txt', 'w') as file:
            file.write('Task Completed')
        time.sleep(5)
        # output_data["screenShots"] = ss_list
        # output_data["screenShots"] = {f"screenshot{i+1}": ss for i, ss in enumerate(cc)}
        for i, ss in enumerate(ss_list):
            # if not os.path.exists(ss):
            #     logger.error(f"File does not exist: {ss}")
            #     continue
            try:
                logger.info(f"uploading image to local")
                filtype = 'image'
                tltype = 'adware'
                client_name = 'opera'
                sshot = file_uploader_api(ss, filtype, tltype, client_name)
                logger.info(f"ScreenShot uploaded to local: {ss}")
            except Exception as ie:
                logger.info(f"error while uploading image to local: {ie}")
                try:
                    time.sleep(5)
                    logger.info(f"uploading image to local")
                    filtype = 'image'
                    tltype = 'adware'
                    client_name = 'opera'
                    sshot = file_uploader_api(ss, filtype, tltype, client_name)
                    logger.info(f"ScreenShot uploaded to local: {ss}")
                    # videoupload = upload_to_s3(ss, s3, S3_BUCKET_NAME)
                except Exception as e:
                    logger.info(f"error while uploading video to s3: {e}")
                    sshot = ""
            output_data[f"screenshot{i+1}"] = sshot
            print(f'screenshot{i+1}: {sshot}')
            time.sleep(3)
            
        disable_proxy()
        time.sleep(5)
        """ upload Video S3 start"""
        print('In progress to upload video')
        time.sleep(10)
        print(f'{videoS3}')
        # videoupload = videoS3
        # videoupload = upload_to_s3(videoS3, s3, S3_BUCKET_NAME)
        try:
            logger.info(f"uploading image to local")
            filtype = 'video'
            tltype = 'Adware'
            client_name = 'opera'
            videoupload = file_uploader_api(videoS3, filtype, tltype, client_name)
            logger.info(f"video uploaded to local: {videoS3}")
        except Exception as ie:
            logger.info(f"error while uploading image to local: {ie}")
            try:
                time.sleep(5)
                logger.info(f"uploading image to local")
                filtype = 'video'
                tltype = 'Adware'
                client_name = 'opera'
                videoupload = file_uploader_api(videoS3, filtype, tltype, client_name)
                logger.info(f"video uploaded to local: {videoS3}")
                # videoupload = upload_to_s3(videoS3, s3, S3_BUCKET_NAME)
            except Exception as e:
                logger.info(f"error while uploading video to local: {e}")
                videoupload = ""
        output_data['videoFilePath'] = videoupload
        logger.info(f"upload video to S3: {videoupload}")
            
        current_datetime12 = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        output_pathhh = rf"{filedir}\{current_datetime12}fiddler_log.saz"
        try:
            save_fiddler_log(output_pathhh)
            time.sleep(5)
            
            timeout = 10  # seconds
            waited = 0
            while (not os.path.exists(output_pathhh) or not os.access(output_pathhh, os.R_OK)) and waited < timeout:
                time.sleep(1)
                waited += 1
            try:
                logger.info(f"uploading image to local")
                filtype = 'logs'
                tltype = 'Adware'
                client_name = 'opera'
                output_pathhh = file_uploader_api(output_pathhh, filtype, tltype, client_name)
                logger.info(f"logs uploaded to local: {videoS3}")
            except Exception as ie:
                logger.info(f"error while uploading log to local: {ie}")
                try:
                    time.sleep(5)
                    logger.info(f"uploading image to local")
                    filtype = 'logs'
                    tltype = 'Adware'
                    client_name = 'opera'
                    output_pathhh = file_uploader_api(output_pathhh, filtype, tltype, client_name)
                    logger.info(f"logs uploaded to local: {videoS3}")
                    # videoupload = upload_to_s3(videoS3, s3, S3_BUCKET_NAME)
                except Exception as e:
                    logger.info(f"error while uploading log to local: {e}")
                    output_pathhh = ""
            output_data['networkLogFilePath'] = output_pathhh
        except:
            logger.info(f"Failed to save fiddler log")
        app_process.terminate()
        output_data["AutomationEnd"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        listdata.append(output_data)
    # Now modify violation structure for output
    for item in listdata:
        if item["violation"]:
            # Ensure the violation contains only the installed programs without extra nesting
            item["violation"] = item["violation"][0]["violation"]

    # Convert the modified data back to a JSON string
    modified_json = json.dumps(listdata, indent=4)

    # Print or save the modified JSON
    print(modified_json)
    # try:
    output_file = os.path.join(rf"{outpath}", "depth0.json")
    with open(output_file, "w") as outfile:
        json.dump(listdata, outfile, indent=4)
    time.sleep(6)
    output_file = os.path.join(rf"{outpath_backup}", f"depth0_{datetime.now().strftime('%Y%m%d%H%M%S')}.json")
    with open(output_file, "w") as outfile:
        json.dump(listdata, outfile, indent=4)
    logger.info(f"Output saved to {output_file}")

    with open(fr"{outpath}\completed.txt", "w") as comp:
        comp.write("task completed")

    # except Exception as e:
    #     logger.error(f"Error saving output file: {e}")


# Run the script as administrator if needed
def run_as_admin():
    if not pyuac.isUserAdmin():
        pyuac.runAsAdmin()  # Request admin privileges
    else:
        input_file = 'conf.json'
        """C:\bundling\bundling_scripts\conf\conf.json"""
        try:
            with open(input_file, 'r') as infile:
                input_data = json.load(infile)
                main(input_data)  # Run the main function with input data
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()  # Get the full traceback (including line number)
            logging.error(f"Error occurred: {e}\n{error_trace}")
            logger.error(f"Failed to read input file: {e}")
            print("Failed to read input file.")


if __name__ == "__main__":
    run_as_admin()



