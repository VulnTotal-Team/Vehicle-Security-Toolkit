#!/usr/bin/python3

import time
import argparse
import requests
from lxml import etree
from pathlib import Path


SERVER = 'http://127.0.0.1:8888'

def app_list():
    """列出app"""

    headers = {'Authorization': f'Token {token}'}
    r = requests.get(url=f'{SERVER}/api/v1/app/', headers=headers)
    return r.json()


def app_create() -> int:
    """创建app"""

    headers = {'Authorization': f'Token {token}'}
    data = {'name': 'test', 'description': 'test'}
    r = requests.post(url=f'{SERVER}/api/v1/app/', headers=headers, data=data)
    return r.json()['id']


def app_delete(app_id: int):
    """删除app"""

    headers = {'Authorization': f'Token {token}'}
    data = {'id': app_id}
    r = requests.delete(url=f'{SERVER}/api/v1/app/{app_id}', headers=headers, data=data)
    return r.text


def scan_list() -> list:
    """列出扫描"""
    results = []
    headers = {'Authorization': f'Token {token}'}
    for i in range(1, 50):
        r = requests.get(url=f'{SERVER}/api/v1/scan/?page={i}', headers=headers)
        if r.status_code == 404:
            break
        else:
            apks = [i['description'] for i in r.json()['results']]
            results += apks
    return results


def scan_create(apk: Path, app: int):
    """创建扫描"""
    print(f'[+] {apk}')

    headers = {'Authorization': f'Token {token}'}
    data = {
        'description': apk,
        'app': app
    }
    files = {
        'apk': (
            apk.name,
            open(apk, 'rb')
        )
    }
    r = requests.post(url=f'{SERVER}/api/v1/scan/', headers=headers, data=data, files=files)
    return r.json()


def scan_read(scan_id: int) -> int:
    """获取扫描进度"""

    headers = {'Authorization': f'Token {token}'}
    data = {'id': scan_id}
    r = requests.get(url=f'{SERVER}/api/v1/scan/{scan_id}', headers=headers, data=data)
    return r.json()


def get_token(username: str, password: str) -> str:
    """获取API token"""

    data = {
        'username': username,
        'password': password
    }
    r = requests.post(url=f'{SERVER}/api/v1/auth-token/', data=data)
    return r.json()['token']


def register(username: str, password: str) -> int:
    """注册用户"""

    r = requests.get(url=f'{SERVER}/accounts/register/')
    csrf_token = r.cookies.get('csrftoken')
    csrfmiddlewaretoken = etree.HTML(r.text).xpath('/html/body/div[1]/form/input/@value')[0]

    cookies = {'csrftoken': csrf_token}
    data = {
        'csrfmiddlewaretoken': csrfmiddlewaretoken,
        'username': username,
        'first_name': '123', 'last_name': '123', 'email': '123@123.com',
        'password1': password, "password2": password
    }
    r = requests.post(url=f'{SERVER}/accounts/register/', cookies=cookies, data=data)
    return r.status_code


def argument():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", help="A config file containing APK path", type=str, required=True)
    return parser.parse_args()


if __name__ == '__main__':
    print('******************** apk-audit.py ********************')

    failed = []
    success_num = 0
    apk_dirs = open(argument().config, 'r').read().splitlines()

    # 注册用户并获取token
    username = 'auditor'
    password = 'audit123'
    r = register(username, password)
    token = get_token(username, password)
    print(f'[+] api token: {token}')

    # 确保只有一个app
    r = app_list()
    if r['count'] != 1:
        for i in r['results']:
            app_delete(i['id'])
        app_id = app_create()
    else:
        app_id = r['results'][0]['id']
    print(f'[+] app_id: {app_id}')

    results = scan_list()
    for apk in apk_dirs:
        if apk not in results:
            scan_id = scan_create(Path(apk), app_id)['id']
            while True:
                r = scan_read(scan_id)
                if r['status'] == 'Finished':
                    success_num += 1
                    break
                elif r['status'] == 'Error':
                    failed.append(apk)
                    break
                else:
                    time.sleep(5)

    print(f'扫描完成: {success_num}, 扫描失败: {len(failed)}')
    print('\n'.join(failed))