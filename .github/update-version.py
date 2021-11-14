#!/usr/bin/python3

from collections import OrderedDict
import fileinput
import json
from ruamel import yaml
import urllib.parse
import urllib.request

###################################################################################################
# Variables
###################################################################################################

github_api = "https://api.github.com/repos/"
docker_api = "https://registry.hub.docker.com/api/content/v1/repositories/public/"
quay_api = "https://quay.io/api/v1/repository/"

file = ".github/workflows/build-container-image.yml"
containerfile = "Containerfile"


###################################################################################################
# Functions
###################################################################################################

def get_schema_is_valid(tag_name, schema):
    if schema == "NUMBER.NUMBER.NUMBER":
        try:
            helper = tag_name.split(".")
        except ValueError:
            return False

        if len(helper) != 3:
            return False

        if helper[0].isdigit() and helper[1].isdigit() and helper[2].isdigit():
            return True

    if schema == "NUMBER.NUMBER":
        try:
            helper = tag_name.split(".")
        except ValueError:
            return False

        if len(helper) != 2:
            return False

        if helper[0].isdigit() and helper[1].isdigit():
            return True

    if schema == "NUMBER.NUMBER-alpine":
        try:
            helper1 = tag_name.split(".")
            helper2 = helper1[1].split("-")
        except IndexError:
            return False
        except ValueError:
            return False

        # NOTE: some versions look like this: 1.19.9-alpine. This filters them away
        if len(helper1) != 2 or len(helper2) != 2:
            return False

        if helper1[0].isdigit() and helper2[0].isdigit() and helper2[1] == "alpine":
            return True

    if schema == "NUMBER.NUMBER.NUMBER-alpine":
        try:
            helper1 = tag_name.split("-")
            helper2 = helper1[0].split(".")
        except IndexError:
            return False
        except ValueError:
            return False

        # NOTE: ignore alpine-perl tags
        if len(helper1) != 2:
            return False

        if len(helper2) != 3:
            return False

        try:
            if helper2[0].isdigit() and helper2[1].isdigit() and helper2[2].isdigit() and helper1[1] == "alpine":
                return True
        except IndexError:
            return False

    if schema == "NUMBER-alpine":
        try:
            helper = tag_name.split("-")
        except ValueError:
            return False

        if len(helper) != 2:
            return False

        if helper[0].isdigit() and helper[1] == "alpine":
            return True

    if schema == "vNUMBER.NUMBER.NUMBER":
        if tag_name.startswith("v"):
            try:
                helper1 = tag_name[1:]
                helper2 = helper1.split(".")
            except ValueError:
                return False

            if len(helper2) != 3:
                return False

            if helper2[0].isdigit() and helper2[1].isdigit() and helper2[2].isdigit():
                return True

    return False


def get_api_generic_latest_tag(api, owner, repo, key):
    with urllib.request.urlopen(api + owner + "/" + repo + "/" + key) as url:
        return json.loads(url.read().decode())


def get_api_github_latest_tag(owner, repo, schema):
    result = get_api_generic_latest_tag(github_api, owner, repo, "tags")
    for entry in result:
        if get_schema_is_valid(entry['name'], schema):
            return entry['name']


def get_api_docker_latest_tag(owner, repo, schema):
    result = get_api_generic_latest_tag(docker_api, owner, repo, "tags?page_size=100")
    for entry in result['results']:
        # NOTE: This is a really weird workaround to get rid of all old versions < 10.6.
        if repo == "mariadb" and not entry['name'].startswith('10.6'):
            continue

        if get_schema_is_valid(entry['name'], schema):
            return entry['name']


def get_api_quay_latest_tag(owner, repo, schema):
    result = get_api_generic_latest_tag(quay_api, owner, repo, "tag/")
    for entry in result['tags']:
        if get_schema_is_valid(entry['name'], schema) and "expiration" not in entry:
            return entry['name']


###################################################################################################

def get_version():
    version = get_api_docker_latest_tag("netboxcommunity", "netbox", "vNUMBER.NUMBER.NUMBER")
    return f"{version}-ldap"


def set_version():
    # load
    with open(file) as fp:
        try:
            data = OrderedDict()
            data = yaml.safe_load(fp)
        except yaml.YAMLError as e:
            print(e)

    # modify
    version = get_version()
    data['jobs']['build-container-image']['strategy']['matrix']['version'][0]

    # save
    with open(file, 'w') as fp:
        try:
            yaml.dump(data, fp, Dumper=yaml.RoundTripDumper, default_flow_style=False, explicit_start=True)
        except yaml.YAMLError as exc:
            print(e)

    for line in fileinput.input(containerfile, inplace=True):
        if line.startswith("ARG VERSION="):
            print(f"ARG VERSION={version}", end='\n')
        else:
            print(line, end='')


###################################################################################################
# Main
###################################################################################################

set_version()
