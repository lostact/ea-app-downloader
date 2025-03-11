import requests, re, os, sys, pymem, logging

# log uncaught exceptions
def log_uncaught_exceptions(exctype, value, tb):
    logging.error("Uncaught exception", exc_info=(exctype, value, tb))
sys.excepthook = log_uncaught_exceptions

STEAMDL_API = "https://api.steamdl.ir/ea"
VERSION = "0.2.1"

MEMORY_PATTERN = br"authorization=Bearer ([a-zA-Z0-9=\._\-]{1,10000})"
DEFAULT_VERSION = "13.128.0.5641"
EA_LOG_PATH = r"%LocalAppData%\Electronic Arts\EA Desktop\Logs\EALauncher.log"
VERSION_PATTERN = r"\(eax::apps::utils::logAppInfo\)\s+Version:\s+(\d+\.\d+\.\d+[\-\.]\d+)"

class EA_Downloader:
    def __init__(self):
        self._access_token = ""
        self._user_id = ""

    def load_version(self):
        version = DEFAULT_VERSION
        try:
            with open(os.path.expandvars(EA_LOG_PATH), encoding="utf-8") as f:
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

    def download_app(self, app_index):
        app = self._owned_apps[app_index]
        response = requests.post(
            f"{STEAMDL_API}/get_download_link",
            json = {"user_id": self._user_id, "access_token": self._access_token, "product_id": app['product_id']}
        )
        data = response.json()
        if data['success']:
            download_url = data["download_url"]
            print(f"\nGot download link: {download_url}")
            # webbrowser.open(download_url, new=0, autoraise=False)
            
            from pypdl import Pypdl

            if not os.path.exists("downloads"):
                os.makedirs("downloads")

            dl = Pypdl(allow_reuse=False, max_concurrent=4)
            result = dl.start(
                url=download_url,
                file_path="downloads",
                multisegment=True,
                segments=2000,
                retries=5,
                display=True,
                clear_terminal=False,
                block=True
            )
            return result


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
            print("Getting games list...")
            app_count = ea_downloader.get_owned_apps()
            if app_count > 0:
                exit = False
                while not exit:
                    ea_downloader.print_apps()
                    choice = input("\nEnter a number to download or 0 to exit. ")
                    if not choice.isdigit():
                        print("Invalid choice.")
                        continue
                    choice_number = int(choice)
                    if choice_number > app_count:
                        print("Invalid number.")
                        continue
                    if choice_number != 0:
                        ea_downloader.download_app(choice_number - 1)
                        if result:
                            print("File downloaded to downloads folder.")
                    else:
                        exit = True

    # input("Press enter to exit.")