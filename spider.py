import time
from configparser import ConfigParser
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import re
import subprocess
import threading


class Spider:
    def __init__(self):
        self.tpool = ThreadPoolExecutor(max_workers=30)

        self.config = ConfigParser()
        try:
            self.config_path = os.getcwd() + r'\config.ini'
            self.config.read(self.config_path, encoding='utf-8')
            self.success_vid = eval(self.config.get('api', 'success_vid'))
        except:
            print('读取配置文件出错，请检查文件格式')
        self.headers = {
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1 Edg/103.0.5060.114'
        }
        self.session = requests.session()
        self.session.headers.update(self.headers)
        self.class_name = ''

    def login(self):
        url = 'https://passport.dapengjiaoyu.cn/account-login'
        data = {
            'account': self.config.get('api', 'user'),
            'password': self.config.get('api', 'password'),
            'source': 'NORMALLOGIN',
            'type': 'USERNAME',
            'responseType': 'JSON',
            'sourceType': 'PC'
        }
        self.session.post(url, data=data)
        self.session.get(
            'https://passport.dapengjiaoyu.cn/oauth/authorize?response_type=code&client_id=Dd8fbbB5&redirect_uri=//www.dapengjiaoyu.cn/callback&state=1')
        resp = self.session.get('https://www.dapengjiaoyu.cn/dp-course/api/users/details')
        if resp.status_code == 200:
            print('登录成功!')
        else:
            print(resp.status_code)
            print('登录失败!')

    def create_mik(self, path):
        if not os.path.exists(path):
            os.mkdir(path)

    def get_all_list(self):
        url = 'https://www.dapengjiaoyu.cn/api/old/courses/open'
        for page in range(1, 3):
            params = {
                'type': 'VIP',
                'collegeId': 'j5m484vz',
                'page': page,
                'size': '10',
            }
            resp = self.session.get(url, params=params)
            for info in resp.json():
                self.class_name = info['title']
                self.create_mik(f'{os.getcwd()}/{self.class_name}')
                courseId = info['id']
                qiid = self.get_qiid(courseId)
                self.get_list(qiid, courseId)

    def get_qiid(self, courseId):
        url = f'https://www.dapengjiaoyu.cn/api/old/courses/stages?courseId={courseId}'
        resp = self.session.get(url).json()
        liveStage = resp['liveStage'][0]
        if liveStage['completeChapter'] == liveStage['totalChapter']:
            qiid = liveStage['id']
        else:
            playbackStage = resp['playbackStage'][0]
            qiid = playbackStage['id']
        return qiid

    def get_list(self, qiid, courseId):
        file_index = 1
        url = f'https://www.dapengjiaoyu.cn/api/old/courses/stages/{qiid}/chapters'
        for page in range(1, 10):
            params = {
                'courseId': courseId,
                'page': page
            }
            resp = self.session.get(url, params=params).json()
            if len(resp) == 0:
                break
            else:
                for info in resp:
                    tasks = []
                    count = 0
                    vid = info['videoContent']['vid']
                    if vid in self.success_vid:
                        print('已经存在，跳过~')
                        file_index += 1
                        continue

                    ke_title = f"{file_index}-{info['title']}"
                    for _ in ['【', '】', ' ', '/']:
                        ke_title = ke_title.replace(_, '')
                    if os.path.exists(f'{os.getcwd()}/{self.class_name}/{ke_title}'):
                        print('已经存在，跳过~')
                        file_index += 1
                        continue

                    self.create_mik(f'{os.getcwd()}/{self.class_name}/{ke_title}')

                    for i in info['downloadableFileList']:
                        ossFileName = i['ossFileName']
                        ossUrl = i['ossUrl']
                        threading.Thread(target=self.zip_down, args=(ossFileName, ossUrl, ke_title)).start()

                    m3u8_url = f"https://hls.videocc.net/ef4825bc7e/a/{vid[:-1]}1.m3u8"
                    m3u8_data = requests.get(m3u8_url, headers=self.headers).text
                    if 'URI' in m3u8_data:
                        key_url = re.findall('URI="(.*?key)"', m3u8_data)[0]
                        key = requests.get(key_url, headers=self.headers).content
                        with open(f'{os.getcwd()}/ts/key.m3u8', 'wb') as f3:
                            f3.write(key)
                        m3u8_data = m3u8_data.replace(key_url, 'key.m3u8')

                    ts_urls = re.findall(r'(https:.*?\.ts)', m3u8_data)
                    for index, ts in enumerate(ts_urls):
                        m3u8_data = m3u8_data.replace(ts, f'{index}.ts')
                        tasks.append(self.tpool.submit(self.ts_down, index, ts))

                    with open(f'{os.getcwd()}/ts/index.m3u8', 'w') as f3:
                        f3.write(m3u8_data)

                    for _ in as_completed(tasks, timeout=60 * 2):
                        count += 1
                        print(f'\r爬取进度：{int(count / len(tasks) * 100)}%', end='')
                    print('\n爬取完毕')
                    self.merge(f'{ke_title}/{ke_title}')
                    self.success_vid.append(vid)
                    file_index += 1
                    # self.config.set('api', 'success_vid', str(self.success_vid))
                    # self.config.write(open(self.config_path, 'w', encoding='utf-8'))

    def zip_down(self, title, url, ke_title, chunk_size=5120):
        if url:
            response = requests.get(url, stream=True, headers=self.headers)
            with open(f'{os.getcwd()}/{self.class_name}/{ke_title}/{title}', mode='wb') as f:
                for chunk in response.iter_content(chunk_size):
                    f.write(chunk)
            print(f'{title}--下载完成')

    def ts_down(self, title, ts):
        resp = requests.get(ts, headers=self.headers, timeout=10)
        with open(f'{os.getcwd()}/ts/{title}.ts', 'wb') as f:
            f.write(resp.content)

    def merge(self, title: str):
        p = f'ffmpeg -allowed_extensions ALL -i {os.getcwd()}/ts/index.m3u8 -c copy {os.getcwd()}/{self.class_name}/{title}.mp4'
        p = p.replace('\\', '/')
        a = subprocess.run(p, shell=True)
        if a.returncode == 0:
            print('合并完成')

    def run(self):
        try:
            self.login()
            self.get_all_list()
            print('所有课程爬取完毕')
        except Exception as e:
            print(e)
        finally:
            self.config.set('api', 'success_vid', str(self.success_vid))
            self.config.write(open(self.config_path, 'w', encoding='utf-8'))
            print('等待线程结束，5S后自动关闭')
            time.sleep(5)

    def dan_run(self):
        try:
            self.login()
            self.class_name = self.config.get('api', 'class_name').replace(" ", "")
            self.create_mik(f'{os.getcwd()}/{self.class_name}')
            courseId = self.config.get('api', 'courseId').replace(" ", "")
            qiid = self.get_qiid(courseId)
            self.get_list(qiid, courseId)
            print('所有课程爬取完毕')
        except Exception as e:
            print(e)
        finally:
            self.config.set('api', 'success_vid', str(self.success_vid))
            self.config.write(open(self.config_path, 'w', encoding='utf-8'))
            print('等待线程结束，5S后自动关闭')
            time.sleep(5)

if __name__ == '__main__':
    s = Spider()
    # 爬取全部
    # s.run()

    # 爬取单个模块
    s.dan_run()
