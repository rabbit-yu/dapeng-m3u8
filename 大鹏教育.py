import requests
import re
import subprocess
import os
from tqdm import tqdm
from time import sleep
from multiprocessing.dummy import Pool

s = '你的cookies'

cookies = {}
s = s.encode('utf-8').decode('latin1')
for k_v in s.split(';'):
    k,v = k_v.split('=',1)
    cookies[k.strip()] = v.replace('"','')


def spider(url,x):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55',
        'Host': 'www.dapengjiaoyu.cn',

        'Referer': 'https://www.dapengjiaoyu.cn/details/course?type=VIP&courseId=ijmiw8ve&faid=0853c508-9328-47e6-b65a-7b155523e509&said=0853c508-9328-47e6-b65a-7b155523e509&fuid=kewhtyxxuk&suid=&d=0&suu=51898ffd-988e-4455-8d8e-4158660db282&suc=1&state=LIVING'
    }
    # u = 'https://www.dapengjiaoyu.cn/dp-course/api/courses/ijmithjn'
    # r = requests.get(url=u,headers=headers).json()
    # className = r['title']
    menu = requests.get(url=url,headers=headers,cookies=cookies).json()
    className = menu['courseVodContents'][0]['title']
    for i in tqdm(menu['courseVodContents'][0]['lectures']):
        x += 1
        videoName = i['title']
        videoName = videoName.replace(' ','')
        # className = i['videoContent']['title']
        # className = re.findall('大鹏教育(.*?课)', className)[0]
        vid = i['videoContent']['vid'].replace('_e', '_2.m3u8')
        m3u8_url = 'https://hls.videocc.net/ef4825bc7e/f/' + vid
        m3u8_data = requests.get(m3u8_url).text
        ts_urls = re.findall('(https:.*?\.ts)', m3u8_data)
        for ts_url in ts_urls:
            index = re.findall('_2_(\d+\.ts)', ts_url)[0]
            ts = requests.get(url=ts_url).content
            write(className,ts,index)
            m3u8_data = m3u8_data.replace(ts_url,index)
        if 'URI' in m3u8_data:
            key_url = re.findall('URI="(.*?key)', m3u8_data)[0]
            key = requests.get(url=key_url).content
            with open(className + '\\' + 'key.m3u8','wb') as f3:
                f3.write(key)
            m3u8_data = m3u8_data.replace(key_url,'key.m3u8')
        write(className, m3u8_data)
        sleep(5)
        path = os.getcwd()
        os.chdir(className)
        sleep(1)
        merge(videoName,x)
        sleep(20)
        remove()
        sleep(2)
        os.chdir(path)
        print(f'合成完毕:{videoName}')


def write(name,data,index=''):
    if not os.path.exists(name):
        os.mkdir(name)
    if type(data) == str:
        with open(name + '\\' + 'index.m3u8','w') as f1:
            f1.write(data)
    else:
        with open(name + '\\' + index, 'wb') as f2:
            f2.write(data)


def merge(title,x):
    c = 'ffmpeg -allowed_extensions ALL -i index.m3u8 -c copy {}.mp4'.format(str(x)+title)
    subprocess.Popen(c,shell=True)


def remove():
    con = True
    while con:
        li = os.listdir()
        for i in li:
            if 'mp4' in i:
                for j in li:
                    if 'mp4' not in j:
                        os.remove(j)
                con = False
                break


if __name__ == '__main__':
    x = 0
    url = 'https://www.dapengjiaoyu.cn/api/old/courses/ih74zlgw/vods?page=1'
    spider(url,x)





