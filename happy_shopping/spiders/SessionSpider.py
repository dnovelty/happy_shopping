import json
import os
import time
from http.cookiejar import LWPCookieJar, MozillaCookieJar, CookieJar

import scrapy

from constant import meta_cookie_map_key, meta_cookie_jar_key
from exception import BizException
from log import session_logger
from mathUtils import int_between
from httpUtils import callback_2_json, status_ok
from timeUtils import millisecond_str

logger = session_logger


class SessionSpider(scrapy.Spider):
    name = "SessionSpider"
    retry_times = 20
    retry_time = 0
    refresh_seconds = 3600
    filename = 'jd.cookie'

    def __init__(self, name=None, **kwargs):
        super().__init__(name, **kwargs)
        self.nick_name = 'jd'
        self.trace_cookie_jar = True
        self.trace_cookie_map = True

    def start_requests(self):
        callback = 'jQuery{}'.format(int_between(1000000, 9999999))
        _ = millisecond_str()
        url = f'https://passport.jd.com/user/petName/getUserInfoForMiniJd.action?callback={callback}&_={_}'

        headers = {
            'Referer': 'https://order.jd.com/center/list.action'
        }
        request = scrapy.Request(url=url, callback=self.login_detect, headers=headers)
        if os.path.exists(SessionSpider.filename):
            cookie = LWPCookieJar(SessionSpider.filename)
            cookie.load(ignore_discard=True, ignore_expires=True)
            request.meta[meta_cookie_jar_key] = cookie
        yield request


    def parse(self, response, **kwargs):
        pass

    def login_detect(self, response):
        rsp_json = callback_2_json(response.text)
        if not rsp_json:
            return self.do_login(response)
        else:
            return self._session_holder(response)

    def do_login(self, response):
        appid = 133
        size = 147
        t = millisecond_str()
        url = f'https://qr.m.jd.com/show?appid={appid}&size={size}&t={t}'

        headers = {
            'Referer': 'https://passport.jd.com/new/login.aspx'
        }
        return scrapy.Request(url=url, headers=headers, callback=self.open_qr_image)

    def open_qr_image(self, response):
        QRCode_file = 'QRcode.png'
        with open(QRCode_file, 'wb') as f:
            f.write(response.body)
        logger.info('二维码获取成功，请打开京东APP扫描')
        self._open_image(QRCode_file)
        SessionSpider.retry_time = 0
        return self._token_fetch_api(response)

    def _token_fetch_api(self, response):
        appid = '133'
        callback = 'jQuery{}'.format(int_between(1000000, 9999999))
        token = response.meta[meta_cookie_map_key]['wlfstk_smdl']
        _ = millisecond_str()

        headers = {
            'Referer': 'https://passport.jd.com/new/login.aspx',
        }
        url = f'https://qr.m.jd.com/check?appid={appid}&callback={callback}&token={token}&_={_}'
        return scrapy.Request(url=url, callback=self._token_validate_api, headers=headers)

    def _token_validate_api(self, response):
        retry = False
        resp_json = {}
        while SessionSpider.retry_time <= SessionSpider.retry_times:
            if not status_ok(response):
                logger.error('获取二维码扫描结果异常')
                retry = True

            resp_json = callback_2_json(response.text)
            if resp_json['code'] != 200:
                logger.info('Code: %s, Message: %s', resp_json['code'], resp_json['msg'])
                retry = True
            if retry:
                time.sleep(2)
                return self._token_fetch_api(response)
            else:
                break
            SessionSpider.retry_time = SessionSpider.retry_time + 1

        if not 'ticket' in resp_json:
            raise BizException("无法获取token进行登录验证")
        ticket = resp_json['ticket']
        url = f'https://passport.jd.com/uc/qrCodeTicketValidation?t={ticket}'
        headers = {
            'Referer': 'https://passport.jd.com/uc/login?ltype=logout',
        }

        return scrapy.Request(url=url, headers=headers, callback=self._token_validate_result)

    def _token_validate_result(self, response):
        if not status_ok(response):
            raise BizException('验证token失败')
        resp_json = json.loads(response.body)
        if resp_json['returnCode'] == 0:
            logger.info("京东登录验证成功")
            return self._session_holder(response)
        else:
            logger.info(resp_json)
            raise BizException('验证token失败')

    def save_cookies(self, response):
        jar = response.meta[meta_cookie_jar_key]
        cookie = LWPCookieJar(SessionSpider.filename)
        # for key, values in jar._cookies.items():
        #     for key_1,values_1 in values.items():
        #         for key_2, values_2 in values_1.items():
        #             cookie.set_cookie(values_2)
        cookie.__dict__.update(jar.__dict__)
        cookie.save(ignore_discard=True, ignore_expires=True)

    def _open_image(self, image_file):
        if os.name == "nt":
            os.system('start ' + image_file)  # for Windows
        else:
            if os.uname()[0] == "Linux":
                if "deepin" in os.uname()[2]:
                    os.system("deepin-image-viewer " + image_file)  # for deepin
                else:
                    os.system("eog " + image_file)  # for Linux
            else:
                os.system("open " + image_file)  # for Mac

    def _session_holder(self, response):
        self.save_cookies(response)
        time.sleep(SessionSpider.refresh_seconds)
        url = 'https://order.jd.com/center/list.action'
        headers = {
            ':authority': 'order.jd.com',
            ':method': 'GET',
            ':path': '/center/list.action',
            ':scheme': 'https',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9',
            'cache-control': 'max-age=0',

            'sec-ch-ua': '"Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-site',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }
        yield scrapy.Request(url=url, callback=self._session_holder, headers=headers)


