# -*- coding: utf-8 -*-

import os
import codecs

class UpdateTag:
    def __init__(self):
        self.tags = {}
        self.file_name = "tags.txt"
        self.file_path = os.path.join(os.getcwd(), self.file_name)
        if os.path.isfile(self.file_path): self.read_tags()

    def read_tags(self):
        try:
            with open(self.file_path, 'r') as fh:
                for tag_data in fh.readlines():
                    tag_name, tag_num = tag_data.split(": ")
                    self.tags[tag_name] = int(tag_num)
        except Exception as err:
            print "read tags.txt filed, err: %s" % err
            raise

    def update_tags(self, tags):
        for tag in tags:
            if self.tags.get(tag): self.tags[tag] += 1
            else: self.tags[tag] = 1

    def write_tags(self):
        # 如果是unicode类型的字符串，就可以直接write，如果是'utf-8'类型的字符串就需要解码为unicode再write
        try:
            with codecs.open(self.file_path, 'w', 'utf-8') as fh:
                for key in self.tags:
                    fh.write(": ".join([to_unicode(key), str(self.tags[key])]) + '\n')
        except Exception as err:
            print "write tags.txt filed, %s\n" % err
            print "tags data is : %s" % self.tags

class KeepUnique:
    def __init__(self):
        self.medium_id_dict = {}
        self.new_id_dict = {}
        self.file_name = "medium_ids.txt"
        self.file_path = os.path.join(os.getcwd(), self.file_name)
        if os.path.isfile(self.file_path): self.read_medium_ids()

    def read_medium_ids(self):
        try:
            with open(self.file_path, 'r') as fh:
                for date in fh.readlines():
                    self.medium_id_dict[date.split("\n")[0]] = ""
        except Exception as err:
            print "read medium ids txt filed, err: %s" % err
            raise

    def is_exist_name(self, name):
        return self.medium_id_dict.get(name) is not None or \
               self.new_id_dict.get(name) is not None

    def add_new_name(self, name):
        self.new_id_dict[name] = ''

    def write_medium_names(self):
        try:
            with codecs.open(self.file_path, 'a', 'utf-8') as fh:
                [fh.write(iden + '\n') for iden in self.new_id_dict.keys()]
        except Exception as err:
            print "write medium names file filed, err: %s\n" % err
            print "new medium names is :%s" % self.new_id_dict

def to_unicode(s):
    return s if isinstance(s, unicode) else s.decode('utf-8')

def to_str(s):
    return s.encode('utf-8') if isinstance(s, unicode) else s
