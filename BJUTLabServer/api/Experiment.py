from datetime import date, datetime
from typing import List

from ..exception import APIReinitializationError, WerkzeugException
from ..utilities import (
    jsonify
)


class ExpAPI:
    __exp_instance = None

    # 通过对这个元组使用index方法获get_labs调用存储过程时应当将filter插入到参数中的位置
    _GET_LAB_FILTER_KEYS = ('name', 'principal', 'open', 'time', 'day')

    _GET_ORDER_RECORD_PROC = ('get_student_order_record',)
    _GET_LAB_DAY_NUM_TO_CHAR = ('一', '二', '三', '四', '五', '六', '日')

    def __init__(self, logger, sql):
        if ExpAPI.__exp_instance is not None:
            raise APIReinitializationError('Experiment')
        self._logger = logger
        self._sql = sql

    @staticmethod
    def get_instance(logger, sql):
        if ExpAPI.__exp_instance is None:
            ExpAPI.__exp_instance = ExpAPI(logger, sql)
        return ExpAPI.__exp_instance

    def get_orders(self, page_index, page_size, type_code: int, uid: str):
        """
        用于用户查询自己的预约记录或管理员查询自己实验室的预约记录。

        使用情景:

            1. 当用户进入个人主页，点击一个有查看`实验室预约记录`功能的按钮时，前端发送请求，
            后端根据请求发送用户本人的所有预约记录。

            2. 实验室管理人员想要查看实验室的借用情况，点击一个有查看`本实验室的预约记录`功
            能的按钮，获取关于一个实验室的所有预约记录，同样，这个实验室必须是负责人本人
            负责的，否则只会返回一个空集。

        :param page_index: 分页下标
        :param page_size: 每页显示的记录数量
        :param type_code: 用户类型，从session['type']获取
        :param uid: 用户id，从session['id']获取
        """
        proc_name = 'get_lab_order_record'
        if type_code < 2:
            param = (page_size, page_index, uid, 0, 0, 0, 0, 0)
        else:
            dataset, record_count = self._sql.query(f'select lab_id from labs where principal_sid = {uid}')
            param = (page_size, page_index, 0, 0, 0, 0, dataset[0][0], 0)
        dataset, count = self._sql.run_proc(proc_name, page_size, param)
        self._logger.info('dataset: {}'.format(dataset))
        self._logger.info('count: {}'.format(count))
        order_list = []
        for record in dataset:
            order_record = {
                'order': record[2],
                'use': record[3],
                'lab': record[5],
                'usage': record[6],
                'status': record[7]
            }
            order_list.append(order_record)
        return jsonify(order_list)

    def get_order(self, order_id: int, type_code: int, user_id: str):
        """
        获取order_id对应的一次预约记录，用于用户或管理员查询某一条预约记录的具体情况。

        使用情景:

            用户或管理人员面前有一个清单，内容为所有的预约记录（对于用户，是他的所有历史预约
            记录；对管理员，是他负责的实验室的所有预约记录），他点击一个记录，则会调用本API
            返回该记录的所有信息。

        :param order_id: 预约记录id
        :param type_code: 用户类型，从session['type']获取
        :param user_id: 用户id，从session['id']获取
        """
        query_string = f'select * from lab_order_record where order_id = {order_id}'
        if type_code < 2:  # 如果不是管理员，通过@user_id判断
            query_string += f' and user_id = {user_id}'

        dataset, result_count = self._sql.query(f'select * from lab_order_record '
                                                f'where order_id = {order_id} and user_type={type_code}', 1)
        if result_count == 0:
            return ''
        lab_id = dataset[0][5]
        if type_code == 2:  # 如果是管理员，判断管理员是否负责该实验室，如果不是，则手动返回空字符串
            dataset, result_count = self._sql.query(f'select principal_sid from labs where lab_id={lab_id}')
            if result_count == 0 or dataset[0][0] != user_id:
                return ''
        return jsonify({
            'user_id': dataset[0][1],
            'order_at': dataset[0][2],
            'use_at': dataset[0][3],
            'range': dataset[0][4],
            'lab_id': lab_id,
            'usage': dataset[0][6],
            'status': dataset[0][7]
        })

    def create_order(self, user_id: str, type_code: int, commit_dt: datetime, use_d: date,
                     time_range: str, lab_id: int, usage: str, instruments: List[str]):
        """
        创建一个实验室预约申请。不需要发送申请人的学号等信息，后端直接从session中提取。

        使用场景:

            用户想要预约使用实验室，则通过此API发送一个申请。

        :param user_id: 用户id，从session['id']获取
        :param type_code: 用户类型，从session['type']获取
        :param commit_dt: 预约提交的时间，由前端发送
        :param use_d: 实验室使用日期
        :param time_range: 实验室使用时间段。格式：08:00~14:30
        :param lab_id: 实验室编号
        :param usage: 实验室借用的用途。100字以内
        :param instruments: 预约的实验仪器，是一个列表（数组），其中的每一个元素是一个实验仪器编号
        """
        proc_name = 'create_order'
        if len(instruments) > 0:
            ins_list_len_12 = [x if len(x) == 12 else '@@@@' + x for x in instruments]  # 把8位的编号扩充为12位
            param_ins = '|'.join(ins_list_len_12) + '|'
        else:
            param_ins = None
        param = (user_id, type_code, commit_dt, use_d, time_range, lab_id, usage, param_ins)
        _, code = self._sql.run_proc(proc_name, 1, param)
        return jsonify({
            'return code': code
        })

    def get_labs(self, page_index: int, number: int, filter_str: str or None):
        proc_name = 'get_lab'
        param = [number, page_index, None, None, None, None]
        if filter_str is None:
            param.append(None)
        else:
            k, v = filter_str.split('->')
            pos = ExpAPI._GET_LAB_FILTER_KEYS.index(k)
            if k == 'day':
                insert_value = ''
                for i in range(1, 8):
                    if str(i) in v:
                        insert_value += ExpAPI._GET_LAB_DAY_NUM_TO_CHAR[i - 1]
            elif k == 'open':
                insert_value = bool(v)
            else:
                insert_value = v
            param.insert(pos + 2, insert_value)
        dataset, count = self._sql.run_proc(proc_name, number, tuple(param))
        self._logger.debug(f'get_labs::dataset: {dataset}')
        return_data = []
        for record in dataset:
            return_data.append({
                'lab_id': record[0],
                'lab_name': record[1],
                'open': record[3]
            })
        return jsonify(return_data)
