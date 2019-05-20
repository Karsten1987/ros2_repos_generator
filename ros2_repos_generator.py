#!/usr/bin/env python

"""ROS2 repos file generator.

script for generating ros2 repository files
in the form of gist files which can be used
to run run for external PR contributions.

using gist rest api as descripted here
https://developer.github.com/v3/gists/#create-a-gist
"""

import argparse
import getpass
import json
import os

import requests
from requests.auth import HTTPBasicAuth

api_url = 'https://api.github.com'
default_ros2_repos = 'https://raw.githubusercontent.com/' \
    'ros2/ros2/master/ros2.repos'


def _get_username_and_password():
    username = input('github username: ')
    password = getpass.getpass('password: ')
    return username, password


def _create_gist(repos_content, token_param, auth, file_name):
    gist_file_name = file_name
    jGist = json.dumps({
        'description': 'external contribution repos file',
        'public': True,
        'files': {
            gist_file_name: {
                'content': repos_content
            }
        }})

    response = requests.post(
        api_url + '/gists' + token_param,
        auth=auth,
        verify=True,
        data=jGist)
    response.raise_for_status()

    gist_details = json.loads(response.content.decode())
    return gist_details['files'][gist_file_name]['raw_url']


def _modify_master_repos(repos, pkg, url, branch):
    lines = repos.split('\n')

    pkg_found = False
    for idx, val in enumerate(lines):
        if pkg + ':' == val.lstrip():
            pkg_found = True
            lines[idx + 2] = '{indent}url: {url}'.format(
                indent=4 * ' ', url=url)
            lines[idx + 3] = '{indent}version: {branch}'.format(
                indent=4 * ' ', branch=branch)
            print('new entry for package:', val.lstrip())
            [print(lines[idx + i] for i in range(4))]
            print(lines[idx + 1])
            print(lines[idx + 2])
            print(lines[idx + 3])
            break

    if not pkg_found:
        new_entry = []
        new_entry.append('{indent}{pkg}:'.format(
            indent=2 * ' ', pkg=pkg))
        new_entry.append('{indent}type: git'.format(
            indent=4 * ' '))
        new_entry.append('{indent}url: {url}'.format(
            indent=4 * ' ', url=url))
        new_entry.append('{indent}version: {branch}'.format(
            indent=4 * ' ', branch=branch))
        print('adding new package entry:')
        [print(new_entry[x]) for x in range(len(new_entry))]
        del lines[-1]  # remove last '\n'
        lines += new_entry
    return '\n'.join(lines)


def _fetch_master_repos_file(repos_file_url=default_ros2_repos):
    response = requests.get(repos_file_url)
    response.raise_for_status()
    return response.content.decode()


def _fetch_pr_info(pr_url):
    url_items = pr_url.split('/')
    org = url_items[3]
    repo = url_items[4]
    pr_id = url_items[6]
    if org is None:
        raise IndexError(
            'could not find any github organization in url {url}'.format(
                url=pr_url))
    if repo is None:
        raise IndexError(
            'could not find any github repository in url {url}'.format(
                url=pr_url))
    if pr_id is None or not pr_id.isdigit():
        raise IndexError(
            'could not find any pull request id in url {url}'.format(
                url=pr_url))

    print('analyzing pull request url', pr_url)

    request_url = api_url + '/repos/{org}/{repo}/pulls/{pr_id}'.format(
        org=org, repo=repo, pr_id=pr_id)
    pr_info = requests.get(request_url)
    jPr = json.loads(pr_info.content.decode())

    repos_index = org + '/' + repo
    url = jPr['head']['repo']['html_url'] + '.git'
    branch = jPr['head']['ref']
    return repos_index, url, branch


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument(
        'pr_url',
        nargs='+',
        help='modify repos file with these PR url')
    parser.add_argument(
        '-m', '--master_repos_url',
        nargs='?',
        help='original repos file where to merge PRs into')
    parser.add_argument(
        '-f', '--gist-file-name',
        type=str, default='external_contribution.txt',
        help='file name of the gist to be created')
    args = parser.parse_args()

    auth = None
    token_param = ''
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token is None:
        username, password = _get_username_and_password()
        auth = HTTPBasicAuth(username, password)
    else:
        token_param = '?access_token=' + github_token

    master_repo_file = default_ros2_repos
    if args.master_repos_url:
        master_repo_file = args.master_repos_url
    ros2_repos = _fetch_master_repos_file(master_repo_file)

    for pr in args.pr_url:
        pkg, url, branch = _fetch_pr_info(pr)
        ros2_repos = _modify_master_repos(ros2_repos, pkg, url, branch)
    gist_url = _create_gist(ros2_repos, token_param, auth, args.gist_file_name)

    print('new gist url:')
    print(gist_url)
