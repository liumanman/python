import json
import os

extend_flag_key = '__extends'


def read(file_path, dic=None):
    abs_file_path = file_path if os.path.isabs(file_path) else os.path.abspath(file_path)
    # with open(abs_file_path) as f:
    #     content = f.read()
    #     dic2 = json.loads(content)
    dic2 = __to_json(abs_file_path)
    parent_file_path = dic2.pop(extend_flag_key, None)
    merged_dict = dic2 if dic is None else _merge_dict(dic, dic2)
    if parent_file_path:
        dir_path = os.path.dirname(abs_file_path)
        abs_parent_file_path = os.path.join(dir_path, parent_file_path)
        return read(abs_parent_file_path, merged_dict)
    return merged_dict


def __to_json(file_path):
    abs_file_path = file_path if os.path.isabs(file_path) else os.path.abspath(file_path)
    dir_path = os.path.dirname(abs_file_path)
    with open(abs_file_path) as f:
        dic = json.load(f)

    __fill_from_file(dic, dir_path)
    return dic


def __fill_from_file(dic, dir_path):
    for k, v in dic.items():
        if isinstance(v, str):
            while 1:
                start = v.find('<file:')
                if start == -1:
                    break
                end = v.find('>', start + 6)
                if end == -1:
                    break
                file = v[start + 6:end]
                abs_file_path = os.path.join(dir_path, file)
                with open(abs_file_path) as f:
                    v = v[:start] + f.read() + v[end+1:]
            dic[k] = v

        elif isinstance(v, dict):
            __fill_from_file(v, dir_path)


def _merge_dict(dic1, dic2):
    for k1, v1 in dic1.items():
        if k1 in dic2:
            v2 = dic2[k1]
            if isinstance(v1, dict) and isinstance(v2, dict):
                dic2[k1] = _merge_dict(v1, v2)
            else:
                dic2[k1] = v1
        else:
            dic2[k1] = v1
    return dic2


def update_json_file(data, json_file):
    with open(json_file) as f:
        json_data = json.load(f)
    json_data.update(data)
    with open(json_file, 'w') as f:
        json.dump(json_data, f, sort_keys=True, indent=4)

if __name__ == '__main__':
    print(read('/home/el17/workspace/ebay/items/001.itm'))
