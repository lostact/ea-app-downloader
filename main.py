import requests, re, os, sys, pymem, logging, subprocess, json, zipfile, time

# log uncaught exceptions
def log_uncaught_exceptions(exctype, value, tb):
    logging.error("Uncaught exception", exc_info=(exctype, value, tb))
sys.excepthook = log_uncaught_exceptions

STEAMDL_API = "https://api.steamdl.ir/ea"
VERSION = "0.3.0"

MEMORY_PATTERN = br"authorization=Bearer ([a-zA-Z0-9=\._\-]{1,10000})"
DEFAULT_VERSION = "13.128.0.5641"
LAUNCHER_LOG_PATH = os.path.expandvars(r"%LocalAppData%\Electronic Arts\EA Desktop\Logs\EALauncher.log")
APP_LOG_PATH = os.path.expandvars(r"%LocalAppData%\Electronic Arts\EA Desktop\Logs\EADesktop.log")
VERSION_PATTERN = r"\(eax::apps::utils::logAppInfo\)\s+Version:\s+(\d+\.\d+\.\d+[\-\.]\d+)"

def follow(file):
    '''generator function that yields new lines in a file
    '''
    # seek the end of the file
    file.seek(0, os.SEEK_END)
    
    # start infinite loop
    while True:
        # read last line of file
        line = file.read()        # sleep if file hasn't been updated
        if not line:
            time.sleep(1)
            continue

        yield line

class EA_Downloader:
    def __init__(self):
        self._access_token = ""
        self._user_id = ""

    def load_version(self):
        version = DEFAULT_VERSION
        try:
            with open(EA_LOG_PATH, encoding="utf-8") as f:
                for line in f:
                    m = re.search(VERSION_PATTERN, line)
                    if m is None:
                        continue
                    version = m.group(1)
        except:
            pass

        return version.replace("-", ".")

    def get_token(self):
        try:
            ea_app = pymem.Pymem("EADesktop.exe")
        except pymem.exception.ProcessNotFound:
            logging.error("EA app process not found!")
            return

        offset = ea_app.pattern_scan_all(MEMORY_PATTERN)
        if offset is None:
            logging.error("Access token not found, try again!")
            return

        data = ea_app.read_bytes(offset, 10021)
        match = re.match(MEMORY_PATTERN, data)
        if match:
            logging.info("Got token.")
            self._access_token = match.group(1).decode()
            return True

    def get_user_id(self):
        version = self.load_version()

        response = requests.post(
            f"{STEAMDL_API}/get_user_id",
            json = {"version": version, "access_token": self._access_token},
            timeout = 60
        )
        data = response.json()
        if data['success']:
            logging.info("Got user id.")
            self._user_id = data["user_id"]
            return True

    def get_owned_apps(self):
        response = requests.post(
            f"{STEAMDL_API}/get_owned_apps",
            json = {"user_id": self._user_id, "access_token": self._access_token},
            timeout = 60
        )
        data = response.json()
        if data['success']:
            logging.info("Got owned apps.")
            owned_apps = self._owned_apps = data['apps']
            return len(owned_apps)

    def print_apps(self):
        owned_apps = self._owned_apps
        print("\nYour games:")
        for index, app in enumerate(owned_apps):
            choice_number = index + 1
            print(f"{choice_number}. {app['name']}")

    def download_app(self, product_id):
        response = requests.post(
            f"{STEAMDL_API}/get_download_link",
            json = {"user_id": self._user_id, "access_token": self._access_token, "product_id": product_id}
        )
        data = response.json()
        if data['success']:
            download_url = data["download_url"]
            print(f"\nGot download link: {download_url}")
            # webbrowser.open(download_url, new=0, autoraise=False)
        
        if not os.path.isdir("downloads"):
            os.makedirs("downloads")

        match = re.search(r"\/([^?/]+)\?", download_url)
        file_path = "downloads/" + match.group(1)

        download_url_final = download_url.replace("http://", "http://dl.steamdl.ir/steamdl_domain/")
        subprocess.Popen(["wget.exe","-t", "0", "-c", "-O", file_path, download_url_final], shell=True)

        return file_path

    def download_choice(self, app_index):
        app = self._owned_apps[app_index]
        download_app(app['product_id'])


if __name__ == "__main__":
    print(f"EA Downloader by SteamDL.ir - v{VERSION}")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        handlers=[
            logging.FileHandler('downloader.log'),
            # logging.StreamHandler(sys.stdout)
        ]
    )

    ea_downloader = EA_Downloader()
    success = ea_downloader.get_token()
    if success:
        print("Connecting to EA...")
        success = ea_downloader.get_user_id()
        if success:
            print("Waiting for game install...")
            logfile = open(APP_LOG_PATH, "r")
            log_follower = follow(logfile)
            for new_lines in log_follower:
                match = re.search(r"GamesManagerProxy::initiateDownload\)\s+inputParams=\[({[^}]+})", new_lines)
                if match:
                    data = json.loads(match.group(1))
                    game_name = data['slug'].replace("-", " ").title()
                    choice = input(f"Detected {game_name} installation, enter y to start download: ")
                    if choice.strip().lower() == "y":
                        file_path = ea_downloader.download_app(data["offerId"])
                        if file_path:
                            choice = input(f"\nDownloading {game_name} completed, enter y to extract: ")
                            if choice.strip().lower() == "y":
                                install_path = data["installPath"]
                                with zipfile.ZipFile(file_path, 'r') as zip_file:
                                    zip_file.extractall(install_path)
                                print("Extract completed, Enjoy!")
                            # break