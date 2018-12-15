# -*- coding: utf-8 -*-

import os
import sys
import requests
import xmltodict
from six.moves import queue as Queue
from threading import Thread
import re
import codecs
from util import UpdateTag, KeepUnique, to_str, to_unicode
import constant as const


class DownloadWorker(Thread):
    def __init__(self, queue, unique, tags, proxies=None):
        Thread.__init__(self)
        self.queue = queue
        self.proxies = proxies
        self.unique = unique
        self.tags = tags
        self.curr_index = 0

    def run(self):
        while True:
            medium_type, post, target_folder, self.curr_index = self.queue.get()
            print "%s:%s: " % (medium_type, self.curr_index)
            self.download(medium_type, post, target_folder)
            self.queue.task_done()

    def download(self, medium_type, post, target_folder):
        try:
            medium_url = self._get_medium_url(medium_type, post)
            if medium_url is not None:
                self._download(medium_type, medium_url, target_folder, post)
            medium_url = self._get_medium_url(medium_type, post, no_photo_url=True)
            if medium_url is not None:
                self._download(medium_type, medium_url, target_folder, post)
        except Exception as err:
            if "已经存在" not in err.message:
                print "download failed, err: %s" % err

    def _get_medium_url(self, medium_type, post, no_photo_url=False):
        try:
            if no_photo_url and medium_type == "photo":
                if not post.get("regular-body"):
                    return None
                regular_body = post['regular-body']
                urls = []
                for url in regular_body.split("img src=\""):
                    if url.startswith("http"):
                        urls.append(url.split("\"")[0])
                if not urls:
                    return
                post["photo-url"] = [{"#text": urls[0]}]
                if len(urls) > 1:
                    post["photoset"] = {"photo": [{"photo-url": [{"#text": url}]} for url in urls]}

            if no_photo_url and medium_type == "video":
                if not post.get("regular-body"):
                    return None
                regular_body = post['regular-body']
                urls = []
                for url in regular_body.split("source src=\""):
                    if url.startswith("http"):
                        urls.append(url.split("\"")[0])
                if not urls:
                    return
                if len(urls) > 1:
                    print post
                return urls[0]

            if medium_type == "photo":
                if post.get("photo-url"):
                    return post["photo-url"][0]["#text"]
                return None

            if medium_type == "video":
                if not post.get("video-player"):
                    return None
                video_player = post["video-player"][1]["#text"]
                hd_pattern = re.compile(r'.*"hdUrl":("([^\s,]*)"|false),')
                hd_match = hd_pattern.match(video_player)
                try:
                    if hd_match is not None and hd_match.group(1) != 'false':
                        return hd_match.group(2).replace('\\', '')
                except IndexError:
                    pass
                pattern = re.compile(r'.*src="(\S*)" ', re.DOTALL)
                match = pattern.match(video_player)
                if match is not None:
                    try:
                        return match.group(1)
                    except IndexError:
                        return None
        except Exception as err:
            print "get medium url failed, err: %s" % err
            raise

    def _download(self, medium_type, medium_url, target_folder, post):
        date = post['@date-gmt'].split(" GMT")[0]
        if medium_type == "photo":
            medium_id = medium_url.split('tumblr_')[1].split('_')[0]
            description = ",".join(re.findall(const.GET_CH_PATTERN, post.get('photo-caption', post.get('@slug'))))
            postfix_name = "." + medium_url.split("/")[-1].split("?")[0].split(".")[-1]
        else:
            medium_id = medium_url.split('tumblr_')[1]
            description = ",".join(re.findall(const.GET_CH_PATTERN, post.get('video-caption', post.get('@slug'))))
            postfix_name = ".mp4"

        medium_name_model = [date, medium_id, description[:200], medium_type]
        tagged = post.get('tag')
        tag_str = "no_tags"
        if tagged:
            tag_str = ",".join(tagged)
            if len("".join([description[:200] + tag_str])) < 200:
                medium_name_model = [date, medium_id, description[:200], tag_str, medium_type]

        medium_name = "_".join(medium_name_model) + postfix_name

        self._write_medium(medium_name, medium_id, medium_type, medium_url, target_folder)
        self._write_txt(date, description, medium_id, target_folder, tag_str)

        if post.get('photoset') and len(post['photoset']['photo']) > 1:
            for pht in post['photoset']['photo'][1:]:
                pht_url = pht["photo-url"][0]["#text"]
                pht_id = pht_url.split('tumblr_')[1].split('_')[0]
                desc = ",".join(re.findall(const.GET_CH_PATTERN, pht.get('@caption', '')))
                postfix = "." + pht_url.split("/")[-1].split("?")[0].split(".")[-1]
                medium = "_".join([date, pht_id, desc[:200], medium_type]) + postfix
                self._write_medium(medium, pht_id, medium_type, pht_url, target_folder)
                self._write_txt(date, desc, pht_id, target_folder, tag_str)

    def _write_medium(self, medium_name, medium_id, medium_type, medium_url, target_folder):
        # 判断是否是重复资源
        if self.unique.is_exist_name(medium_id):
            print "资源[%s]已经存在" % to_str(medium_id)
            raise Exception("资源[%s]已经存在")
        self.unique.add_new_name(medium_id)

        file_path = os.path.join(target_folder, medium_name)
        if not os.path.isfile(file_path):
            print("Downloading %s from %s.\n" % (medium_name,
                                                 medium_url))
            retry_times = 0
            while retry_times < const.RETRY:
                try:
                    resp = requests.get(medium_url,
                                        stream=True,
                                        proxies=self.proxies,
                                        timeout=const.TIMEOUT)
                    with open(file_path, 'wb') as fh:
                        for chunk in resp.iter_content(chunk_size=1024):
                            fh.write(chunk)
                    break
                except:
                    # try again
                    pass
                retry_times += 1
            else:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                print("Failed to retrieve %s from %s.\n" % (medium_type,
                                                            medium_url))

    def _write_txt(self, date, description, medium_id, target_folder, tag_str):
        self.tags.update_tags(tag_str.split(','))
        need_tag_str = False
        name_model = [date, "0", medium_id, "text"]
        if len("".join([description[:200] + tag_str])) >= 200:
            need_tag_str = True
            name_model = [date, "0", medium_id, tag_str[:200], "text"]
        if len(description) > 200 or need_tag_str:
            # write description as a file
            file_name = "_".join(name_model) + ".txt"
            file_path = os.path.join(target_folder, file_name)
            if not os.path.isfile(file_path):
                try:
                    with codecs.open(file_path, 'w', 'utf-8') as fh:
                        fh.write(description)
                        fh.write(tag_str)
                except Exception as err:
                    print "filed to write txt, err: %s\n" \
                          "description: %s" % (err, description)


class CrawlerScheduler(object):

    def __init__(self, sites, proxies=None):
        self.sites = sites
        self.proxies = proxies
        self.queue = Queue.Queue()
        self.unique = KeepUnique()
        self.tags = UpdateTag()
        self.scheduling()

    def scheduling(self):
        # 创建工作线程
        for x in range(const.THREADS):
            worker = DownloadWorker(self.queue,
                                    unique=self.unique,
                                    tags=self.tags,
                                    proxies=self.proxies)
            # 设置daemon属性，保证主线程在任何情况下可以退出
            worker.daemon = True
            worker.start()

        for site in self.sites:
            if const.ISDOWNLOADIMG:
                self.download_photos(site)
            if const.ISDOWNLOADVIDEO:
                self.download_videos(site)

        self.unique.write_medium_names()
        self.tags.write_tags()

    def download_videos(self, site):
        self._download_media(site, "video", const.START)
        # 等待queue处理完一个用户的所有请求任务项
        self.queue.join()
        print("视频下载完成 %s" % site)

    def download_photos(self, site):
        self._download_media(site, "photo", const.START)
        # 等待queue处理完一个用户的所有请求任务项
        self.queue.join()
        print("图片下载完成 %s" % site)

    def _download_media(self, site, medium_type, start):
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, site)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        base_url = "https://{0}.tumblr.com/api/read?type={1}&num={2}&start={3}"
        start = const.START
        while True:
            media_url = base_url.format(site, medium_type, const.MEDIA_NUM, start)
            response = requests.get(media_url,
                                    proxies=self.proxies)
            data = xmltodict.parse(response.content)
            try:
                index = start
                posts = data["tumblr"]["posts"].get("post")
                if not posts:
                    break
                for post in posts:
                    # select the largest resolution
                    # usually in the first element
                    self.queue.put((medium_type, post, target_folder, index))
                    index += 1
                start += const.MEDIA_NUM
                print "%s 个post 已经被加入到队列中" % start
                if const.DEBUG:
                    break
            except KeyError as err:
                print "update posts to queue filed, err: %s" % err

def usage():
    print(u"未找到sites.txt文件，请创建.\n"
          u"请在文件中指定Tumblr站点名，并以逗号分割，不要有空格.\n"
          u"保存文件并重试.\n\n"
          u"例子: site1,site2\n\n"
          u"或者直接使用命令行参数指定站点\n"
          u"例子: python tumblr-photo-video-ripper.py site1,site2")


def illegal_json():
    print(u"文件proxies.json格式非法.\n"
          u"请参照示例文件'proxies_sample1.json'和'proxies_sample2.json'.\n"
          u"然后去 http://jsonlint.com/ 进行验证.")


if __name__ == "__main__":
    sites = None
    proxies = None
    # if os.path.exists("./proxies.json"):
    #     with open("./proxies.json", "r") as fj:
    #         try:
    #             proxies = json.load(fj)
    #             if proxies is not None and len(proxies) > 0:
    #                 print("You are using proxies.\n%s" % proxies)
    #         except:
    #             illegal_json()
    #             sys.exit(1)

    if len(sys.argv) < 2:
        # 校验sites配置文件
        filename = "sites.txt"
        if os.path.exists(filename):
            with open(filename, "r") as f:
                sites = f.read().rstrip().lstrip().split(",")
        else:
            usage()
            sys.exit(1)
    else:
        sites = sys.argv[1].split(",")

    if len(sites) == 0 or sites[0] == "":
        usage()
        sys.exit(1)

    CrawlerScheduler(sites, proxies=proxies)
