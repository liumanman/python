import requests
import xml.dom.minidom as xml_dom
import os
import time
import json
import sys
from decimal import Decimal
from enum import Enum
from jinja2 import Environment, FileSystemLoader
import jreader


def to_file(file_name, content):
    abs_file_path = file_name if os.path.isabs(file_name) else os.path.abspath(file_name)
    dir_path = os.path.dirname(abs_file_path)
    if not os.path.exists(dir_path):
        os.makedirs(dir_path, exist_ok=True)
    with open(abs_file_path, 'w') as f:
        f.write(str(content))


class EWS(object):
    __ebay_url = 'https://api.ebay.com/ws/api.dll'
    __devid= ''
    __appid = ''
    __certid = ''
    __token = ''


    def __init__(self, request_template_dir='templates', log_dir='logs'):
        self._jinja_env = Environment(loader=FileSystemLoader(request_template_dir))
        self._devid = self.__class__.__devid
        self._appid = self.__class__.__appid
        self._certid = self.__class__.__certid
        self._token = self.__class__.__token
        self._api_url = self.__class__.__ebay_url
        self._log_dir = log_dir

    def __render_template(self, template_name, **data):
        template = self._jinja_env.get_template(template_name)
        return template.render(**data)

    def call(self, request_template_name, request_name,
             reference_number=None, header=None,
             files=None, **request_data):
        headers = {'X-EBAY-API-COMPATIBILITY-LEVEL': 933,
                   'X-EBAY-API-DEV-NAME': self._devid,
                   'X-EBAY-API-APP-NAME': self._appid,
                   'X-EBAY-API-CERT-NAME': self._certid,
                   'X-EBAY-API-CALL-NAME': request_name,
                   'X-EBAY-API-SITEID': 0}
        xml_body = self.__render_template(request_template_name,
                                          token=self._token, request_name=request_name,
                                          **request_data)
        data = {'xml_body': xml_body} if files else xml_body
        if files:
            file_dict = {'file' + str(i):
                             (os.path.basename(v),
                              open(v, 'rb'),
                              'application/octet-stream')
                         for i, v in enumerate(files)}
        else:
            file_dict = None
        if header:
            headers.update(header)

        res = requests.post(self._api_url, headers=headers, data=data, files=file_dict)
        # write response log
        self.__log_call(request_name, reference_number, res)
        root = xml_dom.parseString(res.text).documentElement
        ack = root.getElementsByTagName('Ack')[0].childNodes[0].data
        is_success = True if ack in ['Success', 'Warning'] else False
        if is_success:
            msg = res.text
        else:
            msg = root.getElementsByTagName('ShortMessage')[-1].childNodes[0].data
        return is_success, msg

    def __log_call(self, request_name, reference_number, response):
        reference_number = reference_number or 'log'
        res_body = response.text
        res_headers = '\n'.join(['{} {}'.format(k, v) for k, v in response.headers.items()])
        res_log_content = res_headers + '\n\n' + str(res_body)
        request = response.request
        req_body = request.body
        req_headers = '\n'.join(['{} {}'.format(k, v) for k, v in request.headers.items()])
        req_log_content = req_headers + '\n\n' + str(req_body)
        now = time.time()
        time_tag = time.strftime('%Y%m%d.%H%M%S', time.localtime(now))
        time_tag = '{}.{}'.format(time_tag, str(now).split('.')[1][:3])
        log_types = ('request', req_log_content), ('response', res_log_content)
        log_types_detail = (('{}.{}.{}.{}'.format(reference_number, request_name, time_tag, i[0]), i[1]) for i in
                            log_types)
        log_types_detail = ((os.path.join(self._log_dir, i[0]), i[1]) for i in log_types_detail)
        for i in log_types_detail:
            to_file(*i)

    # def to_file(self, file_name, content):
    #     abs_file_path = file_name if os.path.isabs(file_name) else os.path.abspath(file_name)
    #     dir_path = os.path.dirname(abs_file_path)
    #     if not os.path.exists(dir_path):
    #         os.makedirs(dir_path, exist_ok=True)
    #     with open(abs_file_path, 'w') as f:
    #         f.write(str(content))


class ItemEWS(EWS):
    Type = Enum('Type', 'add revise')
    _item_pic_type = 'jpg|png'
    _list_type_dict = {'auction': 'Chinese',
                       'fixed': 'FixedPriceItem'}

    @staticmethod
    def get_item_name(item_file_name):
        return item_file_name.split('.')[0]

    @staticmethod
    def update_item_ebay_info(item_file, ebay_id, list_fee, **kwargs):
        item_name = ItemEWS.get_item_name(os.path.basename(item_file))
        abs_item_file_path = item_file if os.path.isabs(item_file) else os.path.abspath(item_file)
        item_file_dir = os.path.dirname(abs_item_file_path)

        ebay_file_path = os.path.join(item_file_dir, '{}.{}'.format(item_name, 'ebay'),
                                      '{}.{}.ebay'.format(item_name, ebay_id))
        if os.path.exists(ebay_file_path):
            with open(ebay_file_path) as f:
                ebay_content = f.read()
            ebay_dict = json.loads(ebay_content)
        else:
            ebay_dict = {}
        ebay_dict.update(kwargs)
        ebay_dict_shell = DictGetter(ebay_dict)
        ebay_dict_shell._ebay_id = ebay_id
        if 'list_fee' in ebay_dict_shell:
            ebay_dict_shell.list_fee = \
                str(Decimal(ebay_dict_shell.list_fee) + list_fee)
        else:
            ebay_dict_shell.list_fee = str(list_fee)
        # ebay_dict_shell.__setattr__(jreader.extend_flag_key, item_file)
        ebay_content = json.dumps(ebay_dict_shell.get_dict(), indent=4)

        to_file(ebay_file_path, ebay_content)


    def __init__(self, item_file_dir='.'):
        self.item_file_dir = item_file_dir
        self.pic_srv = PictureEWS()
        super().__init__()

    def _get_abs_item_file_path(self, file_name):
        if os.path.isabs(file_name):
            return file_name
        else:
            return os.path.join(self.item_file_dir, file_name)

    def _update_item(self, update_type, item_file):
        item_name = ItemEWS.get_item_name(os.path.basename(item_file))
        abs_item_file_path = item_file if os.path.isabs(item_file) else os.path.join(self.item_file_dir, item_file) 
        item_dict = jreader.read(abs_item_file_path)
        item_dict = self._convert_item_dict(item_dict)
        if 'pictures' not in item_dict:
            item_dict['pictures'] = self._upload_pictures(item_name, item_file)
        template_name = 'item.xml'
        api_name = 'AddItem' if update_type == ItemEWS.Type.add else 'ReviseItem'
        is_success, res = super().call(template_name, api_name, reference_number=item_name, **item_dict)
        if not is_success:
            raise Exception(res)
        ebay_id, fee = self._read_resp(res)
        # self._save_ebay_info(ebay_id, fee,
        #                      item_file, item_name)
        ItemEWS.update_item_ebay_info(abs_item_file_path, ebay_id, fee)
        return ebay_id, fee

    def _get_item_ebay_info(self, ebay_id=None, file_name=None, *fields):
        if not ebay_id:
            if not file_name:
                pass
            item_dict = jreader.read(file_name)
            ebay_id = item_dict['ebay_id']
        is_success, res = super().call('get_item.xml', 'GetItem', reference_number=ebay_id, ebay_id=ebay_id)
        if not is_success:
            raise Exception(res)
        ebay_item_dict = self.__class__._get_item_dict_from_res(res, fields)
        if not fields:
            return res
        if len(ebay_item_dict) == 1:
            return ebay_item_dict[fields[0]]
        else:
            return ebay_item_dict

    @staticmethod
    def _get_item_dict_from_res(res, fields):
        root = xml_dom.parseString(res).documentElement
        item_dict = {v:root.getElementsByTagName(v)[0].childNodes[0].data for v in fields}
        return item_dict

    def _get_item_pictures(self, item_name):
        file_list = os.listdir(self.item_file_dir)

        def f(x):
            return x[0] == item_name and x[-1] in ItemEWS._item_pic_type.split('|')
        picture_list = [i for i in file_list if f(i.split('.'))]
        return picture_list

    def _upload_pictures(self, item_name, item_file):
        pic_path_list = self._get_item_pictures(item_name)
        if not pic_path_list:
            raise Exception("Can't find any picture for item {}".format(item_name))

        def f(x):
            return x if os.path.isabs(x) else os.path.join(self.item_file_dir, x)
        pic_abs_path_list = list(map(f, pic_path_list))
        pic_url_list = self.pic_srv.upload(*pic_abs_path_list)
        pic_base_url = self._get_pic_base_url(pic_url_list[0])
        item_file_abs_path = os.path.join(self.item_file_dir, item_file)
        jreader.update_json_file({'pictures': pic_url_list, '_pic_base_url': pic_base_url},
                                 item_file_abs_path)
        return pic_url_list

    def _get_pic_base_url(self, pic_url):
        tmp_url = pic_url.split('?')[0]
        i = tmp_url.rfind('/$_')
        if i == -1:
            raise Exception('Invalid pic url.')
        return tmp_url[: i + 3]

    def _read_resp(self, res):
        root = xml_dom.parseString(res).documentElement
        ebay_id = root.getElementsByTagName('ItemID')[0].childNodes[0].data
        fee_nodes = (Decimal(i.childNodes[0].data) for i in root.getElementsByTagName('Fee') if
                     i.childNodes[0].nodeType == i.TEXT_NODE)
        return ebay_id, sum(fee_nodes)


    def add_item(self, item_file):
        ebay_id, fee = self._update_item(ItemEWS.Type.add, item_file)
        now = time.time()
        time_tag = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
        jreader.update_json_file({'_ebay_id': ebay_id, 'last_upload_data': time_tag},
                                 os.path.join(self.item_file_dir, item_file))
        return ebay_id, fee


    def revise_item(self, item_file):
        ebay_id, fee = self._update_item(ItemEWS.Type.revise, item_file)
        now = time.time()
        time_tag = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now))
        jreader.update_json_file({'last_upload_data': time_tag},
                                 os.path.join(self.item_file_dir, item_file))
        return ebay_id, fee

    def update_item(self, upload_type, item_file):
        fun = self.add_item if upload_type == ItemEWS.Type.add else self.revise_item
        return fun(item_file)


    def upload_item_by_batch(self, upload_type, batch_item_file):
        abs_batch_item_file_path = os.path.join(self.item_file_dir, batch_item_file)
        item_file_dir = os.path.dirname(abs_batch_item_file_path)
        with open(abs_batch_item_file_path) as f:
            while 1:
                item_file = f.readline().strip()
                if not item_file:
                    break
                item_file = os.path.join(item_file_dir, item_file)
                try:
                    ebay_id, fee = self.update_item(update_type, item_file) 
                except Exception as e:
                    print('{}:{}'.format(item_file, str(e)))
                else:
                    print('{}:{}'.format(item_file, fee))

    def update_ebay_id(self, item_file):
        abs_item_file = self._get_abs_item_file_path(item_file)
        item_dict = jreader.read(abs_item_file)
        ebay_id = item_dict['ebay_id']
        relisted_ebay_id = self._get_item_ebay_info(ebay_id, None, 'RelistedItemID')
        if relisted_ebay_id:
            jreader.update_json_file({'ebay_id':relisted_ebay_id}, abs_item_file)
            return relisted_ebay_id

    def update_ebay_id_by_batch(self, batch_file):
        abs_batch_item_file_path = os.path.join(self.item_file_dir, batch_item_file)
        item_file_dir = os.path.dirname(abs_batch_item_file_path)
        with open(abs_batch_item_file_path) as f:
            for item_file in f:
                item_file = item_file.strip()
                item_file = os.path.join(item_file_dir, item_file)
                try:
                    relisted_ebay_id = self.update_ebay_id(item_file) or 0 
                except Exception as e:
                    print('{}:{}'.format(item_file, str(e)))
                else:
                    print('{}:{}'.format(item_file, relisted_ebay_id))


    def _convert_item_dict(self, item_dict):
        item = DictGetter(item_dict)
        if 'list_type' in item:
            item.list_type = self.__class__._list_type_dict[item.list_type]
        item.duration = 'Days_30' if item.list_type == 'FixedPriceItem' else 'Days_7'
        if '_ebay_id' in item:
            item.ebay_id = item._ebay_id
        return item.get_dict()


class PictureEWS(EWS):
    def upload_single(self, pic_path):
        pic_name = os.path.basename(pic_path)
        is_success, res = super().call('upload_picture.xml',
                                       'UploadSiteHostedPictures', pic_name, files=[pic_path],
                                       picture_name=pic_name)
        if is_success:
            root = xml_dom.parseString(res).documentElement
            pic_url = root.getElementsByTagName('FullURL')[0].childNodes[0].data
            return pic_url
        else:
            raise Exception(res)

    def upload(self, *pics_path):
        return list(map(self.upload_single, pics_path))


class DictGetter(object):
    __internal_attr = ['_dic']

    def __init__(self, dic):
        self._dic = dic

    def __getattr__(self, name):
        value = self._dic[name]
        if isinstance(value, dict):
            return DictGetter(value)
        else:
            return value

    def __setattr__(self, name, value):
        if name in self.__class__.__internal_attr:
            return object.__setattr__(self, name, value)
        else:
            self._dic[name] = value

    def __iter__(self):
        return iter(self._dic)

    def get_dict(self):
        return self._dic

    # def has_key(self, key):
    #     return key in self._dic

def generate_item_list_html(item_list_file, output_file):
    abs_item_list_file_path = os.path.abspath(item_list_file)
    file_dir = os.path.dirname(abs_item_list_file_path)
    item_file_list = []
    with open(item_list_file) as f:
        while 1:
            item_file = f.readline().strip()
            if not item_file:
                break
            item_file_list.append(item_file)
    item_list = []
    for item_file in item_file_list:
        print(item_file)
        item_dict = jreader.read(os.path.join(file_dir, item_file))
        item_url = 'http://www.ebay.com/itm/{}'.format(item_dict['_ebay_id'])
        item_pic_url = '{}0.jpg'.format(item_dict['_pic_base_url'])
        item_list.append((item_url, item_pic_url))
    env = Environment(loader=FileSystemLoader(os.path.join(sys.path[0], 'templates')))
    template = env.get_template('item_list.html')
    html = template.render(item_list=item_list)
    with open(output_file, 'w') as f:
        f.write(html)


if __name__ == '__main__':
    upload_type_dict = {'additem': ItemEWS.Type.add, 'reviseitem': ItemEWS.Type.revise}
    operation_type = sys.argv[1]
    batch_file = sys.argv[2] if len(sys.argv) > 1 else None
    # if batch_file:
    #     abs_batch_file_path = batch_file if os.path.isabs(batch_file) else os.path.abspath(batch_file)
    #     item_file_dir = os.path.dirname(abs_batch_file_path)
    #     batch_file_name = os.path.basename(abs_batch_file_path)
    if operation_type in upload_type_dict:
        ews = ItemEWS()
        if batch_file:
            ews.upload_item_by_batch(upload_type_dict[operation_type], batch_file)
        else:
            for item_file in sys.stdin:
                ews.update_item(upload_type_dict[operation_type], item_file)
    elif operation_type == 'mkitemlist':
        output_html = sys.argv[3]
        generate_item_list_html(batch_file, output_html)
    else operation_type == 'updateid':
        ews = ItemEWS()
        if batch_file:
            ews.update_ebay_id_by_batch(batch_file)
        else:
            for item_file in sys.stdin:
                ews.update_ebay_id(item_file)
