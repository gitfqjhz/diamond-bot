# -*- coding: utf-8 -*-
import base64
import json
import time
import uuid
import random
import requests
import datetime
import hashlib
import sys
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# --- 密钥配置 (保持不变) ---
RSA_PRIVATE_KEY_STR = "MIICdwIBADANBgkqhkiG9w0BAQEFAASCAmEwggJdAgEAAoGBAK2obrvkb/npsEjqvvuJcVgGigOcdtvjGMGggufULIf6u4otOsofcBHdk3QZ2H/0qnf9Na7q6wmmE1+kuWJlEUO1/G/coBLrb3J3H7W6L2QR0dIYccEnD1P5qRaXdJvSWgSRIqzPQcP1A1a9BTwiDpQ9v77NTWGqi4JfbY24eI5TAgMBAAECgYABQd9vX9OJuS3sETsJwjB+ZSm5pffcVrQWrs1T1V7vKxsRgItU7E5Y6sRHCmrdXk2fqccqOYwzGS85uY0YD8hEtK580SCz1XKAgVqe/loPi7lYJH1W1xN29WWtS1JjNSN5HnPlWwQbGwkTxo1Om9u/SJ/fYphVXriwLP8bP+VCWQJBANOQJtRABQS4OYAHyyVbW6RBZ5d64Y/Kjhf1ZlIKRa9QDWCRlNg6XrJ0tZ5xt9RK1SDRZDniu6Eku3YHuI0/CJkCQQDSIhpNbDbS1554x1dO7oZATdufL+JVjZa/o6tqizslo5aoD7ahREuOh7e1mI4yDqmaA6jSsRL9OyG4a11lN8XLAkEAxe/kpEiRaW0DPyoLgpQLFY6r4Snyx5l3gCr05GT/9ZosKeGLJRLXbpeLJQa4O0MYTHAcGZxsd8PqL+/hVyVWYQJBAMFucxfiDXV41oAHv+8A0sRO52RaB9cJR0ORvjGNiRzUwdJi5JL+8y548DtR+1NI/AayZ63LItfInvnMm2SZOpECQFtjgv08sKNyKgFKOumAl55A4/Ai4LX7w1US2HGAeOJwL8G6nipePA8KbGBzjvXH9Lfr8GEuy1DdCxYcxhwnmWg="
RSA_PUBLIC_KEY_STR = 'MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDkmujpECrpxvCCF5iHnXDhSb4a8OODNg7x2dUggK0JNWzbw3Oz30aIZxzXm0dfVTRhuO+Upv0gtkwx5WVW1oLzwxAcQwmWx5G0F5B3yglsGZoDJZwgZmp7zrowOkyR59zKy4CHwbjwcxaSBVXtJ/NIZ21x63p663Nxjj1ZTIkl3wIDAQAB'

API_URLS = {
    'login': 'http://111.230.160.82/v2/user/login',
    'ad_list': 'http://111.230.160.82/v2/advert/info/getAdvert',
    'ad_submit': 'http://111.230.160.82/v2/advert/info/advertSubmit',
    'fund': 'http://111.230.160.82/user/fund/getFund'
}

class AccountWorker:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.session()
        self.token = None
        self.total_earned = 0 # 本次运行总获得
        self.current_total = 0 # 账号现有总数
        self.is_finished = False

    def log(self, msg):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{now}][{self.email}] {msg}")
        sys.stdout.flush()

    # --- 加解密辅助函数 ---
    def _aes_encrypt(self, text, key):
        cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        return base64.b64encode(cipher.encrypt(pad(text.encode('utf-8'), AES.block_size))).decode('utf-8')

    def _aes_decrypt(self, key, ciphertext):
        if not key or not ciphertext: return None
        cipher = AES.new(key.encode('utf-8'), AES.MODE_ECB)
        return unpad(cipher.decrypt(base64.b64decode(ciphertext)), AES.block_size).decode('utf-8')

    def _rsa_decrypt(self, ciphertext):
        private_key = serialization.load_der_private_key(base64.b64decode(RSA_PRIVATE_KEY_STR), password=None, backend=default_backend())
        return private_key.decrypt(base64.b64decode(ciphertext), padding.PKCS1v15()).decode('utf-8')

    def _get_secret(self, aes_key):
        public_key = serialization.load_der_public_key(base64.b64decode(RSA_PUBLIC_KEY_STR), backend=default_backend())
        encrypted = public_key.encrypt(aes_key.encode('utf-8'), padding.PKCS1v15())
        return base64.b64encode(encrypted).decode('utf-8')

    def refresh_headers(self):
        models = ["22041211AC", "SM-G9910", "KB2000", "V2049A", "M2102K1C"]
        self.session.headers.update({
            'User-Agent': f"Dalvik/2.1.0 (Linux; U; Android {random.randint(10,14)}; {random.choice(models)} Build/UP1A.231005.007)",
            'App-Version': '2.0.4',
            'App-Number': hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:16],
            'System-Type': 'Android',
        })

    def login(self):
        self.refresh_headers()
        key = str(uuid.uuid4()).replace('-', '')[:16]
        data = {"account": self.email, "appKey": "android", "code": self.password, "inviteCode": "", "type": 2}
        try:
            payload = self._aes_encrypt(json.dumps(data, separators=(',', ':')), key)
            resp = self.session.post(API_URLS['login'], data=payload, headers={'Secret': self._get_secret(key)})
            res_key = self._rsa_decrypt(resp.headers.get('Secret'))
            res_data = self._aes_decrypt(res_key, resp.json().get('data'))
            self.token = json.loads(res_data)['accessToken']
            self.session.headers.update({'Authorization': 'Bearer ' + self.token})
            return True
        except Exception as e:
            self.log(f"登录失败: {e}")
            return False

    def get_fund(self):
        try:
            key = str(uuid.uuid4()).replace('-', '')[:16]
            resp = self.session.get(API_URLS['fund'], headers={'Secret': self._get_secret(key)})
            total = int(resp.json().get('data', {}).get('quantity', 0))
            self.current_total = total
            return total
        except: return self.current_total

    def run_batch(self, batch_limit=20, total_target=9999999):
        """运行一个批次，直到赚够 batch_limit 或达到总目标"""
        if self.is_finished: return 0
        
        if not self.token:
            if not self.login(): return 0

        initial_bal = self.get_fund()
        current_earned = 0 # 本次批次赚得
        
        self.log(f"开始批次任务（当前总数:{initial_bal}, 目标:+{batch_limit}钻）")

        while current_earned < batch_limit and (self.total_earned) < total_target:
            self.refresh_headers()
            key = str(uuid.uuid4()).replace('-', '')[:16]
            try:
                # 获取广告列表
                self.log("获取广告列表...")
                ad_resp = self.session.post(API_URLS['ad_list'], data=self._aes_encrypt('{"systemType":1}', key), headers={'Current': "1", 'Size': '10', 'Secret': self._get_secret(key)})
                res_header_secret = ad_resp.headers.get('Secret')
                if not res_header_secret:
                    self.log("IP受限或列表获取失败，跳过本轮"); break
                
                ads_data = self._aes_decrypt(self._rsa_decrypt(res_header_secret), ad_resp.json().get('data'))
                if not ads_data:
                    self.log("广告数据解析失败，跳过本轮"); break
                
                self.log(f"获取到广告数据: {ads_data[:100]}...")
                for space in json.loads(ads_data):
                    for ad in space.get('adverts', []):
                        val = int(ad.get('diamond', 0))
                        if val not in [1, 2] or (self.total_earned) >= total_target: 
                            continue
                        
                        # 执行任务
                        wait = random.randint(32, 45)
                        self.log(f"执行任务[{ad['advertNo']}]({val}钻) 等待{wait}s...")
                        time.sleep(wait)
                        
                        s_key = str(uuid.uuid4()).replace('-', '')[:16]
                        reward_info = {
                            "advertNo": ad['advertNo'], "costModel": ad['costModel'],
                            "phoneBrand": "Xiaomi", "platformCode": ad["platformCode"],
                            "platformId": ad['platformId'], "spaceId": ad['spaceId'],
                            "systemType": "1", "systemVersion": "12",
                            "typeId": ad["typeId"], "typePlatformId": "0"
                        }
                        payload = self._aes_encrypt(json.dumps(reward_info, separators=(',', ':'), ensure_ascii=False), s_key)
                        self.log("提交任务完成...")
                        resp = self.session.post(API_URLS['ad_submit'], data=payload, headers={'Secret': self._get_secret(s_key)})
                        self.log(f"提交响应: {resp.status_code}")
                        
                        # 检查余额
                        time.sleep(2)
                        new_bal = self.get_fund()
                        earned_now = new_bal - (initial_bal + current_earned)
                        if earned_now > 0:
                            current_earned += earned_now
                            self.total_earned += earned_now
                            self.log(f"[√] 到账成功！当前现有总数:{new_bal} | 批次进度:{current_earned}/{batch_limit} 总进度:{self.total_earned}/{total_target}")
                        else:
                            self.log(f"[!] 余额未加，跳过该任务 (现有总数:{new_bal})")
                        
                        if current_earned >= batch_limit or self.total_earned >= total_target: break
                        time.sleep(random.randint(5, 10))
                    if current_earned >= batch_limit or self.total_earned >= total_target: break
            except Exception as e:
                self.log(f"批次运行异常: {e}")
                import traceback
                traceback.print_exc()
                break

        if self.total_earned >= total_target:
            self.log(f"🏆 该账户已完成总目标！账号现有总数: {self.current_total}")
            self.is_finished = True
        
        self.log(f"批次任务结束，本次获得: {current_earned}钻")
        return current_earned

if __name__ == '__main__':
    # 配置你的账户列表 (邮箱, 密码)
    accounts_config = [
        ("3965337298@qq.com", "qwert12345."),
    ]

    workers = [AccountWorker(u, p) for u, p in accounts_config]
    
    total_target_per_acc = 20  # 每次运行只跑50个钻石
    batch_per_acc = 20
    start_time = time.time()  # 记录开始时间
    time_limit = 5 * 60  # 5分钟时间限制（秒）

    print(f"=== 多账户轮询启动 | 账户总数: {len(workers)} | 目标: {total_target_per_acc}钻 | 时间限制: 5分钟 ===")

    while any(not w.is_finished for w in workers):
        # 检查运行时间是否超过限制
        if time.time() - start_time > time_limit:
            print("⏰ 运行时间超过5分钟，自动结束")
            break
            
        for worker in workers:
            if worker.is_finished:
                continue
            
            # 检查运行时间是否超过限制
            if time.time() - start_time > time_limit:
                print("⏰ 运行时间超过5分钟，自动结束")
                break
            
            worker.run_batch(batch_limit=batch_per_acc, total_target=total_target_per_acc)
            
            print(f"--- 账户 {worker.email} 批次结束，现有总钻石数: {worker.current_total}，准备切换 ---")
            time.sleep(10) # 账户间切换缓冲

    print("✅ 任务结束！")
    for worker in workers:
        print(f"账户 {worker.email} 本次运行获得: {worker.total_earned}钻，现有总数: {worker.current_total}钻")
